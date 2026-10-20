"""FastAPI sidecar for SpikingBrain-7B on RTX 3060 6 GB (task T205).

Loads ``maujim/spikingbrain-v1-7b-base`` directly via HuggingFace
``transformers`` with **bitsandbytes 4-bit (NF4) quantization**. Replaces
the previous vLLM-HyMeta subprocess path: ~4-4.5 GB in VRAM instead of
~14 GB, all weights resident on GPU (no CPU offload), expected ~5-10
tok/s on an RTX 3060 Laptop.

The two endpoints the Q-SPEACE :class:`HTTPSpikingBrainClient` expects
are kept verbatim, so the Windows-side package is unchanged:

    POST /think  -> {text, confidence, belief, spikes, plasticity, ...}
    GET  /health -> {ready, model, vram_mb, quantization, pid, ...}

Belief / spike / plasticity conversion reuses the same SPEACE primitives
as the offline stub (:func:`q_speace.spiking.encoder.dynamic_spikes`
and :class:`q_speace.spiking.SpikePlasticity`) for end-to-end
numerical coherence. This requires ``q_speace`` to be importable on
``sys.path``; the install script adds the repo root for that.

Required environment variables
------------------------------

- ``SPB_MODEL_PATH``        local path to the SpikingBrain-7B repo.
                            Default: ``~/models/maujim/spikingbrain-v1-7b-base``.
- ``SPB_SIDECAR_PORT``      port this sidecar listens on (default 8001).
- ``SPB_MAX_MODEL_LEN``     context length cap (default 512, RTX 3060 6GB).
- ``SPB_BF16``              bool, run in bf16 if True (default True). With
                            4-bit quantization this is the *compute* dtype
                            of the dequantized weights; the storage dtype
                            is int4 (NF4).
- ``SPB_QUANT_BITS``        quantization bits (4 or 8). Default 4.
- ``SPB_DEVICE_MAP``        HF device map (default ``"auto"``).
- ``SPB_MAX_NEW_TOKENS_CAP`` cap for ``n_tokens`` (default 256).

Run on WSL2::

    pip install fastapi uvicorn httpx transformers torch bitsandbytes accelerate
    python -m spiking_brain_server.server

Then from Windows PowerShell::

    $env:Q_SPEACE_BRAIN_ENDPOINT = "http://localhost:8001"
    qspace brain think "What is coherence_phi?"
"""
from __future__ import annotations

import asyncio
import math
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ----------------------------------------------------------------------
# Make q_speace importable for the shared belief/spike/plasticity math
# ----------------------------------------------------------------------
# The repo root (the directory that *contains* the ``q_speace`` package)
# is the parent of ``spiking_brain_server/``. When the sidecar is launched
# from WSL2, the working directory is the repo root (see install.sh /
# README), so this is normally a no-op — but adding it explicitly is
# robust to relocations.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# Lazy imports: torch / transformers / bitsandbytes are only needed when
# the model is actually loaded. This keeps the FastAPI app importable on
# Windows (where these may not be installed) for unit tests.
def _lazy_import_runtime():
    """Import torch + transformers + bitsandbytes. Raises on failure."""
    try:
        import torch  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "torch is required to run the sidecar; install via install.sh"
        ) from exc
    try:
        from transformers import (  # noqa: F401
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "transformers is required to run the sidecar; install via install.sh"
        ) from exc
    try:
        import bitsandbytes  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "bitsandbytes is required for 4-bit quantization; "
            "install via install.sh"
        ) from exc


# SPEACE primitives (reused to match the stub exactly).
from q_speace.spiking.encoder import dynamic_spikes  # noqa: E402
from q_speace.spiking.plasticity import SpikePlasticity  # noqa: E402

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}


import json as _json

SIDECAR_PORT = _env_int("SPB_SIDECAR_PORT", 8001)
MAX_MODEL_LEN = _env_int("SPB_MAX_MODEL_LEN", 512)
QUANT_BITS = _env_int("SPB_QUANT_BITS", 4)


def _resolve_device_map(raw: str) -> str | dict:
    """Resolve ``SPB_DEVICE_MAP``.

    ``transformers`` strictly type-checks the ``device_map`` kwarg: a
    string must be a device name (e.g. ``"cpu"``, ``"cuda:0"``) or one
    of the preset balanced modes (``"auto"``, ``"balanced"``...); a
    dict must be a layer→device mapping like ``{"": 0}``. We accept
    either in the env var: starting with ``{`` is parsed as JSON,
    otherwise the raw string is forwarded (transformers rejects
    anything else with a clear ``ValueError``).
    """
    if raw.startswith("{"):
        return _json.loads(raw)
    return raw


DEVICE_MAP = _resolve_device_map(os.environ.get("SPB_DEVICE_MAP", "auto"))
MAX_NEW_TOKENS_CAP = _env_int("SPB_MAX_NEW_TOKENS_CAP", 256)
# T-SPB-0B fix: cache-less mode forces forward singles (no
# past_key_values). ~10x slower but avoids the cache sliding window
# degradation observed in fla × transformers 4.55. Set via
# SPB_NO_CACHE=1 or --no-cache on the CLI.
CACHE_LESS = _env_bool("SPB_NO_CACHE", False)
DEFAULT_MODEL_PATH = os.path.expanduser(
    os.environ.get(
        "SPB_MODEL_PATH", "~/models/maujim/spikingbrain-v1-7b-base"
    )
)


# ----------------------------------------------------------------------
# Model state (singleton)
# ----------------------------------------------------------------------

model_obj: Any | None = None
tokenizer_obj: Any | None = None
model_ready: bool = False
model_lock: asyncio.Lock = asyncio.Lock()


def _compute_dtype() -> torch.dtype:
    import torch

    return torch.bfloat16 if _env_bool("SPB_BF16", True) else torch.float16


def _make_bnb_config(compute_dtype: torch.dtype):
    from transformers import BitsAndBytesConfig

    if QUANT_BITS == 4:
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )
    if QUANT_BITS == 8:
        return BitsAndBytesConfig(load_in_8bit=True)
    raise ValueError(
        f"SPB_QUANT_BITS must be 4 or 8, got {QUANT_BITS}"
    )


