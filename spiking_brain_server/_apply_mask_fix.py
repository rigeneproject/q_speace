"""Apply mask shape fix + indices long cast to window_attention.py.

Fix #1 (mask shape):
- attn_mask was created with shape (B, H, q_len, head_dim) — wrong when k_len
  differs from head_dim (e.g. varlen with cache).
- Correct shape: (B, H, q_len, k_len) where k_len = k_b.shape[2] / k_.shape[2].

Fix #2 (indices dtype):
- pad_input uses index_copy_ which expects a long tensor.
- _upad_input returns int32 indices; .to() preserves dtype.
- Add .long() cast before index_copy_.

This script is idempotent.
"""
import sys
from pathlib import Path

FILES = [
    Path("/home/roby/.cache/huggingface/modules/transformers_modules/spikingbrain-v1-7b-base/window_attention.py"),
    Path("/home/roby/models/maujim/spikingbrain-v1-7b-base/window_attention.py"),
]

# Fix #1: mask shape
old1 = "attn_mask = torch.zeros_like(q_b, dtype=q.dtype).masked_fill(~mask, float('-inf'))"
new1 = ("attn_mask = torch.zeros("
        "(q_b.shape[0], q_b.shape[1], q_b.shape[2], k_b.shape[2]), "
        "dtype=q.dtype, device=q.device"
        ").masked_fill(~mask, float('-inf'))")

old2 = "attn_mask = torch.zeros_like(q_, dtype=q.dtype).masked_fill(~mask, float('-inf'))"
new2 = ("attn_mask = torch.zeros("
        "(q_.shape[0], q_.shape[1], q_.shape[2], k_.shape[2]), "
        "dtype=q.dtype, device=q.device"
        ").masked_fill(~mask, float('-inf'))")

# Fix #2: indices long cast
old3 = "out.index_copy_(0, indices.to(hidden_states.device), hidden_states)"
new3 = "out.index_copy_(0, indices.to(hidden_states.device).long(), hidden_states)"

for p in FILES:
    if not p.exists():
        print(f"SKIP (missing): {p}")
        continue
    src = p.read_text()
    before = src
    n1 = src.count(old1)
    src = src.replace(old1, new1)
    n2 = src.count(old2)
    src = src.replace(old2, new2)
    n3 = src.count(old3)
    src = src.replace(old3, new3)
    if src == before:
        print(f"NO-OP: {p}")
    else:
        p.write_text(src)
        print(f"PATCHED: {p}  (mask1={n1}, mask2={n2}, indices={n3})")
print("done")
