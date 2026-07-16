"""Add retry-on-truncation to AgentBase.chat()."""
from pathlib import Path

AB = Path(r"C:\cellular_speace\speace_agi_team\agent_base.py")
text = AB.read_text(encoding="utf-8")

# Find the chat() definition; insert a retry wrapper right after def chat returns its first response.
# Strategy: wrap the existing chat() with a _chat_with_retry helper.
# We'll add a small helper method right before the existing chat() method and replace the body
# of chat() to use it.
import re

# Insert a new method _chat_with_retry right after the chat() method, then re-route chat() to use it.
helper = (
    "\n    def _chat_with_retry(self, prompt: str, max_retries: int = 2) -> str:\n"
    "        \"\"\"Call self.chat() with a retry-on-truncation policy.\n"
    "\n"
    "        If the response looks truncated (ends mid-sentence, no terminal\n"
    "        punctuation, or signals 'truncated' / 'output parziale' in italian\n"
    "        prompts), the call is retried up to max_retries times with a short\n"
    "        continuation prompt.\n"
    "        \"\"\"\n"
    "        last = self.chat(prompt)\n"
    "        for _ in range(max_retries):\n"
    "            if not self._looks_truncated(last):\n"
    "                return last\n"
    "            cont = self.chat(prompt + \"\\n\\n[Continua esattamente da dove ti sei interrotto.]\")\n"
    "            last = last + \" \" + cont\n"
    "        return last\n"
    "\n"
    "    @staticmethod\n"
    "    def _looks_truncated(text: str) -> bool:\n"
    "        if not text:\n"
    "            return True\n"
    "        t = text.rstrip()\n"
    "        if not t:\n"
    "            return True\n"
    "        if t[-1] not in \".!?)}\\\"':\":\n"
    "            return True\n"
    "        if \"truncat\" in t.lower() or \"parziale\" in t.lower():\n"
    "            return True\n"
    "        return False\n"
)

marker = "    def get_research_history"
if marker in text and "_chat_with_retry" not in text:
    text = text.replace(marker, helper + "\n" + marker, 1)
    AB.write_text(text, encoding="utf-8")
    print("OK: added _chat_with_retry + _looks_truncated to AgentBase")
else:
    print("SKIP: _chat_with_retry already present or marker missing")
