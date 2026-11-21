"""Build public verifier configuration for an Auth0-compatible issuer; no credentials read."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from q_speace.remote_mcp.config import HTTPConfig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--issuer", required=True, help="Exact token issuer, including trailing slash if applicable"
    )
    parser.add_argument(
        "--resource", required=True, help="Actual public HTTPS MCP URL ending in /mcp"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Refusing to replace operator configuration")
    for value in (args.issuer, args.resource):
        url = urlsplit(value)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Canonical HTTPS issuer/resource required")
    # This helper intentionally targets Auth0's documented JWKS location.
    # Other identity providers may require a different discovery integration.
    response = httpx.get(
        args.issuer.rstrip("/") + "/.well-known/jwks.json", timeout=15, follow_redirects=False
    )
    response.raise_for_status()
    keys = {}
    for item in response.json()["keys"]:
        if (
            item.get("kty") != "RSA"
            or item.get("use", "sig") != "sig"
            or item.get("alg", "RS256") != "RS256"
        ):
            continue
        key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(item))
        if not isinstance(key, RSAPublicKey):
            raise ValueError("JWKS must contain public keys only")
        kid = item["kid"]
        if kid in keys:
            raise ValueError("Duplicate signing key identifier")
        keys[kid] = key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
    config = HTTPConfig(
        issuer=args.issuer,
        resource=args.resource,
        public_keys=keys,
        audit_path=Path("/tmp/qspeace/audit.sqlite"),
        host="0.0.0.0",
        port=7860,
        allowed_hosts=[urlsplit(args.resource).netloc],
        principal_workers=1,
        total_workers=1,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = config.model_dump(mode="json")
    # The target is Linux even when this helper runs on Windows.
    payload["audit_path"] = "/tmp/qspeace/audit.sqlite"
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("Saved public verification configuration to", args.output.resolve())
    print("No client secret, access token, or private signing key was requested or stored.")


if __name__ == "__main__":
    main()
