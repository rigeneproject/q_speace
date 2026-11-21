"""Explicit operator configuration. Public verification keys only; no signing keys."""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


def loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class HTTPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    issuer: str
    resource: str
    public_keys: dict[str, str]
    audit_path: Path
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_hosts: list[str]
    allowed_origins: list[str] = []
    tenant: str = "research"
    requests_per_minute: int = Field(default=60, ge=1, le=600)
    burst: int = Field(default=10, ge=1, le=60)
    worker_seconds: float = Field(default=5, gt=0, le=30)
    principal_workers: int = Field(default=2, ge=1, le=2)
    total_workers: int = Field(default=8, ge=1, le=8)
    sessions_per_principal: int = Field(default=4, ge=1, le=4)
    session_idle_seconds: float = Field(default=1800, gt=0, le=1800)
    session_max_seconds: float = Field(default=28800, gt=0, le=28800)

    @model_validator(mode="after")
    def check_security(self) -> HTTPConfig:
        for value in (self.issuer, self.resource):
            parsed = urlsplit(value)
            if (
                parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or not parsed.hostname
            ):
                raise ValueError("issuer/resource must be canonical URLs without credentials")
            if parsed.scheme != "https" and not (
                parsed.scheme == "http" and loopback(parsed.hostname) and loopback(self.host)
            ):
                raise ValueError("HTTPS required except for a loopback-only prototype")
        if urlsplit(self.resource).path != "/mcp":
            raise ValueError("resource path must be /mcp")
        if (
            not self.public_keys
            or not self.allowed_hosts
            or "*" in self.allowed_hosts
            or "*" in self.allowed_origins
        ):
            raise ValueError("pinned public keys and exact host/origin lists are required")
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

        for key in self.public_keys.values():
            decoded = serialization.load_pem_public_key(key.encode())
            if not isinstance(decoded, RSAPublicKey) or decoded.key_size < 2048:
                raise ValueError("RSA public verification keys >=2048 bits required")
        return self

    @classmethod
    def load(cls, path: Path) -> HTTPConfig:
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))
