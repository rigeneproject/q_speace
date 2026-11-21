"""Container launch using explicit operator-provided public verifier configuration."""

from __future__ import annotations

import os

import uvicorn

from q_speace.remote_mcp.config import HTTPConfig
from q_speace.remote_mcp.server import create_app


def main() -> None:
    config = HTTPConfig.model_validate_json(os.environ["QSPEACE_HTTP_CONFIG_JSON"])
    if (
        config.host != "0.0.0.0"
        or not config.resource.startswith("https://")
        or not config.issuer.startswith("https://")
    ):
        raise ValueError("Container requires explicit public HTTPS resource/issuer configuration")
    uvicorn.run(
        create_app(config),
        host=config.host,
        port=int(os.environ.get("PORT", "7860")),
        proxy_headers=False,
        access_log=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
