"""Experimental T225 OAuth resource server; no built-in authorization server.

Run with --config containing issuer/resource URLs and pinned RSA public keys.
No Bridge, DAT mutation, GitHub or actuation tools are exposed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import jwt
from mcp import types
from mcp.server.auth.routes import create_protected_resource_routes
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from q_speace.economy.mcp_server import list_tools

from .config import HTTPConfig
from .service import Audit, Execution, ServiceError, SQLiteStateStore
from .worker import SCOPES


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"non_finite_json_constant:{token}")


def bounded(value: Any, depth: int = 0, count: list[int] | None = None) -> None:
    count = [0] if count is None else count
    count[0] += 1
    if depth > 12 or count[0] > 8192:
        raise ValueError("input_structure_limit")
    if isinstance(value, str) and len(value) > 2048:
        raise ValueError("string_limit")
    if (
        isinstance(value, (float, int))
        and not isinstance(value, bool)
        and not -1e12 <= value <= 1e12
    ):
        raise ValueError("numeric_limit")
    if isinstance(value, dict):
        for key, item in value.items():
            bounded(key, depth + 1, count)
            bounded(item, depth + 1, count)
    if isinstance(value, list):
        if len(value) > 256:
            raise ValueError("array_limit")
        for item in value:
            bounded(item, depth + 1, count)


class Endpoint:
    def __init__(self, manager: StreamableHTTPSessionManager) -> None:
        self.manager = manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.manager.handle_request(scope, receive, send)


class Gateway:
    """Auth/scope/owner admission is repeated for each HTTP request, not cached by session."""

    def __init__(
        self,
        app: ASGIApp,
        config: HTTPConfig,
        audit: Audit,
        state_store: SQLiteStateStore | None = None,
    ) -> None:
        self.app, self.config, self.audit = app, config, audit
        self.state_store = state_store
        if state_store is not None:
            self.sessions: dict[str, tuple[str, float, float]] = state_store.load_sessions()
            self.rates: dict[str, tuple[float, float]] = state_store.load_rates()
            self._prune_expired_sessions(self._now())
        else:
            self.sessions = {}
            self.rates = {}
        self.initializing = asyncio.Lock()
        self.metadata_url = (
            config.resource.removesuffix("/mcp") + "/.well-known/oauth-protected-resource/mcp"
        )

    def _now(self) -> float:
        return time.time() if self.state_store is not None else time.monotonic()

    def identity(self, authorization: str) -> tuple[str, set[str]]:
        if not authorization.startswith("Bearer ") or len(authorization) > 8192:
            raise ServiceError("invalid_token", 401)
        token = authorization[7:]
        try:
            header = jwt.get_unverified_header(token)
            key = self.config.public_keys[header["kid"]]
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.config.resource,
                issuer=self.config.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
            subject = claims["sub"]
            scopes = claims.get("scope", "")
            if (
                not isinstance(subject, str)
                or not subject
                or len(subject) > 256
                or not isinstance(scopes, str)
            ):
                raise ValueError("invalid_claims")
            owner = hashlib.sha256(
                (self.config.tenant + "\0" + self.config.issuer + "\0" + subject).encode()
            ).hexdigest()
            return owner, set(scopes.split())
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise ServiceError("invalid_token", 401) from exc

    def rate(self, owner: str) -> None:
        now = self._now()
        if owner not in self.rates and len(self.rates) >= 4096:
            self.rates = {k: v for k, v in self.rates.items() if now - v[1] < 60}
            if self.state_store is not None:
                self.state_store.prune_rates(now - 60)
            if len(self.rates) >= 4096:
                raise ServiceError("principal_capacity", 503)
        tokens, previous = self.rates.get(owner, (float(self.config.burst), now))
        elapsed = max(0.0, now - previous)
        tokens = min(self.config.burst, tokens + elapsed * self.config.requests_per_minute / 60)
        self.rates[owner] = (tokens, now)
        if self.state_store is not None:
            self.state_store.put_rate(owner, tokens, now)
        if tokens < 1:
            raise ServiceError("rate_limit", 429)
        self.rates[owner] = (tokens - 1, now)
        if self.state_store is not None:
            self.state_store.put_rate(owner, tokens - 1, now)

    async def error(self, scope: Scope, receive: Receive, send: Send, error: ServiceError) -> None:
        headers = {"Cache-Control": "no-store"}
        if error.status in (401, 403):
            kind = "invalid_token" if error.status == 401 else "insufficient_scope"
            headers["WWW-Authenticate"] = (
                f'Bearer resource_metadata="{self.metadata_url}", error="{kind}"'
            )
        if error.status == 429:
            headers["Retry-After"] = "1"
        await JSONResponse({"error": error.code}, status_code=error.status, headers=headers)(
            scope, receive, send
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        if request.headers.get("host", "") not in self.config.allowed_hosts:
            await self.error(scope, receive, send, ServiceError("invalid_host", 403))
            return
        if (
            request.headers.get("origin") is not None
            and request.headers["origin"] not in self.config.allowed_origins
        ):
            await self.error(scope, receive, send, ServiceError("invalid_origin", 403))
            return
        if scope["path"] != "/mcp":
            await self.app(scope, receive, send)
            return
        try:
            owner, scopes = self.identity(request.headers.get("authorization", ""))
            self.rate(owner)
            scope["qspeace.owner"], scope["qspeace.scopes"] = owner, scopes
            body = bytearray()
            message: dict[str, Any] = {}
            if scope["method"] == "POST":
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 65536:
                        raise ServiceError("body_limit", 413)
                try:
                    decoded = json.loads(body, parse_constant=_reject_json_constant)
                    bounded(decoded)
                    if not isinstance(decoded, dict):
                        raise ValueError("invalid_message")
                    message = decoded
                except (ValueError, RecursionError, UnicodeError) as exc:
                    raise ServiceError("invalid_message", 400) from exc
            method = message.get("method", "")
            sid = request.headers.get("mcp-session-id")
            now = self._now()
            if sid:
                entry = self.sessions.get(sid)
                if entry is None or entry[0] != owner:
                    raise ServiceError("unknown_session", 404)
                if (
                    now - entry[2] > self.config.session_idle_seconds
                    or now - entry[1] > self.config.session_max_seconds
                ):
                    del self.sessions[sid]
                    if self.state_store is not None:
                        self.state_store.delete_session(sid)
                    raise ServiceError("unknown_session", 404)
                self.sessions[sid] = (owner, entry[1], now)
                if self.state_store is not None:
                    self.state_store.put_session(sid, owner, entry[1], now)
            elif method != "initialize" and scope["method"] != "GET":
                raise ServiceError("session_required", 400)
            if method == "initialize" and sid:
                raise ServiceError("already_initialized", 400)
            if scope["method"] == "GET":
                await self.error(scope, receive, send, ServiceError("sse_not_offered", 405))
                return
            call = method == "tools/call"
            if call:
                params = message.get("params")
                if "id" not in message or not isinstance(params, dict):
                    raise ServiceError("invalid_call", 400)
                name = params.get("name")
                if not isinstance(name, str) or name not in SCOPES:
                    raise ServiceError("tool_not_available", 403)
                if SCOPES[name] not in scopes:
                    raise ServiceError("scope_required", 403)
            consumed = False

            async def replay() -> Message:
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            collected: list[Message] = []

            async def capture(item: Message) -> None:
                collected.append(item)

            trace = secrets.token_hex(16)
            if call:
                self.audit.append(
                    {
                        "event": "intent",
                        "request": trace,
                        "principal_hash": owner,
                        "tool": message["params"]["name"],
                        "input_hash": hashlib.sha256(bytes(body)).hexdigest(),
                    }
                )
            if method == "initialize":
                async with self.initializing:
                    self._prune_expired_sessions(now)
                    if (
                        sum(e[0] == owner for e in self.sessions.values())
                        >= self.config.sessions_per_principal
                    ):
                        raise ServiceError("session_limit", 429)
                    await self.app(scope, replay, capture)
                    self.record_session(collected, owner)
            else:
                await self.app(scope, replay, capture)
            if call:
                output = b"".join(m.get("body", b"") for m in collected)
                self.audit.append(
                    {
                        "event": "result",
                        "request": trace,
                        "principal_hash": owner,
                        "output_hash": hashlib.sha256(output).hexdigest(),
                    }
                )
            if (
                scope["method"] == "DELETE"
                and sid
                and collected
                and collected[0].get("status", 500) < 300
            ):
                self.sessions.pop(sid, None)
                if self.state_store is not None:
                    self.state_store.delete_session(sid)
            if call:
                try:
                    result_body = json.loads(b"".join(item.get("body", b"") for item in collected))
                    result = result_body.get("result", {})
                    content = result.get("content", [])
                    if (
                        result.get("isError")
                        and content
                        and content[0].get("text") == "workers_exhausted"
                    ):
                        await self.error(
                            scope, receive, send, ServiceError("workers_exhausted", 429)
                        )
                        return
                except (ValueError, TypeError, AttributeError):
                    raise ServiceError("invalid_worker_response") from None
            for item in collected:
                if item["type"] == "http.response.start":
                    item["headers"] = [*item.get("headers", []), (b"cache-control", b"no-store")]
                await send(item)
        except ServiceError as exc:
            await self.error(scope, receive, send, exc)

    def _prune_expired_sessions(self, now: float) -> None:
        expired = [
            sid
            for sid, (_, created, last_seen) in self.sessions.items()
            if (
                now - last_seen > self.config.session_idle_seconds
                or now - created > self.config.session_max_seconds
            )
        ]
        for sid in expired:
            del self.sessions[sid]
        if expired and self.state_store is not None:
            self.state_store.delete_sessions(expired)

    def record_session(self, messages: list[Message], owner: str) -> None:
        if not messages or messages[0].get("status") != 200:
            return
        headers = dict(messages[0].get("headers", []))
        sid = headers.get(b"mcp-session-id")
        if sid:
            now = self._now()
            sid_str = sid.decode()
            self.sessions[sid_str] = (owner, now, now)
            if self.state_store is not None:
                self.state_store.put_session(sid_str, owner, now, now)


def create_app(config: HTTPConfig) -> Gateway:
    server: Server[Any, Any] = Server("q-speace-http", version="0.1.0")
    execution = Execution(config)

    @server.list_tools()
    async def tools() -> list[types.Tool]:
        request = server.request_context.request
        if request is None:
            raise RuntimeError("HTTP request context required")
        allowed = request.scope["qspeace.scopes"]
        return [
            types.Tool.model_validate(t)
            for t in list_tools()
            if t["name"] in SCOPES and SCOPES[t["name"]] in allowed
        ]

    @server.call_tool(validate_input=False)
    async def call(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        request = server.request_context.request
        if request is None:
            raise RuntimeError("HTTP request context required")
        if name not in SCOPES or SCOPES[name] not in request.scope["qspeace.scopes"]:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="permission_denied")], isError=True
            )
        try:
            result = await execution.compute(request.scope["qspeace.owner"], name, arguments)
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(result, allow_nan=False))],
                isError=False,
            )
        except ServiceError as exc:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=exc.code)], isError=True
            )

    manager = StreamableHTTPSessionManager(
        server,
        json_response=True,
        session_idle_timeout=config.session_idle_seconds,
        max_sessions=64,
        max_request_body_size=65536,
        security_settings=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=config.allowed_hosts,
            allowed_origins=config.allowed_origins,
        ),
    )

    @asynccontextmanager
    async def lifespan(app: Starlette) -> Any:
        try:
            async with manager.run():
                yield
        finally:
            audit.db.close()
            if state_store is not None:
                state_store.close()

    async def home(request: Request) -> JSONResponse:
        return JSONResponse({"service": "q-speace", "profile": "experimental", "mcp": "/mcp"})

    routes = [Route("/", home), Route("/mcp", Endpoint(manager))]
    routes.extend(
        create_protected_resource_routes(
            AnyHttpUrl(config.resource),
            [AnyHttpUrl(config.issuer)],
            scopes_supported=list(set(SCOPES.values())),
        )
    )
    audit = Audit(config.audit_path)
    state_store = (
        SQLiteStateStore(config.state_db_path) if config.state_db_path is not None else None
    )
    return Gateway(Starlette(routes=routes, lifespan=lifespan), config, audit, state_store)


def main() -> None:
    import os

    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = HTTPConfig.load(args.config)
    port = int(os.environ.get("PORT", config.port))
    uvicorn.run(
        create_app(config),
        host=config.host,
        port=port,
        proxy_headers=False,
        access_log=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