def _install_window_attention_patcher() -> None:
    """Install a :class:`sys.meta_path` hook that patches BICLab's
    ``window_attention.py`` **in memory** at import time.

    Why we need this: ``maujim/spikingbrain-v1-7b-base`` ships a
    dynamic ``window_attention.py`` that calls
    ``_upad_input(q, k, v, attention_mask, q_len)`` — a signature
    valid in transformers ≤ 4.54. From transformers 4.55 onward,
    ``_upad_input`` gained a required 6th positional argument
    ``unpad_input_func``. Forward passes therefore crash with::

        TypeError: _upad_input() missing 1 required positional argument:
        'unpad_input_func'

    HuggingFace's dynamic-module loader auto-refreshes the cached
    copy under ``~/.cache/huggingface/modules/transformers_modules/...``
    every time it sees a hash mismatch, which defeats on-disk
    patches. The fix is to intercept the import *before* the bytecode
    is compiled: a :class:`MetaPathFinder` + :class:`SourceLoader`
    pair reads the source from disk, mutates the ``_upad_input(...)``
    call site to pass ``unpad_input_func=None``, then compiles and
    execs the patched source in the module's namespace.

    The hook is installed at sidecar startup and is idempotent: if
    already installed (sentinel attribute on the finder class) it
    returns immediately. After a successful install,
    ``_q_speace_window_attention_finder`` is registered in
    ``sys.meta_path`` ahead of HuggingFace's loader.
    """
    import importlib.abc
    import importlib.machinery

    TARGET_BASENAME = "window_attention.py"
    OLD = (
        "                    else torch.ones(key_states.shape[:2]).to(key_states), q_len\n"
        "            )"
    )
    NEW = (
        "                    else torch.ones(key_states.shape[:2]).to(key_states), q_len,\n"
        "                unpad_input_func=None,\n"
        "            )"
    )

    # q_speace patch: fix BICLab's SDPA fallback mask shape. Their
    # code uses torch.zeros_like(q_b) which has shape (B, H, q_len,
    # head_dim=128) — wrong when k_len differs from head_dim (varlen
    # with cache). Correct: (B, H, q_len, k_len). Same fix applied to
    # the q_/k_ path. The SDPA fallback template in this same function
    # uses DOUBLE-quoted -inf; the on-disk BICLab file uses single.
    OLD_MASK_V_DQ = (
        "attn_mask = torch.zeros_like(q_b, dtype=q.dtype).masked_fill("
        "~mask, float(\"-inf\"))"
    )
    NEW_MASK_V_DQ = (
        "attn_mask = torch.zeros("
        "(q_b.shape[0], q_b.shape[1], q_b.shape[2], k_b.shape[2]), "
        "dtype=q.dtype, device=q.device"
        ").masked_fill(~mask, float(\"-inf\"))"
    )
    OLD_MASK_V_SQ = (
        "attn_mask = torch.zeros_like(q_b, dtype=q.dtype).masked_fill("
        "~mask, float('-inf'))"
    )
    NEW_MASK_V_SQ = (
        "attn_mask = torch.zeros("
        "(q_b.shape[0], q_b.shape[1], q_b.shape[2], k_b.shape[2]), "
        "dtype=q.dtype, device=q.device"
        ").masked_fill(~mask, float('-inf'))"
    )
    OLD_MASK_S_DQ = (
        "attn_mask = torch.zeros_like(q_, dtype=q.dtype).masked_fill("
        "~mask, float(\"-inf\"))"
    )
    NEW_MASK_S_DQ = (
        "attn_mask = torch.zeros("
        "(q_.shape[0], q_.shape[1], q_.shape[2], k_.shape[2]), "
        "dtype=q.dtype, device=q.device"
        ").masked_fill(~mask, float(\"-inf\"))"
    )
    OLD_MASK_S_SQ = (
        "attn_mask = torch.zeros_like(q_, dtype=q.dtype).masked_fill("
        "~mask, float('-inf'))"
    )
    NEW_MASK_S_SQ = (
        "attn_mask = torch.zeros("
        "(q_.shape[0], q_.shape[1], q_.shape[2], k_.shape[2]), "
        "dtype=q.dtype, device=q.device"
        ").masked_fill(~mask, float('-inf'))"
    )

    # q_speace patch: index_copy_ requires a long tensor; _upad_input
    # returns int32 indices. Add .long() cast.
    OLD_INDICES = (
        "out.index_copy_(0, indices.to(hidden_states.device), hidden_states)"
    )
    NEW_INDICES = (
        "out.index_copy_(0, indices.to(hidden_states.device).long(), hidden_states)"
    )

    # Second patch: install a PyTorch SDPA fallback for the symbols
    # normally provided by the ``flash_attn`` package. BICLab's
    # modeling_gla_swa.py / window_attention.py expects
    # ``flash_attn_varlen_func``, ``flash_attn_func`` and
    # ``pad_input`` to be importable whenever ``is_flash_attn_2_available()``
    # is True. When the user has not installed flash-attn (no
    # CUDA toolkit to build it, or skipped for speed), we synthesise
    # those symbols on the fly using torch's
    # ``F.scaled_dot_product_attention`` plus a tiny varlen↔batched
    # bridge. The performance is lower than the native flash-attn
    # kernel (no fused softmax, no sliding-window fused mask) but
    # correctness is preserved, which is enough to validate the
    # end-to-end Q-SPEACE <-> SpikingBrain pipeline.
    FLASH_IMPORT_BLOCK = (
        "from transformers.utils import is_flash_attn_2_available\n"
        "if is_flash_attn_2_available():\n"
        "    from flash_attn.flash_attn_interface import flash_attn_varlen_func, flash_attn_func\n"
        "    from flash_attn.bert_padding import pad_input\n"
    )
    FLASH_IMPORT_BLOCK_PATCHED = FLASH_IMPORT_BLOCK + (
        "else:\n"
        "    # Injected by q_speace/spiking_brain_server: SDPA fallback when\n"
        "    # flash-attn is not installed. See _install_window_attention_patcher.\n"
        "    import torch.nn.functional as _F\n"
        "\n"
        "    def _q_speace_varlen_to_batched(x, cu_seqlens, max_len):\n"
        "        batch = cu_seqlens.shape[0] - 1\n"
        "        out = torch.zeros(\n"
        "            (batch, max_len, x.shape[1], x.shape[2]),\n"
        "            dtype=x.dtype, device=x.device,\n"
        "        )\n"
        "        for _i in range(batch):\n"
        "            _s, _e = int(cu_seqlens[_i]), int(cu_seqlens[_i + 1])\n"
        "            if _e > _s:\n"
        "                out[_i, : _e - _s] = x[_s:_e]\n"
        "        return out\n"
        "\n"
        "    def _q_speace_batched_to_varlen(x, cu_seqlens):\n"
        "        chunks = []\n"
        "        for _i in range(cu_seqlens.shape[0] - 1):\n"
        "            _s, _e = int(cu_seqlens[_i]), int(cu_seqlens[_i + 1])\n"
        "            if _e > _s:\n"
        "                chunks.append(x[_i, : _e - _s])\n"
        "        return torch.cat(chunks, dim=0) if chunks else x.new_zeros((0, x.shape[1], x.shape[2]))\n"
        "\n"
        "    def flash_attn_varlen_func(\n"
        "        q, k, v,\n"
        "        cu_seqlens_q, cu_seqlens_k,\n"
        "        max_seqlen_q, max_seqlen_k,\n"
        "        dropout_p=0.0, softmax_scale=None, causal=True, window_size=(-1, -1),\n"
        "    ):\n"
        "        # q,k,v: (total_tokens, num_heads, head_dim) per token varlen layout.\n"
        "        if softmax_scale is None:\n"
        "            softmax_scale = q.shape[-1] ** -0.5\n"
        "        q_b = _q_speace_varlen_to_batched(q, cu_seqlens_q, int(max_seqlen_q)).transpose(1, 2)\n"
        "        k_b = _q_speace_varlen_to_batched(k, cu_seqlens_k, int(max_seqlen_k)).transpose(1, 2)\n"
        "        v_b = _q_speace_varlen_to_batched(v, cu_seqlens_k, int(max_seqlen_k)).transpose(1, 2)\n"
        "        # sliding window: build a per-position (q,k) mask; for SDPA we use a\n"
        "        # boolean attn_mask of shape (batch, num_heads, q_len, k_len).\n"
        "        win_left, win_right = window_size\n"
        "        bsz, _, q_len, _ = q_b.shape\n"
        "        k_len = k_b.shape[2]\n"
        "        attn_mask = None\n"
        "        if causal or win_left >= 0 or win_right >= 0:\n"
        "            qi = torch.arange(q_len, device=q.device).view(1, 1, q_len, 1)\n"
        "            ki = torch.arange(k_len, device=q.device).view(1, 1, 1, k_len)\n"
        "            mask = torch.ones((bsz, 1, q_len, k_len), dtype=torch.bool, device=q.device)\n"
        "            if causal:\n"
        "                causal_mask = qi >= ki\n"
        "                mask = mask & causal_mask\n"
        "            if win_left >= 0:\n"
        "                left_mask = (qi - ki) <= win_left\n"
        "                mask = mask & left_mask\n"
        "            if win_right >= 0:\n"
        "                right_mask = (ki - qi) <= win_right\n"
        "                mask = mask & right_mask\n"
        "            attn_mask = torch.zeros(\n"
        "                (q_b.shape[0], q_b.shape[1], q_b.shape[2], k_b.shape[2]),\n"
        "                dtype=q.dtype, device=q.device,\n"
        "            ).masked_fill(~mask, float(\"-inf\"))\n"
        "        out_b = _F.scaled_dot_product_attention(\n"
        "            q_b, k_b, v_b,\n"
        "            attn_mask=attn_mask,\n"
        "            dropout_p=dropout_p if dropout_p > 0 else 0.0,\n"
        "            is_causal=False,  # we pass attn_mask explicitly above\n"
        "            scale=softmax_scale,\n"
        "        )\n"
        "        # back to (total_tokens, num_heads, head_dim)\n"
        "        out_b = out_b.transpose(1, 2)\n"
        "        return _q_speace_batched_to_varlen(out_b, cu_seqlens_q)\n"
        "\n"
        "    def flash_attn_func(\n"
        "        q, k, v,\n"
        "        dropout_p=0.0, softmax_scale=None, causal=True, window_size=(-1, -1),\n"
        "    ):\n"
        "        # q,k,v: (batch, seq, num_heads, head_dim) -> transpose to SDPA layout.\n"
        "        if softmax_scale is None:\n"
        "            softmax_scale = q.shape[-1] ** -0.5\n"
        "        q_ = q.transpose(1, 2)\n"
        "        k_ = k.transpose(1, 2)\n"
        "        v_ = v.transpose(1, 2)\n"
        "        bsz, _, q_len, _ = q_.shape\n"
        "        k_len = k_.shape[2]\n"
        "        attn_mask = None\n"
        "        win_left, win_right = window_size\n"
        "        if causal or win_left >= 0 or win_right >= 0:\n"
        "            qi = torch.arange(q_len, device=q.device).view(1, 1, q_len, 1)\n"
        "            ki = torch.arange(k_len, device=q.device).view(1, 1, 1, k_len)\n"
        "            mask = torch.ones((bsz, 1, q_len, k_len), dtype=torch.bool, device=q.device)\n"
        "            if causal:\n"
        "                mask = mask & (qi >= ki)\n"
        "            if win_left >= 0:\n"
        "                mask = mask & ((qi - ki) <= win_left)\n"
        "            if win_right >= 0:\n"
        "                mask = mask & ((ki - qi) <= win_right)\n"
        "            attn_mask = torch.zeros(\n"
        "                (q_.shape[0], q_.shape[1], q_.shape[2], k_.shape[2]),\n"
        "                dtype=q.dtype, device=q.device,\n"
        "            ).masked_fill(~mask, float(\"-inf\"))\n"
        "        out_ = _F.scaled_dot_product_attention(\n"
        "            q_, k_, v_,\n"
        "            attn_mask=attn_mask,\n"
        "            dropout_p=dropout_p if dropout_p > 0 else 0.0,\n"
        "            is_causal=False,\n"
        "            scale=softmax_scale,\n"
        "        )\n"
        "        return out_.transpose(1, 2).contiguous()\n"
        "\n"
        "    def pad_input(hidden_states, indices, batch, seqlen):\n"
        "        out = torch.zeros(\n"
        "            (batch * seqlen, *hidden_states.shape[1:]),\n"
        "            dtype=hidden_states.dtype, device=hidden_states.device,\n"
        "        )\n"
        "        out.index_copy_(0, indices.to(hidden_states.device).long(), hidden_states)\n"
        "        return out.view(batch, seqlen, *hidden_states.shape[1:])\n"
    )
    FLASH_PATCH_MARKER = "# q_speace_sdpa_fallback_installed"

    class _PatchedSourceLoader(importlib.abc.SourceLoader):
        def __init__(self, name: str, path: str) -> None:
            super().__init__()
            self._name = name
            self._path = path

        def get_filename(self, fullname: str) -> str:
            return self._path

        def get_data(self, path: str) -> bytes:
            with open(path, "rb") as f:
                src_bytes = f.read()
            src = src_bytes.decode("utf-8")
            # Idempotency check.
            if ("unpad_input_func=None" in src
                    and FLASH_PATCH_MARKER in src
                    and "k_b.shape[2]" in src
                    and "k_.shape[2]" in src
                    and ".long(), hidden_states" in src):
                return src_bytes
            patched = src
            if OLD in patched and "unpad_input_func=None" not in patched:
                patched = patched.replace(OLD, NEW, 1)
                print(
                    f"[sidecar] patched {os.path.basename(path)} "
                    "in-memory (unpad_input_func=None)",
                    file=sys.stderr,
                )
            if FLASH_IMPORT_BLOCK in patched and FLASH_PATCH_MARKER not in patched:
                patched = patched.replace(
                    FLASH_IMPORT_BLOCK,
                    FLASH_IMPORT_BLOCK_PATCHED,
                    1,
                )
                print(
                    f"[sidecar] patched {os.path.basename(path)} "
                    "in-memory (SDPA fallback for flash_attn)",
                    file=sys.stderr,
                )
            # q_speace mask shape fix (varlen path). Accept both
            # single- and double-quoted -inf since the SDPA fallback
            # template uses double quotes while the on-disk file
            # uses single quotes.
            if ("k_b.shape[2]" not in patched):
                print(
                    f"[sidecar] DEBUG: checking mask fix varlen, "
                    f"q_b in patched: {'q_b' in patched}, "
                    f"OLD_MASK_V_DQ in patched: {OLD_MASK_V_DQ in patched}, "
                    f"OLD_MASK_V_SQ in patched: {OLD_MASK_V_SQ in patched}",
                    file=sys.stderr,
                )
                for old_v, new_v, q in [
                    (OLD_MASK_V_DQ, NEW_MASK_V_DQ, "dq"),
                    (OLD_MASK_V_SQ, NEW_MASK_V_SQ, "sq"),
                ]:
                    if old_v in patched:
                        patched = patched.replace(old_v, new_v, 1)
                        print(
                            f"[sidecar] patched {os.path.basename(path)} "
                            f"in-memory (mask shape: q_b x k_b [{q}])",
                            file=sys.stderr,
                        )
                        break
            # q_speace mask shape fix (standard path)
            if "k_.shape[2]" not in patched:
                for old_s, new_s, q in [
                    (OLD_MASK_S_DQ, NEW_MASK_S_DQ, "dq"),
                    (OLD_MASK_S_SQ, NEW_MASK_S_SQ, "sq"),
                ]:
                    if old_s in patched:
                        patched = patched.replace(old_s, new_s, 1)
                        print(
                            f"[sidecar] patched {os.path.basename(path)} "
                            f"in-memory (mask shape: q_ x k_ [{q}])",
                            file=sys.stderr,
                        )
                        break
                print(
                    f"[sidecar] patched {os.path.basename(path)} "
                    "in-memory (mask shape: q_ x k_)",
                    file=sys.stderr,
                )
            # q_speace indices long cast
            if OLD_INDICES in patched and ".long(), hidden_states" not in patched:
                patched = patched.replace(OLD_INDICES, NEW_INDICES, 1)
                print(
                    f"[sidecar] patched {os.path.basename(path)} "
                    "in-memory (indices .long())",
                    file=sys.stderr,
                )
            if patched is src:
                return src_bytes
            return patched.encode("utf-8")

    class _WAWindowAttentionFinder:
        # Class-level sentinel for idempotent install.
        _installed = False

        def find_spec(self, fullname, path, target=None):
            if not fullname.endswith(TARGET_BASENAME[:-3]):
                return None
            # Only intercept the BICLab module: search sys.modules for
            # any cached submodule whose __file__ points at the HF
            # transformers_modules cache.
            cached = sys.modules.get(fullname)
            if cached is not None:
                file_path = getattr(cached, "__file__", None)
            else:
                # Fallback: scan the most likely cache dir.
                file_path = self._likely_cache_path()
            if not file_path or not os.path.exists(file_path):
                return None
            return importlib.machinery.ModuleSpec(
                fullname,
                _PatchedSourceLoader(fullname, file_path),
                origin=file_path,
            )

        @staticmethod
        def _likely_cache_path() -> str | None:
            repo_name = os.path.basename(DEFAULT_MODEL_PATH.rstrip("/"))
            repo_dir = os.path.join(
                os.path.expanduser("~"),
                ".cache",
                "huggingface",
                "modules",
                "transformers_modules",
                repo_name,
            )
            target = os.path.join(repo_dir, TARGET_BASENAME)
            return target if os.path.exists(target) else None

    if _WAWindowAttentionFinder._installed:
        return
    sys.meta_path.insert(0, _WAWindowAttentionFinder())
    _WAWindowAttentionFinder._installed = True
    print(
        "[sidecar] window_attention import hook installed",
        file=sys.stderr,
    )


