"""T-SPB-0B diagnostic v2: cache-less generation vs cached.

If la degradazione è nella cache sliding window fla × transformers,
disabilitare la cache dovrebbe produrre testo pulito.

Test:
- use_cache=True (default generate)
- use_cache=False (forward manuale, ricomputo intero contesto ogni step)
"""
import os
import sys
import time

os.environ.setdefault("SPB_SKIP_DISK_PATCHER", "1")
os.environ.setdefault("SPB_MAX_MEMORY", '{"0":"5700MB","cpu":"1500MB"}')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "spiking_brain_server"))

import server  # noqa: E402

server._install_window_attention_patcher()
server._evict_cached_window_attention()

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_PATH = "/home/roby/models/maujim/spikingbrain-v1-7b-base"
PROMPT = "The capital of France is"
N_TOKENS = 16  # cache-less e' piu' lento, riduciamo per restare nel tempo

print("Loading tokenizer...")
tok = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
print("Loading model (NF4, bf16 compute)...")
t0 = time.time()
m = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True,
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4"),
    device_map="auto",
    max_memory={0: "5700MB", "cpu": "1500MB"},
    torch_dtype=torch.bfloat16,
)
print(f"Loaded in {time.time() - t0:.1f}s")

inp = tok(PROMPT, return_tensors="pt").to(m.device)
print(f"Input: {PROMPT!r} ({inp.input_ids.shape[1]} tokens)\n")


def generate_no_cache(model, input_ids_tensor, base_len, max_new_tokens):
    """Cache-less greedy: forward sull'intero contesto ad ogni step.

    Args:
        input_ids_tensor: torch.Tensor shape (1, base_len).
        base_len: int lunghezza del prompt iniziale.
    """
    cur = input_ids_tensor
    out_ids = cur[0].tolist()
    for _ in range(max_new_tokens):
        with torch.no_grad():
            logits = model(cur, use_cache=False).logits
        next_id = int(logits[0, -1].argmax())
        out_ids.append(next_id)
        cur = torch.cat([cur, torch.tensor([[next_id]], device=cur.device)], dim=1)
    return out_ids[base_len:]


def generate_with_cache(model, inputs_dict, base_len, max_new_tokens):
    """Default cache-based greedy (confronto)."""
    out = model.generate(
        **inputs_dict,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        use_cache=True,
        repetition_penalty=1.1,
    )
    return out[0][base_len:].tolist()


print(f"=== CACHE-LESS GREEDY (no_cache, greedy), n_tokens={N_TOKENS} ===")
base_len = inp.input_ids.shape[1]
t0 = time.time()
ids = generate_no_cache(m, inp.input_ids, base_len, N_TOKENS)
dt = time.time() - t0
text = tok.decode(ids, skip_special_tokens=True)
print(f"output: {text!r}")
print(f"latency: {dt:.2f}s ({dt / N_TOKENS:.2f}s/token)")

print()
print(f"=== WITH-CACHE GREEDY (default generate), n_tokens={N_TOKENS} ===")
t0 = time.time()
ids = generate_with_cache(m, inp, base_len, N_TOKENS)
dt = time.time() - t0
text = tok.decode(ids, skip_special_tokens=True)
print(f"output: {text!r}")
print(f"latency: {dt:.2f}s ({dt / N_TOKENS:.2f}s/token)")
