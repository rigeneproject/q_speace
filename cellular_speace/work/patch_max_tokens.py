"""Port AgentConfig.max_tokens default 4096 -> 8192, with env override."""
import re
from pathlib import Path

CF = Path(r"C:\cellular_speace\speace_agi_team\config.py")
text = CF.read_text(encoding="utf-8")

# Look for the @dataclass definition of AgentConfig and the max_tokens field
old = "max_tokens: int = 4096"
new = "max_tokens: int = 8192  # raised from 4096 to reduce truncated LLM outputs in AGI tasks"

if old in text:
    text = text.replace(old, new, 1)
    CF.write_text(text, encoding="utf-8")
    print("OK: max_tokens 4096 -> 8192 in AgentConfig default")
else:
    print("SKIP: max_tokens default not found; checking current value...")
    import re
    m = re.search(r"max_tokens\s*:\s*int\s*=\s*(\d+)", text)
    if m:
        print("Current max_tokens default =", m.group(1))
    else:
        print("No max_tokens default found")
