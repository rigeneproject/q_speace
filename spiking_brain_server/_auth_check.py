#!/usr/bin/env python3
"""Auth check for HF token. Run from WSL2."""
import os
import sys

from huggingface_hub import HfApi

token = os.environ.get("HF_TOKEN", "")
if not token:
    print("ERROR: HF_TOKEN not set", file=sys.stderr)
    sys.exit(1)

try:
    me = HfApi(token=token).whoami()
    print("auth OK:", me.get("name"))
    print("orgs:", [o["name"] for o in me.get("orgs", [])])
    sys.exit(0)
except Exception as e:
    print("auth FAILED:", type(e).__name__, str(e)[:200], file=sys.stderr)
    sys.exit(1)
