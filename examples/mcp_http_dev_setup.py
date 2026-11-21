"""Create loopback-only fixture credentials. This is not an OAuth login server."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(".qspeace-dev"))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    issuer = f"http://127.0.0.1:{args.port}/test-issuer"
    resource = f"http://127.0.0.1:{args.port}/mcp"
    config = {
        "issuer": issuer,
        "resource": resource,
        "public_keys": {"test-only": public},
        "audit_path": str((args.directory / "audit.sqlite").resolve()),
        "allowed_hosts": [f"127.0.0.1:{args.port}", f"localhost:{args.port}"],
        "port": args.port,
        "burst": 60,
    }
    (args.directory / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": issuer,
            "aud": resource,
            "sub": "local-fixture",
            "iat": now,
            "exp": now + 3600,
            "scope": "qspeace:catalog.read qspeace:compute qspeace:simulation.compute",
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-only"},
    )
    token_path = args.directory / "access-token.txt"
    token_path.write_text(token, encoding="utf-8")
    token_path.chmod(0o600)
    print("Created loopback fixture config and a one-hour test token in", args.directory.resolve())
    print("No private signing key was saved. Never deploy this fixture configuration.")


if __name__ == "__main__":
    main()

