"""T-SPB-0B diagnostic: do_sample=False vs True su SpB-7B NF4.

Confronta:
- Greedy decoding (do_sample=False)
- Sampling (do_sample=True, T=0.7, top_p=0.9)

Verifica se la degradazione `pérdida/cámara` è causata dal sampling
stocastico (sospetto) o dal modello in NF4 con cache sliding window.
"""
import os
import sys
import time

os.environ.setdefault("SPB_SKIP_DISK_PATCHER", "1")
os.environ.setdefault("SPB_MAX_MEMORY", '{"0":"5700MB","cpu":"1500MB"}')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "spiking_brain_server"))

# Install the in-memory patcher BEFORE transformers loads window_attention
import server  # noqa: E402  (sidecar module)

server._install_window_attention_patcher()
server._evict_cached_window_attention()

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_PATH = os.environ.get(
    "Q_SPEACE_SPB_MODEL_PATH",
    os.path.join(os.path.expanduser("~"), "models", "maujim", "spikingbrain-v1-7b-base"),
)
PROMPT = "The capital of France is"
N_TOKENS = 24

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
print(f"Input: {PROMPT!r} ({inp.input_ids.shape[1]} tokens)")

print()
print(f"=== GREEDY (do_sample=False), n_tokens={N_TOKENS} ===")
t0 = time.time()
with torch.no_grad():
    out = m.generate(
        **inp,
        max_new_tokens=N_TOKENS,
        do_sample=False,
        repetition_penalty=1.1,
    )
dt = time.time() - t0
text = tok.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True)
print(f"output: {text!r}")
print(f"latency: {dt:.2f}s ({dt / N_TOKENS:.2f}s/token)")

print()
print(f"=== SAMPLING (do_sample=True, T=0.7, top_p=0.9), n_tokens={N_TOKENS} ===")
torch.manual_seed(42)
t0 = time.time()
with torch.no_grad():
    out = m.generate(
        **inp,
        max_new_tokens=N_TOKENS,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.1,
    )
dt = time.time() - t0
text = tok.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True)
print(f"output: {text!r}")
print(f"latency: {dt:.2f}s ({dt / N_TOKENS:.2f}s/token)")

print()
print(f"=== SAMPLING (do_sample=True, T=0.1, top_p=0.9), n_tokens={N_TOKENS} ===")
torch.manual_seed(42)
t0 = time.time()
with torch.no_grad():
    out = m.generate(
        **inp,
        max_new_tokens=N_TOKENS,
        do_sample=True,
        temperature=0.1,
        top_p=0.9,
        repetition_penalty=1.1,
    )
dt = time.time() - t0
text = tok.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True)
print(f"output: {text!r}")
print(f"latency: {dt:.2f}s ({dt / N_TOKENS:.2f}s/token)")