def _evict_cached_window_attention() -> None:
    """Drop any cached copy of BICLab's ``window_attention`` from
    ``sys.modules`` and patch the source on disk in BOTH the HF
    dynamic-module cache AND the model repo.

    Why: ``transformers``' dynamic-module loader caches
    ``window_attention.py`` in ``sys.modules`` the first time
    ``AutoModelForCausalLM.from_pretrained(..., trust_remote_code=True)``
    is called, even before our patcher is installed. On the second
    model load (re-entering lifespan after a hot restart, or running
    the server after the smoke-test script already imported the
    buggy module), ``sys.modules`` still holds the unpatched bytecode
    and the meta-path hook never gets a chance to intercept the
    import. Worse: HF's dynamic-module loader hashes the source file
    and re-generates the cached copy when the hash changes, so a
    one-shot in-memory patch is overwritten on the next load.

    Strategy:
      1. Evict the cached module so Python re-imports it.
      2. Patch the source on disk in BOTH:
         - the model repo (``~/models/<repo>/window_attention.py``)
         - the HF cache (``~/.cache/huggingface/modules/...``)
         Idempotent via a marker comment. Patching the model repo
         guarantees that any subsequent HF cache regeneration also
         copies the patched source.
    """
    targets = [
        name
        for name, mod in sys.modules.items()
        if name.endswith("window_attention")
        and getattr(mod, "__file__", None) is not None
        and "huggingface/modules" in (getattr(mod, "__file__", "") or "")
    ]
    for name in targets:
        del sys.modules[name]
    if targets:
        print(
            f"[sidecar] evicted cached window_attention: {targets}",
            file=sys.stderr,
        )

    # SPB_SKIP_DISK_PATCHER=1 → trust the on-disk files. Used after
    # the mask + indices fixes have been applied externally by
    # _apply_mask_fix.py. Re-applying the patcher here would race
    # with those edits and generate malformed Python (SyntaxError).
    if _env_bool("SPB_SKIP_DISK_PATCHER", False):
        print(
            "[sidecar] SPB_SKIP_DISK_PATCHER=1 — trusting on-disk "
            "window_attention.py (patches applied externally)",
            file=sys.stderr,
        )
        return

    OLD = (
        "                    else torch.ones(key_states.shape[:2]).to(key_states), q_len\n"
        "            )"
    )
    NEW = (
        "                    else torch.ones(key_states.shape[:2]).to(key_states), q_len,\n"
        "                unpad_input_func=None,\n"
        "            )  # q_speace_patched_upad_input"
    )
    UPAD_MARKER = "# q_speace_patched_upad_input"

    FLASH_IMPORT_BLOCK = (
        "from transformers.utils import is_flash_attn_2_available\n"
        "if is_flash_attn_2_available():\n"
        "    from flash_attn.flash_attn_interface import flash_attn_varlen_func, flash_attn_func\n"
        "    from flash_attn.bert_padding import pad_input\n"
    )
    FLASH_IMPORT_BLOCK_PATCHED = FLASH_IMPORT_BLOCK + (
        "else:\n"
        "    # Injected by q_speace/spiking_brain_server: SDPA fallback when\n"
        "    # flash-attn is not installed.\n"
        "    def _q_speace_varlen_to_batched(x, cu_seqlens, max_len):\n"
        "        batch = cu_seqlens.shape[0] - 1\n"
        "        out = torch.zeros((batch, max_len, x.shape[1], x.shape[2]), dtype=x.dtype, device=x.device)\n"
        "        for _i in range(batch):\n"
        "            _s, _e = int(cu_seqlens[_i]), int(cu_seqlens[_i + 1])\n"
        "            if _e > _s: out[_i, : _e - _s] = x[_s:_e]\n"
        "        return out\n"
        "    def _q_speace_batched_to_varlen(x, cu_seqlens):\n"
        "        chunks = []\n"
        "        for _i in range(cu_seqlens.shape[0] - 1):\n"
        "            _s, _e = int(cu_seqlens[_i]), int(cu_seqlens[_i + 1])\n"
        "            if _e > _s: chunks.append(x[_i, : _e - _s])\n"
        "        return torch.cat(chunks, dim=0) if chunks else x.new_zeros((0, x.shape[1], x.shape[2]))\n"
        "    def flash_attn_varlen_func(q, k, v, cu_seqlens_q, cu_seqlens_k, max_seqlen_q, max_seqlen_k, dropout_p=0.0, softmax_scale=None, causal=True, window_size=(-1, -1)):\n"
        "        if softmax_scale is None: softmax_scale = q.shape[-1] ** -0.5\n"
        "        q_b = _q_speace_varlen_to_batched(q, cu_seqlens_q, int(max_seqlen_q)).transpose(1, 2)\n"
        "        k_b = _q_speace_varlen_to_batched(k, cu_seqlens_k, int(max_seqlen_k)).transpose(1, 2)\n"
        "        v_b = _q_speace_varlen_to_batched(v, cu_seqlens_k, int(max_seqlen_k)).transpose(1, 2)\n"
        "        win_left, win_right = window_size\n"
        "        bsz, _, q_len, _ = q_b.shape\n"
        "        k_len = k_b.shape[2]\n"
        "        attn_mask = None\n"
        "        if causal or win_left >= 0 or win_right >= 0:\n"
        "            qi = torch.arange(q_len, device=q.device).view(1, 1, q_len, 1)\n"
        "            ki = torch.arange(k_len, device=q.device).view(1, 1, 1, k_len)\n"
        "            mask = torch.ones((bsz, 1, q_len, k_len), dtype=torch.bool, device=q.device)\n"
        "            if causal: mask = mask & (qi >= ki)\n"
        "            if win_left >= 0: mask = mask & ((qi - ki) <= win_left)\n"
        "            if win_right >= 0: mask = mask & ((ki - qi) <= win_right)\n"
        "            attn_mask = torch.zeros((q_b.shape[0], q_b.shape[1], q_b.shape[2], k_b.shape[2]), dtype=q.dtype, device=q.device).masked_fill(~mask, float('-inf'))\n"
        "        out_b = F.scaled_dot_product_attention(q_b, k_b, v_b, attn_mask=attn_mask, dropout_p=dropout_p if dropout_p > 0 else 0.0, is_causal=False, scale=softmax_scale)\n"
        "        return _q_speace_batched_to_varlen(out_b.transpose(1, 2), cu_seqlens_q)\n"
        "    def flash_attn_func(q, k, v, dropout_p=0.0, softmax_scale=None, causal=True, window_size=(-1, -1)):\n"
        "        if softmax_scale is None: softmax_scale = q.shape[-1] ** -0.5\n"
        "        q_ = q.transpose(1, 2); k_ = k.transpose(1, 2); v_ = v.transpose(1, 2)\n"
        "        bsz, _, q_len, _ = q_.shape\n"
        "        k_len = k_.shape[2]\n"
        "        attn_mask = None\n"
        "        win_left, win_right = window_size\n"
        "        if causal or win_left >= 0 or win_right >= 0:\n"
        "            qi = torch.arange(q_len, device=q.device).view(1, 1, q_len, 1)\n"
        "            ki = torch.arange(k_len, device=q.device).view(1, 1, 1, k_len)\n"
        "            mask = torch.ones((bsz, 1, q_len, k_len), dtype=torch.bool, device=q.device)\n"
        "            if causal: mask = mask & (qi >= ki)\n"
        "            if win_left >= 0: mask = mask & ((qi - ki) <= win_left)\n"
        "            if win_right >= 0: mask = mask & ((ki - qi) <= win_right)\n"
        "            attn_mask = torch.zeros((q_.shape[0], q_.shape[1], q_.shape[2], k_.shape[2]), dtype=q.dtype, device=q.device).masked_fill(~mask, float('-inf'))\n"
        "        out_ = F.scaled_dot_product_attention(q_, k_, v_, attn_mask=attn_mask, dropout_p=dropout_p if dropout_p > 0 else 0.0, is_causal=False, scale=softmax_scale)\n"
        "        return out_.transpose(1, 2).contiguous()\n"
        "    def pad_input(hidden_states, indices, batch, seqlen):\n"
        "        out = torch.zeros((batch * seqlen, *hidden_states.shape[1:]), dtype=hidden_states.dtype, device=hidden_states.device)\n"
        "        out.index_copy_(0, indices.to(hidden_states.device), hidden_states)\n"
        "        return out.view(batch, seqlen, *hidden_states.shape[1:])\n"
    )
    FLASH_MARKER = "# q_speace_sdpa_fallback_installed"

    candidate_paths = []
    # 1. The model repo (canonical source).
    if os.path.isdir(DEFAULT_MODEL_PATH):
        candidate_paths.append(
            os.path.join(DEFAULT_MODEL_PATH, "window_attention.py")
        )
    # 2. The HF dynamic-module cache.
    cache_dir = os.path.join(
        os.path.expanduser("~"),
        ".cache",
        "huggingface",
        "modules",
        "transformers_modules",
        os.path.basename(DEFAULT_MODEL_PATH.rstrip("/")),
    )
    candidate_paths.append(os.path.join(cache_dir, "window_attention.py"))

    for target_path in candidate_paths:
        if not os.path.exists(target_path):
            continue
        with open(target_path, encoding="utf-8") as f:
            src = f.read()
        if UPAD_MARKER in src and FLASH_MARKER in src:
            print(
                f"[sidecar] {target_path} already patched, skipping",
                file=sys.stderr,
            )
            continue
        original = src
        if UPAD_MARKER not in src and OLD in src:
            src = src.replace(OLD, NEW, 1)
        if FLASH_MARKER not in src and FLASH_IMPORT_BLOCK in src:
            src = src.replace(FLASH_IMPORT_BLOCK, FLASH_IMPORT_BLOCK_PATCHED, 1)
        if src == original:
            print(
                f"[sidecar] WARNING: nothing to patch in {target_path}",
                file=sys.stderr,
            )
            continue
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(src)
        print(
            f"[sidecar] patched {target_path} on disk "
            "(unpad_input_func=None + SDPA flash fallback)",
            file=sys.stderr,
        )


