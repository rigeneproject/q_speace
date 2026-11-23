"""T239 Self-Hosted SPEACE Micro Node zero-lock-in local RS256 bootstrap.

Generates operator-owned local RS256 public verification config and a short-lived
scoped bearer token in an untracked directory (default: `.qspeace-micro-node/`)
without requiring Auth0, Render, or any external cloud identity provider.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from examples.mcp_http_dev_setup import generate_dev_bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap a self-hosted SPEACE Micro Node (zero cloud/Auth0 lock-in)."
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path(".qspeace-micro-node"),
        help="Target directory for local config and scoped token (must not already exist).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for the self-hosted MCP HTTP server (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Bind port for the self-hosted MCP HTTP server (default: 8765).",
    )
    args = parser.parse_args()

    out = generate_dev_bundle(args.directory, host=args.host, port=args.port)
    print(f"[micro-node] Self-hosted config generated at: {out['config']}")
    print(f"[micro-node] Scoped local bearer token saved at: {out['token']} (never commit to Git)")
    print("[micro-node] Next steps:")
    print(f"  1. Start server:  python -m q_speace.remote_mcp.server --config {out['config']}")
    print("  2. Certify node:  qspace micro-node certify --output micro_node_evidence.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
