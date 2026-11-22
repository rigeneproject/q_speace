"""Bounded advisory agent for testing Q-SPEACE MCP Streamable HTTP connections.

Implements the client workflow documented in the Q-SPEACE MCP guide (T225):
  1. Verifies OAuth protected-resource metadata and unauthenticated 401 gating.
  2. Acquires or uses a Bearer token (in memory only; never prints or logs secrets).
  3. Initializes an MCP Streamable HTTP session (official MCP SDK), pings, and
     discovers scope-filtered tools.
  4. Runs a client-governed advisory loop applying separate energy and Sevo gates,
     adaptive clock pacing, and the documented reference tool calls.
  5. Verifies invalid-argument recovery (isError=True followed by a live ping)
     and confirms mutating DAT tools are not exposed.

Supports both a remote T225 endpoint (Auth0 client_credentials or Bearer token)
and an isolated ``--local-demo`` loopback server for offline verification.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_ENDPOINT = "https://q-speace-mcp.onrender.com/mcp"
DEFAULT_TOKEN_URL = "https://dev-imfska6viiq1ehqw.us.auth0.com/oauth/token"
FORBIDDEN_REMOTE_TOOLS = frozenset({"dat_mint", "dat_spend"})


@dataclass(frozen=True)
class PolicyConfig:
    """Client-owned hard bounds (Section 5 of the Q-SPEACE MCP guide)."""

    max_estimated_energy_joules: float = 10.0
    sevo_threshold: float = 1.5
    delay_scale_seconds: float = 0.5
    min_delay_seconds: float = 0.0
    max_delay_seconds: float = 0.25
    min_step_interval_seconds: float = 0.35
    apply_delay: bool = False
    http_timeout_seconds: float = 60.0
    total_timeout_seconds: float = 180.0


@dataclass
class StepRecord:
    """One auditable agent check (never stores credentials or Bearer tokens)."""

    step: str
    status: str  # "passed" | "skipped" | "failed"
    elapsed_ms: float
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentReport:
    """Structured outcome of a full connection verification run."""

    endpoint: str
    server_name: str | None = None
    server_version: str | None = None
    granted_tools: list[str] = field(default_factory=list)
    steps: list[StepRecord] = field(default_factory=list)
    passed: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "server_name": self.server_name,
            "server_version": self.server_version,
            "granted_tools": self.granted_tools,
            "passed": self.passed,
            "error": self.error,
            "steps": [asdict(s) for s in self.steps],
        }


class TokenProvider:
    """Caches an OAuth access token in memory without logging or persisting it."""

    def __init__(
        self,
        *,
        endpoint: str,
        token_url: str,
        access_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._endpoint = endpoint
        self._token_url = token_url
        self._access_token = access_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout_seconds
        self._expires_at = float("inf") if access_token else 0.0

    async def get_token(self) -> str:
        now = time.monotonic()
        if self._access_token and now < self._expires_at - 30.0:
            return self._access_token
        if not self._client_id or not self._client_secret:
            raise RuntimeError(
                "Missing credentials: set QSPEACE_ACCESS_TOKEN, or QSPEACE_CLIENT_ID and "
                "QSPEACE_CLIENT_SECRET, or pass --credentials-file, or use --local-demo."
            )
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self._token_url,
                json={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "audience": self._endpoint,
                },
            )
            response.raise_for_status()
            payload = response.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("OAuth token endpoint did not return a valid access_token")
        expires_in = float(payload.get("expires_in", 900))
        self._access_token = token
        self._expires_at = now + max(expires_in, 60.0)
        return token


def _metadata_url_for(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    return f"{parsed.scheme}://{parsed.netloc}/.well-known/oauth-protected-resource{parsed.path}"


def _extract_json_text(result: Any) -> dict[str, Any]:
    for item in result.content:
        if getattr(item, "type", None) == "text":
            parsed = json.loads(item.text)
            if isinstance(parsed, dict):
                return parsed
    raise ValueError("Tool response did not contain a JSON object text block")


class QSpeaceConnectionAgent:
    """Advisory test agent exercising the Q-SPEACE MCP HTTP protocol & policies."""

    def __init__(
        self,
        *,
        endpoint: str,
        token_provider: TokenProvider,
        policy: PolicyConfig | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.token_provider = token_provider
        self.policy = policy or PolicyConfig()

    async def _record_step(
        self,
        report: AgentReport,
        step: str,
        coro: Any,
    ) -> Any:
        t0 = time.monotonic()
        try:
            detail = await coro
            elapsed = round((time.monotonic() - t0) * 1000.0, 2)
            report.steps.append(
                StepRecord(step=step, status="passed", elapsed_ms=elapsed, detail=detail)
            )
            return detail
        except Exception as exc:
            elapsed = round((time.monotonic() - t0) * 1000.0, 2)
            report.steps.append(
                StepRecord(
                    step=step,
                    status="failed",
                    elapsed_ms=elapsed,
                    detail={"error": f"{type(exc).__name__}: {exc}"},
                )
            )
            raise

    async def run(self) -> AgentReport:
        report = AgentReport(endpoint=self.endpoint)
        try:
            await self._check_public_surface(report)
            token = await self.token_provider.get_token()
            await self._run_authenticated_session(report, token)
            report.passed = all(s.status in {"passed", "skipped"} for s in report.steps)
        except Exception as exc:
            report.passed = False
            report.error = f"{type(exc).__name__}: {exc}"
        return report

    async def _check_public_surface(self, report: AgentReport) -> None:
        meta_url = _metadata_url_for(self.endpoint)
        async with httpx.AsyncClient(timeout=self.policy.http_timeout_seconds) as client:

            async def check_metadata() -> dict[str, Any]:
                r = await client.get(meta_url)
                r.raise_for_status()
                body = r.json()
                if body.get("resource") != self.endpoint:
                    raise ValueError(f"resource mismatch: {body.get('resource')!r}")
                return {
                    "status_code": r.status_code,
                    "authorization_servers": body.get("authorization_servers", []),
                    "scopes_supported": sorted(body.get("scopes_supported", [])),
                }

            async def check_unauth_rejection() -> dict[str, Any]:
                r = await client.post(
                    self.endpoint,
                    json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                )
                if r.status_code != 401:
                    raise ValueError(f"expected 401 without token, got {r.status_code}")
                www_auth = r.headers.get("www-authenticate", "")
                if "resource_metadata=" not in www_auth:
                    raise ValueError("missing resource_metadata in WWW-Authenticate header")
                return {"status_code": r.status_code, "has_resource_metadata_header": True}

            await self._record_step(report, "protected_resource_metadata", check_metadata())
            await self._record_step(
                report, "unauthenticated_rpc_rejected", check_unauth_rejection()
            )

    async def _run_authenticated_session(self, report: AgentReport, token: str) -> None:
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(
            headers=headers, timeout=self.policy.http_timeout_seconds
        ) as http:

            async def check_get_405() -> dict[str, Any]:
                r = await http.get(self.endpoint)
                if r.status_code != 405:
                    raise ValueError(f"expected 405 on authenticated GET /mcp, got {r.status_code}")
                return {"status_code": r.status_code}

            await self._record_step(report, "authenticated_get_returns_405", check_get_405())

            async with (
                streamable_http_client(self.endpoint, http_client=http) as (
                    read,
                    write,
                    _,
                ),
                ClientSession(read, write) as session,
            ):

                async def do_init() -> dict[str, Any]:
                    init = await session.initialize()
                    report.server_name = init.serverInfo.name
                    report.server_version = init.serverInfo.version
                    await session.send_ping()
                    return {
                        "server_name": init.serverInfo.name,
                        "server_version": init.serverInfo.version,
                        "ping": "ok",
                    }

                async def do_discover() -> dict[str, Any]:
                    tools = (await session.list_tools()).tools
                    names = sorted(t.name for t in tools)
                    forbidden = sorted(FORBIDDEN_REMOTE_TOOLS.intersection(names))
                    if forbidden:
                        raise ValueError(f"forbidden remote tools exposed: {forbidden}")
                    report.granted_tools = names
                    return {"tool_count": len(names), "tools": names}

                await self._record_step(report, "mcp_initialize_and_ping", do_init())
                await self._record_step(report, "mcp_discover_tools", do_discover())

                granted = set(report.granted_tools)
                await self._run_policy_workflow(report, session, granted)
                await self._check_invalid_arg_recovery(report, session, granted)
                if self.policy.min_step_interval_seconds > 0:
                    await asyncio.sleep(self.policy.min_step_interval_seconds)

    async def _call_if_granted(
        self,
        report: AgentReport,
        session: ClientSession,
        granted: set[str],
        step: str,
        tool_name: str,
        arguments: dict[str, Any],
        validator: Any = None,
    ) -> dict[str, Any] | None:
        if tool_name not in granted:
            report.steps.append(
                StepRecord(
                    step=step,
                    status="skipped",
                    elapsed_ms=0.0,
                    detail={"reason": f"tool '{tool_name}' not granted by token scopes"},
                )
            )
            return None

        async def invoke() -> dict[str, Any]:
            result = await session.call_tool(tool_name, arguments)
            if result.isError:
                raise RuntimeError(f"{tool_name} returned isError=True: {result.content}")
            data = _extract_json_text(result)
            if validator is not None:
                extra = validator(data)
                if isinstance(extra, dict):
                    return {**data, **extra}
            return data

        out: dict[str, Any] = await self._record_step(report, step, invoke())
        if self.policy.min_step_interval_seconds > 0:
            await asyncio.sleep(self.policy.min_step_interval_seconds)
        return out

    async def _run_policy_workflow(
        self,
        report: AgentReport,
        session: ClientSession,
        granted: set[str],
    ) -> None:
        # 1. Concept discipline (BCEL catalog)
        def check_bcel(data: dict[str, Any]) -> dict[str, Any]:
            entries = data.get("entries", [])
            if not entries or entries[0].get("classification") != "functional":
                raise ValueError(f"unexpected BCEL payload: {data}")
            return {"verified_classification": entries[0]["classification"]}

        await self._call_if_granted(
            report,
            session,
            granted,
            "tool_bcel_lookup",
            "bcel_lookup",
            {"concept": "Homeostasis"},
            validator=check_bcel,
        )

        # 2. Adaptive pacing policy (Section 5)
        planned_delay = 0.0

        def check_clock(data: dict[str, Any]) -> dict[str, Any]:
            nonlocal planned_delay
            rate = float(data["rate"])
            if not (14.0 <= rate <= 14.3):
                raise ValueError(f"unexpected rate for coherence_phi=0.5: {rate}")
            planned_delay = min(
                self.policy.max_delay_seconds,
                max(self.policy.min_delay_seconds, self.policy.delay_scale_seconds / rate),
            )
            return {"planned_delay_seconds": round(planned_delay, 4)}

        clock_res = await self._call_if_granted(
            report,
            session,
            granted,
            "tool_adaptive_clock_rate",
            "adaptive_clock_rate",
            {"coherence_phi": 0.5},
            validator=check_clock,
        )
        if clock_res is not None and self.policy.apply_delay and planned_delay > 0:
            await asyncio.sleep(planned_delay)

        # 3. Separate energy + Sevo gates (Section 5)
        def check_metabolism(data: dict[str, Any]) -> dict[str, Any]:
            joules = float(data["estimated_energy_joules"])
            sevo_defined = bool(data["sevo_defined"])
            sevo = data["sevo"]
            energy_ok = joules <= self.policy.max_estimated_energy_joules
            sevo_ok = sevo_defined and sevo is not None and float(sevo) > self.policy.sevo_threshold
            if not (energy_ok and sevo_ok):
                raise ValueError(f"policy gate failed: energy_ok={energy_ok}, sevo_ok={sevo_ok}")
            return {"energy_ok": energy_ok, "sevo_ok": sevo_ok}

        await self._call_if_granted(
            report,
            session,
            granted,
            "tool_metabolism_cost_eval",
            "metabolism_cost_eval",
            {
                "num_qubits": 0,
                "num_gates": 10,
                "num_spikes": 100,
                "duration_s": 1.0,
                "delta_utility": 2.0,
                "delta_entropy_info": 1.0,
                "sevo_threshold": self.policy.sevo_threshold,
            },
            validator=check_metabolism,
        )

        # 4. Worked Scenario A — KL-barycentre aggregation (Section 6 & 7)
        def check_kl(data: dict[str, Any]) -> dict[str, Any]:
            bary = data.get("barycentre", [])
            if len(bary) != 3 or abs(sum(bary) - 1.0) > 1e-6:
                raise ValueError(f"invalid barycentre distribution: {bary}")
            return {"sum": round(sum(bary), 6)}

        await self._call_if_granted(
            report,
            session,
            granted,
            "scenario_a_kl_barycentre",
            "kl_barycentre_aggregate",
            {
                "distributions": [[0.6, 0.3, 0.1], [0.4, 0.5, 0.1]],
                "weights": [0.5, 0.5],
                "max_iter": 50,
            },
            validator=check_kl,
        )

        # 5. Worked Scenario B — Bounded VTEC allocation (Section 6 & 7)
        def check_vtec(data: dict[str, Any]) -> dict[str, Any]:
            if not data.get("feasible"):
                raise ValueError(f"expected feasible toy VTEC allocation, got {data}")
            return {"allocation_sum": round(sum(data["u"]), 6)}

        await self._call_if_granted(
            report,
            session,
            granted,
            "scenario_b_vtec_allocate",
            "vtec_allocate",
            {
                "objective_kind": "sum",
                "u_max": [1.0, 1.0, 1.0],
                "constraints": {
                    "s_assimilable": 2.0,
                    "e_available": 2.0,
                    "m_available": 2.0,
                    "ecological_threshold": 2.0,
                    "risk_acceptable": 2.0,
                    "human_agency_min": 0.0,
                },
                "horizon": [20, 5],
                "lr": 0.05,
            },
            validator=check_vtec,
        )

        # 6. T234 Singularity Phase-Transition & Genetic-Epigenetic assimilation checks
        def check_manifest(data: dict[str, Any]) -> dict[str, Any]:
            if data.get("framework_id") != "q_speace.singularity.v1" or not data.get(
                "advisory_only"
            ):
                raise ValueError(f"unexpected singularity manifest: {data}")
            return {"framework_id": data["framework_id"]}

        await self._call_if_granted(
            report,
            session,
            granted,
            "tool_singularity_manifest",
            "singularity_framework_manifest",
            {"section": "stages"},
            validator=check_manifest,
        )

        def check_phase_assess(data: dict[str, Any]) -> dict[str, Any]:
            if data.get("stage") != "STAGE_2_BOUNDED_RECURSIVE" or data.get(
                "physical_actuation_permitted"
            ):
                raise ValueError(f"unexpected phase transition assessment: {data}")
            return {"stage": data["stage"], "dominant_bottleneck": data["dominant_bottleneck"]}

        await self._call_if_granted(
            report,
            session,
            granted,
            "tool_phase_transition_assess",
            "phase_transition_assess",
            {
                "timescale_decoupling_ratio": 15.0,
                "autocatalytic_k": 1.4,
                "independent_validation_rate": 0.98,
                "semantic_entropy_drift": 0.02,
                "net_verified_improvement": 0.05,
                "consecutive_verified_cycles": 4,
                "allopoietic_dependence": 0.85,
                "sevo": 2.1,
                "thermal_load_ratio": 0.55,
                "independent_review_passed": True,
            },
            validator=check_phase_assess,
        )

        def check_epigenetic(data: dict[str, Any]) -> dict[str, Any]:
            if not data.get("accepted") or not data.get("genome_write_lock_intact"):
                raise ValueError(f"expected accepted bounded epigenetic step, got {data}")
            return {"generation": data["next_profile"]["generation"]}

        await self._call_if_granted(
            report,
            session,
            granted,
            "tool_epigenetic_step_evaluate",
            "epigenetic_step_evaluate",
            {
                "locus": "verification_depth",
                "delta": 0.05,
                "proposer_id": "mcp-agent-1",
                "reviewer_id": "external-reviewer-1",
                "reviewer_approved": True,
                "semantic_entropy_drift": 0.01,
                "causal_benchmark_delta": 0.03,
                "sevo": 2.0,
                "power_watts": 110.0,
            },
            validator=check_epigenetic,
        )

    async def _check_invalid_arg_recovery(
        self,
        report: AgentReport,
        session: ClientSession,
        granted: set[str],
    ) -> None:
        if "adaptive_clock_rate" not in granted:
            report.steps.append(
                StepRecord(
                    step="invalid_argument_recovery",
                    status="skipped",
                    elapsed_ms=0.0,
                    detail={"reason": "adaptive_clock_rate not granted"},
                )
            )
            return

        async def verify_recovery() -> dict[str, Any]:
            result = await session.call_tool("adaptive_clock_rate", {"coherence_phi": 1.5})
            if not result.isError:
                raise ValueError("expected isError=True for out-of-range coherence_phi=1.5")
            await session.send_ping()
            return {"invalid_call_is_error": True, "subsequent_ping": "ok"}

        await self._record_step(report, "invalid_argument_recovery", verify_recovery())


def _write_evidence(report: AgentReport, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    events_path = report_dir / "events.jsonl"
    summary_path = report_dir / "summary.json"
    with events_path.open("w", encoding="utf-8") as fh:
        for step in report.steps:
            fh.write(json.dumps(asdict(step), sort_keys=True) + "\n")
    summary_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def _run_local_demo(policy: PolicyConfig) -> AgentReport:
    """Run the agent against a temporary loopback T225 HTTP server (no secrets saved)."""
    import jwt
    import uvicorn
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    from q_speace.remote_mcp.config import HTTPConfig
    from q_speace.remote_mcp.server import create_app

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    endpoint = f"http://127.0.0.1:{port}/mcp"
    issuer = f"http://127.0.0.1:{port}/local-demo-issuer/"

    with tempfile.TemporaryDirectory(
        prefix="qspeace-agent-demo-", ignore_cleanup_errors=True
    ) as tmp:
        config = HTTPConfig(
            issuer=issuer,
            resource=endpoint,
            public_keys={"demo-k1": public_pem},
            audit_path=Path(tmp) / "audit.sqlite",
            host="127.0.0.1",
            port=port,
            allowed_hosts=[f"127.0.0.1:{port}"],
            worker_seconds=20.0,
        )
        app = create_app(config)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            meta_url = _metadata_url_for(endpoint)
            for _ in range(60):
                try:
                    if httpx.get(meta_url, timeout=1.0).status_code == 200:
                        break
                except Exception:
                    time.sleep(0.1)

            now = int(time.time())
            token = jwt.encode(
                {
                    "iss": issuer,
                    "aud": endpoint,
                    "sub": "connection-test-agent",
                    "iat": now,
                    "exp": now + 300,
                    "scope": "qspeace:catalog.read qspeace:compute qspeace:simulation.compute",
                },
                private_pem,
                algorithm="RS256",
                headers={"kid": "demo-k1"},
            )
            provider = TokenProvider(endpoint=endpoint, token_url="", access_token=token)
            agent = QSpeaceConnectionAgent(
                endpoint=endpoint, token_provider=provider, policy=policy
            )
            return asyncio.run(asyncio.wait_for(agent.run(), timeout=policy.total_timeout_seconds))
        finally:
            server.should_exit = True
            thread.join(timeout=5.0)
            app.audit.db.close()


def _build_token_provider(args: argparse.Namespace) -> TokenProvider:
    access_token = os.environ.get("QSPEACE_ACCESS_TOKEN")
    client_id = os.environ.get("QSPEACE_CLIENT_ID")
    client_secret = os.environ.get("QSPEACE_CLIENT_SECRET")

    if args.credentials_file is not None:
        raw = json.loads(args.credentials_file.read_text(encoding="utf-8"))
        client_id = raw.get("client_id", client_id)
        client_secret = raw.get("client_secret", client_secret)

    return TokenProvider(
        endpoint=args.endpoint,
        token_url=args.token_url,
        access_token=access_token,
        client_id=client_id,
        client_secret=client_secret,
        timeout_seconds=args.timeout,
    )


def _print_summary(report: AgentReport) -> None:
    verdict = "PASS" if report.passed else "FAIL"
    print(f"=== Q-SPEACE MCP Connection Agent [{verdict}] ===")
    print(f"Endpoint: {report.endpoint}")
    if report.server_name:
        print(f"Server:   {report.server_name} {report.server_version or ''}".strip())
    if report.granted_tools:
        print(f"Tools ({len(report.granted_tools)}): {', '.join(report.granted_tools)}")
    for step in report.steps:
        mark = {"passed": "OK", "skipped": "SKIP", "failed": "FAIL"}[step.status]
        print(f"  [{mark:4s}] {step.step:30s} ({step.elapsed_ms:6.1f} ms)")
    if report.error:
        print(f"Error: {report.error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="MCP Streamable HTTP URL.")
    parser.add_argument("--token-url", default=DEFAULT_TOKEN_URL, help="OAuth token endpoint.")
    parser.add_argument(
        "--credentials-file",
        type=Path,
        default=None,
        help="Optional local JSON file containing client_id and client_secret (never printed).",
    )
    parser.add_argument(
        "--local-demo",
        action="store_true",
        help="Spin up a temporary loopback T225 HTTP server and test against it offline.",
    )
    parser.add_argument(
        "--apply-delay",
        action="store_true",
        help="Actually sleep for the bounded adaptive clock delay during the run.",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request HTTP timeout (s).")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Optional directory where events.jsonl and summary.json will be written.",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON report to stdout.")
    args = parser.parse_args(argv)

    policy = PolicyConfig(apply_delay=args.apply_delay, http_timeout_seconds=args.timeout)
    if args.local_demo:
        report = _run_local_demo(policy)
    else:
        provider = _build_token_provider(args)
        agent = QSpeaceConnectionAgent(
            endpoint=args.endpoint, token_provider=provider, policy=policy
        )
        report = asyncio.run(asyncio.wait_for(agent.run(), timeout=policy.total_timeout_seconds))

    if args.report_dir is not None:
        _write_evidence(report, args.report_dir)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_summary(report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