def _load_model() -> None:
    """Load the model + tokenizer into the singleton globals.

    Called once at lifespan startup. Heavy import + 4-bit quantize on
    a 7B model takes 30-60s on RTX 3060; emits progress logs.
    """
    global model_obj, tokenizer_obj, model_ready

    # Install the window_attention meta-path hook BEFORE any
    # ``trust_remote_code`` import happens. Then evict any already-cached
    # copy of the buggy module from ``sys.modules`` so that the patcher
    # sees the next ``import`` and re-loads the patched source.
    _install_window_attention_patcher()
    _evict_cached_window_attention()

    if not os.path.isdir(DEFAULT_MODEL_PATH):
        print(
            f"[sidecar] WARNING: model path {DEFAULT_MODEL_PATH} does not "
            f"exist; run install.sh + download_model.sh first.",
            file=sys.stderr,
        )
        return

    _lazy_import_runtime()
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(
        f"[sidecar] loading tokenizer from {DEFAULT_MODEL_PATH}",
        file=sys.stderr,
    )
    tokenizer_obj = AutoTokenizer.from_pretrained(
        DEFAULT_MODEL_PATH,
        trust_remote_code=True,
        padding_side="left",
    )
    if tokenizer_obj.pad_token is None:
        tokenizer_obj.pad_token = tokenizer_obj.eos_token

    compute_dtype = _compute_dtype()
    bnb_config = _make_bnb_config(compute_dtype)
    quant_label = "nf4-4bit" if QUANT_BITS == 4 else "int8-8bit"
    print(
        f"[sidecar] loading model with {quant_label} quantization "
        f"(compute={compute_dtype}, device_map={DEVICE_MAP})...",
        file=sys.stderr,
    )
    t0 = time.time()
    max_memory_raw = os.environ.get("SPB_MAX_MEMORY", "")
    max_memory = None
    if max_memory_raw:
        raw_dict = _json.loads(max_memory_raw)
        # transformers requires integer keys for GPU devices.
        max_memory = {
            (int(k) if k.isdigit() else k): v for k, v in raw_dict.items()
        }
    kwargs = dict(
        trust_remote_code=True,
        quantization_config=bnb_config,
        device_map=DEVICE_MAP,
        torch_dtype=compute_dtype,
        # low_cpu_mem_usage=True is REQUIRED with bnb 4-bit + max_memory
        # to avoid meta-tensor errors when device_map="auto" offloads
        # some layers to CPU. Verified working in _probe_4bit.py.
        low_cpu_mem_usage=True,
    )
    if max_memory:
        kwargs["max_memory"] = max_memory
    model_obj = AutoModelForCausalLM.from_pretrained(
        DEFAULT_MODEL_PATH,
        **kwargs,
    )
    model_obj.eval()
    dt = time.time() - t0
    n_params = sum(p.numel() for p in model_obj.parameters())
    print(
        f"[sidecar] model loaded in {dt:.1f}s "
        f"({n_params/1e9:.2f}B params, {quant_label})",
        file=sys.stderr,
    )
    model_ready = True


