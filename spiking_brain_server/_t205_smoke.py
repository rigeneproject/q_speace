from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = os.environ.get("Q_SPEACE_REPO_ROOT", str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, _REPO_ROOT)
os.chdir(_REPO_ROOT)

# Patch N_PROMPTS to 3 for smoke
import spiking_brain_server._t205_measure as m

m.N_PROMPTS = 3
m._default_prompts_orig = m._default_prompts

def _smoke_prompts():
    return [
        "Rispondi in italiano: cos'è la costante di Planck?",
        "In one sentence: what is TCP/IP?",
        "Answer briefly: 5 + 3 * 2 = ?",
    ]
m._default_prompts = _smoke_prompts

# Disable plotting for the smoke (matplotlib may not be there yet)
m.PLOTS_DIR = __import__("pathlib").Path("/tmp/_t205_smoke")
m.CSV_PATH = __import__("pathlib").Path("/tmp/_t205_smoke.csv")

print("[smoke] measuring idle 3s")
pidle = m.measure_idle_power(duration_s=3.0)
print(f"[smoke] P_idle = {pidle:.2f} W")

print("[smoke] running 3 prompts")
rows = m.run(p_idle_w=pidle, coherence=1.0, n_tokens=24)
print(f"[smoke] got {len(rows)} rows")
m.write_csv(rows)
print("[smoke] OK")
