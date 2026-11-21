"""English-language connection smoke test; never prints the OAuth access token."""

from __future__ import annotations

import argparse
import asyncio
import json
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def connect(url: str) -> None:
    token = os.environ["QSPEACE_ACCESS_TOKEN"]
    async with (
        httpx.AsyncClient(headers={"Authorization": "Bearer " + token}, timeout=30) as http,
        streamable_http_client(url, http_client=http) as (read, write, session_id),
        ClientSession(read, write) as session,
    ):
        initialized = await session.initialize()
        print("Connected:", initialized.serverInfo.name, initialized.serverInfo.version)
        await session.send_ping()
        names = [tool.name for tool in (await session.list_tools()).tools]
        print("Available tools:", ", ".join(names))
        for name, arguments in (
            ("bcel_lookup", {"concept": "Homeostasis"}),
            ("adaptive_clock_rate", {"coherence_phi": 0.5}),
            (
                "metabolism_cost_eval",
                {"num_qubits": 0, "num_gates": 1, "delta_utility": 2, "delta_entropy_info": 1},
            ),
        ):
            if name not in names:
                print(name, "not granted by this token; skipped")
                continue
            result = await session.call_tool(name, arguments)
            print(name, "isError=", result.isError)
            for content in result.content:
                if content.type == "text":
                    print(
                        json.dumps(json.loads(content.text), indent=2)
                        if not result.isError
                        else content.text
                    )
            if result.isError:
                raise RuntimeError("Tool failed: " + name)
        print("Connection test passed. No actuation was requested.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(connect(args.url), 90))


if __name__ == "__main__":
    main()