# ----------------------------------------------------------------------
# Request / response models
# ----------------------------------------------------------------------


class ThinkRequest(BaseModel):
    prompt: str
    coherence_phi: float = 1.0
    n_tokens: int = 32
    history: list[dict[str, Any]] | None = None


class ThinkResponse(BaseModel):
    text: str
    confidence: float
    belief: list[float]
    spikes: dict[str, Any]
    plasticity: list[float]
    n_tokens: int = 0
    latency_s: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    ready: bool
    model: str
    vram_mb: int
    backend: str
    quantization: str
    cache_less: bool = False  # T-SPB-0B flag
    pid: int | None = None


# ----------------------------------------------------------------------
# Inference + SPEACE-native conversion
# ----------------------------------------------------------------------

# Plasticity tracker is stateful (EMA), exactly as in StubSpikingBrain.
# We keep one per agent_id; for the base model, a single tracker is enough
# since the sidecar is single-worker.
_plasticity = SpikePlasticity(num_units=3, decay=0.9, seed=0)


def _softmax_temperature(logits: list[float], coherence_phi: float) -> np.ndarray:
    arr = np.asarray(logits, dtype=float)
    temp = max(1.0 - coherence_phi, 0.05)
    z = arr / temp
    z = z - float(np.max(z))
    p = np.exp(z)
    p = p / max(float(np.sum(p)), 1e-12)
    return p


