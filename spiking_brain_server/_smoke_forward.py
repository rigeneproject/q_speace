"""One-shot forward pass test against the loaded model.

Used during T1 smoke-test to isolate inference errors from server wiring.

Imports ``spiking_brain_server.server`` FIRST so that the
``window_attention`` meta-path patcher is installed before HF's
dynamic-module loader pulls in the buggy module via ``trust_remote_code``.
"""
import os
import sys

os.environ.setdefault("SPB_DEVICE_MAP", '{"":0}')

# Make the repo root importable so we can reach spiking_brain_server.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# IMPORTANT: must come before any transformers/auto import.
from spiking_brain_server import server  # noqa: F401  -- installs meta-path hook

# Apply the on-disk patch + evict cached module BEFORE transformers
# dynamic-module loader reads window_attention.py.
server._evict_cached_window_attention()

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL = "/home/roby/models/maujim/spikingbrain-v1-7b-base"
tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True, padding_side="left")
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
m = AutoModelForCausalLM.from_pretrained(
    MODEL,
    trust_remote_code=True,
    quantization_config=bnb,
    device_map={"": 0},
    torch_dtype=torch.bfloat16,
)
m.eval()
print("loaded, n_params:", sum(p.numel() for p in m.parameters()))

inp = tok(
    ["question: What is coherence_phi?\nanswer:"],
    return_tensors="pt",
    padding=True,
).to("cuda")
try:
    with torch.no_grad():
        out = m.generate(
            **inp,
            max_new_tokens=16,
            do_sample=False,
            return_dict_in_generate=True,
        )
    new_ids = out.sequences[0][inp.input_ids.shape[1]:]
    print("OK:", repr(tok.decode(new_ids, skip_special_tokens=True)))
except Exception:
    import traceback

    traceback.print_exc()
