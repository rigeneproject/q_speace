"""Trigger the failing _upad_input call with the actual SpikingBrain model
and dump the full traceback to find which file + line needs patching.
"""
import sys
import traceback

sys.path.insert(0, "/home/roby/.venvs/spikingbrain/lib/python3.12/site-packages")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
MODEL = "/home/roby/models/maujim/spikingbrain-v1-7b-base"

print("Loading tokenizer...", flush=True)
tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True, padding_side="left")
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

print("Loading model...", flush=True)
m = AutoModelForCausalLM.from_pretrained(
    MODEL,
    trust_remote_code=True,
    quantization_config=bnb,
    device_map={"": 0},
    torch_dtype=torch.bfloat16,
)
m.eval()

print("Forward pass with short prompt...", flush=True)
prompt = "question: What is coherence_phi?\nanswer:"
inp = tok([prompt], return_tensors="pt", padding=True).to("cuda")
try:
    with torch.no_grad():
        out = m.generate(**inp, max_new_tokens=8, do_sample=False, return_dict_in_generate=True)
    print("OK:", tok.decode(out.sequences[0][inp.input_ids.shape[1]:], skip_special_tokens=True))
except Exception:
    traceback.print_exc()
    sys.exit(1)