def _confidence_from_belief(belief: np.ndarray, coherence_phi: float) -> float:
    n = belief.size
    if n < 2:
        return float(min(max(coherence_phi, 0.0), 1.0))
    entropy = float(-np.sum(belief * np.log(np.maximum(belief, 1e-12))))
    max_entropy = math.log(n)
    c = 1.0 - entropy / max_entropy
    c = c * (0.5 + 0.5 * coherence_phi)
    return float(min(max(c, 0.0), 1.0))


def _build_prompt(req: ThinkRequest) -> str:
    """Compose a short, self-contained prompt.

    Keeps the base-model format (no chat template — maujim/.../V1-7B-base
    is the pretrained, not instruction-tuned, model). Recent history is
    prepended for short multi-turn coherence.
    """
    parts: list[str] = []
    if req.history:
        for h in req.history[-4:]:
            t = h.get("text", "")
            if t:
                parts.append(f"prev: {t}")
    parts.append(f"question: {req.prompt}")
    parts.append("answer:")
    return "\n".join(parts)


def _generate_cache_less(
    model: Any,
    tokenizer: Any,
    inputs: dict,
    n_tokens: int,
    coherence: float,
) -> torch.Tensor:
    """Generate ``n_tokens`` tokens via single forward passes (no cache).

    T-SPB-0B fix: ``flash-linear-attention`` × ``transformers>=4.55``
    corrupts the SWA cache across steps, producing garbage tokens after
    the first one. Re-tokenizing the growing sequence each step and
    throwing away the cache sidesteps the bug at ~10x cost in latency.

    Sampling parameters mirror the cached path:
    temperature = max(0.1, 0.7 * coherence + 0.1), top_p = 0.9,
    repetition_penalty = 1.1, do_sample = True.
    """
    import torch
    import torch.nn.functional as F

    eos_id = tokenizer.eos_token_id
    if eos_id is None:
        eos_id = tokenizer.pad_token_id
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = eos_id if eos_id is not None else 0

    temperature = max(0.1, 0.7 * coherence + 0.1)
    rep_penalty = 1.1
    top_p = 0.9

    # Track generated ids + attention mask of the *original* prompt
    # (used for repetition_penalty).
    prompt_ids = inputs["input_ids"][0].tolist()
    generated: list[int] = []
    cur = {k: v.clone() for k, v in inputs.items()}

    for _ in range(n_tokens):
        with torch.no_grad():
            logits = model_obj_forward(model, cur)
        next_logits = logits[:, -1, :].float()
        # Repetition penalty (basic implementation matching generate()
        # default: divide logits of already-seen tokens by rep_penalty).
        seen = set(prompt_ids + generated)
        if seen:
            penalty_mask = torch.zeros_like(next_logits, dtype=torch.bool)
            for tok in seen:
                if 0 <= tok < next_logits.shape[-1]:
                    penalty_mask[0, tok] = True
            next_logits = torch.where(
                penalty_mask & (next_logits > 0),
                next_logits / rep_penalty,
                next_logits,
            )
            next_logits = torch.where(
                penalty_mask & (next_logits <= 0),
                next_logits * rep_penalty,
                next_logits,
            )
        next_logits = next_logits / temperature
        # top-p (nucleus) sampling.
        sorted_logits, sorted_idx = torch.sort(next_logits, descending=True, dim=-1)
        probs = F.softmax(sorted_logits, dim=-1)
        cum = torch.cumsum(probs, dim=-1)
        keep = cum <= top_p
        keep[..., 0] = True
        sorted_logits = torch.where(keep, sorted_logits, torch.full_like(sorted_logits, float("-inf")))
        probs = F.softmax(sorted_logits, dim=-1)
        next_id = int(sorted_idx[0, torch.multinomial(probs[0], num_samples=1)].item())
        generated.append(next_id)
        if next_id == eos_id:
            break
        # Extend the sequence for the next forward pass.
        next_t = torch.tensor([[next_id]], device=cur["input_ids"].device, dtype=cur["input_ids"].dtype)
        cur["input_ids"] = torch.cat([cur["input_ids"], next_t], dim=1)
        if "attention_mask" in cur:
            cur["attention_mask"] = torch.cat(
                [cur["attention_mask"], torch.ones_like(next_t)], dim=1
            )

    return torch.tensor([generated], dtype=cur["input_ids"].dtype, device=cur["input_ids"].device)


