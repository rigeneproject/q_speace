"""Probe diagnostico: capire perché il modello produce EOS al primo token.

Tre esperimenti:
1. Genera con eos_token_id=None (forza 16 token)
2. Genera con un prompt più colloquiale (Hello, how are you?)
3. Forward senza generate: stampa top-5 logits del primo decode step
"""
from __future__ import annotations

import time
from pathlib import Path
import site

# patch fla-bitnet (idempotente)
for p in site.getsitepackages():
    cand = Path(p) / "fla" / "models" / "bitnet" / "__init__.py"
    if cand.exists():
        txt = cand.read_text()
        if "exist_ok=True" not in txt:
            txt = txt.replace(
                "AutoConfig.register(BitNetConfig.model_type, BitNetConfig)",
                "AutoConfig.register(BitNetConfig.model_type, BitNetConfig, exist_ok=True)",
            ).replace(
                "AutoModel.register(BitNetConfig, BitNetModel)",
                "AutoModel.register(BitNetConfig, BitNetModel, exist_ok=True)",
            ).replace(
                "AutoModelForCausalLM.register(BitNetConfig, BitNetForCausalLM)",
                "AutoModelForCausalLM.register(BitNetConfig, BitNetForCausalLM, exist_ok=True)",
            )
            cand.write_text(txt)
        break

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_DIR = Path("/home/roby/models/maujim/spikingbrain-v1-7b-base")
tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
print(f"[probe] tokenizer: vocab={tok.vocab_size}, eos={tok.eos_token_id}, pad={tok.pad_token_id}")

model = AutoModelForCausalLM.from_pretrained(
    str(MODEL_DIR),
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    ),
    device_map="auto",
    max_memory={0: "5.7GB", "cpu": "1.5GB"},
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
)
model.eval()
print(f"[probe] VRAM: {torch.cuda.memory_allocated()/1e9:.2f} GB")

# --- ESPERIMENTO 1: prompt originale, NO early-stop ---
print("\n=== ESP1: prompt originale, no eos early-stop ===")
prompt = "Explain quantum entanglement in one sentence."
inputs = tok(prompt, return_tensors="pt").to("cuda")
with torch.no_grad():
    t0 = time.time()
    out = model.generate(
        **inputs,
        max_new_tokens=16,
        do_sample=False,
        temperature=None,
        top_p=None,
        eos_token_id=-1,  # disabilita stop su EOS
        pad_token_id=tok.eos_token_id,
    )
    print(f"[probe] {time.time()-t0:.1f}s, gen tokens: {out.shape[1]-inputs.input_ids.shape[1]}")
    print(f"[probe] input_ids shape: {tuple(inputs.input_ids.shape)}")
    print(f"[probe] token ids generati: {out[0, inputs.input_ids.shape[1]:].tolist()}")
    print(f"[probe] testo: {tok.decode(out[0, inputs.input_ids.shape[1]:], skip_special_tokens=False)!r}")

# --- ESPERIMENTO 2: prompt colloquiale ---
print("\n=== ESP2: prompt colloquiale ===")
inputs = tok("Hello, how are you?", return_tensors="pt").to("cuda")
with torch.no_grad():
    t0 = time.time()
    out = model.generate(
        **inputs,
        max_new_tokens=16,
        do_sample=False,
        temperature=None,
        top_p=None,
        eos_token_id=-1,
        pad_token_id=tok.eos_token_id,
    )
    print(f"[probe] {time.time()-t0:.1f}s")
    print(f"[probe] token ids generati: {out[0, inputs.input_ids.shape[1]:].tolist()}")
    print(f"[probe] testo: {tok.decode(out[0, inputs.input_ids.shape[1]:], skip_special_tokens=False)!r}")

# --- ESPERIMENTO 3: forward manuale, top-5 logits ---
print("\n=== ESP3: forward manuale, top-5 logits del primo decode step ===")
prompt = "The capital of France is"
input_ids = tok(prompt, return_tensors="pt").input_ids.to("cuda")
print(f"[probe] input_ids: {input_ids.tolist()[0]}")
print(f"[probe] decoded:  {tok.decode(input_ids[0])!r}")
with torch.no_grad():
    t0 = time.time()
    out = model(input_ids)
    print(f"[probe] forward {time.time()-t0:.1f}s")
    logits = out.logits[0, -1, :]  # ultimo token
    top5 = torch.topk(logits, 5)
    print(f"[probe] top-5 logits (no softmax):")
    for rank, (val, idx) in enumerate(zip(top5.values.tolist(), top5.indices.tolist())):
        print(f"  rank {rank+1}: idx={idx} val={val:.3f}  tok={tok.decode([idx])!r}")
    top5_prob = torch.topk(torch.softmax(logits.float(), -1), 5)
    print(f"[probe] top-5 probs:")
    for rank, (val, idx) in enumerate(zip(top5_prob.values.tolist(), top5_prob.indices.tolist())):
        print(f"  rank {rank+1}: p={val:.4f}  tok={tok.decode([idx])!r}")

# --- ESPERIMENTO 4: forward con sample per vedere se greedy sta degenerando ---
print("\n=== ESP4: greedy con temperature=1.0 ===")
inputs = tok("The capital of France is", return_tensors="pt").to("cuda")
with torch.no_grad():
    t0 = time.time()
    out = model.generate(
        **inputs,
        max_new_tokens=8,
        do_sample=True,
        temperature=1.0,
        top_p=0.9,
        eos_token_id=-1,
        pad_token_id=tok.eos_token_id,
    )
    print(f"[probe] {time.time()-t0:.1f}s")
    print(f"[probe] testo: {tok.decode(out[0, inputs.input_ids.shape[1]:], skip_special_tokens=False)!r}")

del model
torch.cuda.empty_cache()
print("\n[probe] done")