def model_obj_forward(model: Any, inputs: dict) -> torch.Tensor:
    """Single forward returning last-token logits. No cache.

    Helper extracted so the cache-less loop stays readable and the
    flag ``use_cache=False`` is set in exactly one place. Forward
    returns ``logits`` directly; we read ``logits[:, -1, :]`` in the
    caller.
    """
    return model(**inputs, use_cache=False).logits


def _think_sync(req: ThinkRequest, n_classes: int) -> ThinkResponse:
    """Run the model once and convert output into the SPEACE-native triplet.

    This is the CPU/IO-blocking part: HF generate is not async, so we run
    it on a worker thread (asyncio.to_thread wraps the call site).
    """
    if model_obj is None or tokenizer_obj is None:
        raise RuntimeError("model not loaded")

    import torch

    coherence = float(min(max(req.coherence_phi, 0.0), 1.0))
    n_tokens = max(1, min(int(req.n_tokens), MAX_NEW_TOKENS_CAP))
    prompt = _build_prompt(req)

    inputs = tokenizer_obj(
        [prompt],
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=MAX_MODEL_LEN,
    )
    # Move tensors to the model's primary device.
    device = next(model_obj.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    in_len = int(inputs["input_ids"].shape[1])

    t0 = time.time()
    if CACHE_LESS:
        # T-SPB-0B fix: avoid past_key_values. Run forward singles and
        # re-tokenize the growing sequence each step. ~10x slower but
        # text is clean (no pérdida/adultes/Publié degradation observed
        # with the fla × transformers 4.55 cache sliding window).
        new_ids = _generate_cache_less(
            model_obj, tokenizer_obj, inputs, n_tokens, coherence
        )
        latency = time.time() - t0
    else:
        with torch.no_grad():
            out = model_obj.generate(
                **inputs,
                max_new_tokens=n_tokens,
                do_sample=True,
                temperature=max(0.1, 0.7 * coherence + 0.1),
                top_p=0.9,
                repetition_penalty=1.1,
                return_dict_in_generate=True,
                output_scores=True,
            )
        latency = time.time() - t0
        seq = out.sequences[0]
        new_ids = seq[in_len:]

    text = tokenizer_obj.decode(new_ids, skip_special_tokens=True)
    used_tokens = int(new_ids.shape[0])

    # Build the SPEACE belief vector. Strategy: hash the generated text
    # (stable, deterministic) into a prior, softmax with temperature
    # 1/coherence, then run dynamic_spikes + SpikePlasticity to get the
    # same numerics as StubSpikingBrain.
    import hashlib

    chunks: list[float] = []
    counter = 0
    while len(chunks) < n_classes:
        h = hashlib.sha256(f"{counter}:{text}".encode()).digest()
        for i in range(0, len(h), 4):
            if len(chunks) >= n_classes:
                break
            chunks.append(int.from_bytes(h[i : i + 4], "big") / 0xFFFFFFFF)
        counter += 1
    prior = np.asarray(chunks[:n_classes], dtype=float)
    prior = prior / max(float(np.linalg.norm(prior)), 1e-12)

    belief = _softmax_temperature(
        np.log(np.maximum(prior, 1e-12)).tolist(), coherence
    )

    # SAME primitives as StubSpikingBrain: dynamic_spikes + SpikePlasticity.
    # We re-init the plasticity tracker if n_classes changes.
    global _plasticity
    if _plasticity.coefficients().size != n_classes:
        _plasticity = SpikePlasticity(num_units=n_classes, decay=0.9, seed=0)

    spike_res = dynamic_spikes(
        belief, k=3.0, coherence_phi=coherence, beta=0.1
    )
    _plasticity.update(spike_res.spikes)
    plasticity = _plasticity.coefficients()

    confidence = _confidence_from_belief(belief, coherence)

    return ThinkResponse(
        text=text,
        confidence=confidence,
        belief=belief.tolist(),
        spikes={
            "spikes": [float(x) for x in spike_res.spikes.tolist()],
            "vth": [float(x) for x in spike_res.vth.tolist()],
            "num_spikes": int(spike_res.num_spikes),
            "sparsity": float(spike_res.sparsity),
            "rate": float(spike_res.rate),
        },
        plasticity=[float(x) for x in plasticity.tolist()],
        n_tokens=used_tokens,
        latency_s=latency,
        metadata={
            "backend": "hf-transformers-bnb4bit",
            "quantization": "nf4-4bit" if QUANT_BITS == 4 else "int8-8bit",
            "model_path": DEFAULT_MODEL_PATH,
            "device": str(device),
            # T-SPB-2 fix: prompt token count for energy-per-token math.
            "n_tokens_in": in_len,
            "cache_less": CACHE_LESS,
        },
    )


# ----------------------------------------------------------------------
# VRAM helper
# ----------------------------------------------------------------------


def _vram_mb() -> int:
    """Best-effort GPU VRAM usage query via nvidia-smi.

    Returns 0 on failure (no GPU, no nvidia-smi, etc.). The sidecar still
    reports ``ready=true`` if the model is loaded — VRAM is informational.
    """
    try:
        import subprocess

        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            timeout=3,
        )
        return int(out.decode().strip().splitlines()[0])
    except Exception:
        return 0


# ----------------------------------------------------------------------
# FastAPI app
# ----------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_ready
    # Try to load the model on startup. If anything fails (no torch, no
    # GPU, missing checkpoint) we keep ``model_ready=False`` and let the
    # endpoints respond with 503 / ready=False — the Windows side will
    # then either fall back to the stub or surface a clear error.
    try:
        await asyncio.to_thread(_load_model)
    except Exception as exc:
        print(
            f"[sidecar] model load failed: {exc.__class__.__name__}: {exc}",
            file=sys.stderr,
        )
        model_ready = False
    try:
        yield
    finally:
        # Free GPU memory.
        global model_obj, tokenizer_obj
        model_obj = None
        tokenizer_obj = None
        model_ready = False
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


app = FastAPI(title="Q-SPEACE SpikingBrain sidecar", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ready=model_ready,
        model=DEFAULT_MODEL_PATH,
        vram_mb=_vram_mb(),
        backend="hf-transformers-bnb4bit",
        quantization="nf4-4bit" if QUANT_BITS == 4 else "int8-8bit",
        cache_less=CACHE_LESS,
        pid=os.getpid(),
    )


@app.post("/think", response_model=ThinkResponse)
async def think(req: ThinkRequest) -> ThinkResponse:
    if not model_ready:
        raise HTTPException(
            status_code=503,
            detail="SpikingBrain model not ready (check /health)",
        )
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is empty")

    n_classes = int(os.environ.get("Q_SPEACE_BRAIN_NCLASSES", "3"))
    async with model_lock:
        try:
            return await asyncio.to_thread(_think_sync, req, n_classes)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except Exception as exc:
            # OOM, CUDA error, etc. — surface as 503 so the client can
            # fall back without dumping a 500 stack trace.
            print(
                f"[sidecar] /think failed: {exc.__class__.__name__}: {exc}",
                file=sys.stderr,
            )
            raise HTTPException(
                status_code=503,
                detail=f"inference error: {exc.__class__.__name__}",
            )


def main() -> None:
    import argparse

    import uvicorn

    global CACHE_LESS

    ap = argparse.ArgumentParser(
        prog="spiking_brain_server",
        description=(
            "FastAPI sidecar for SpikingBrain-7B on RTX 3060 6 GB. "
            "Use --no-cache to force forward-singles generation (T-SPB-0B fix): "
            "avoids the cache sliding window degradation at ~10x cost in latency."
        ),
    )
    ap.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=SIDECAR_PORT,
                    help=f"bind port (default {SIDECAR_PORT}; env SPB_SIDECAR_PORT)")
    ap.add_argument("--no-cache", dest="no_cache", action="store_true",
                    help="force cache-less generation (single forward per token)")
    args = ap.parse_args()

    if args.no_cache:
        CACHE_LESS = True

    uvicorn.run(
        "spiking_brain_server.server:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
