# Connecting an agentic AI client to Q-SPEACE MCP

Date: 2026-11-22. Profile: experimental T225 HTTP adapter + T234 v1.1 Singularity phase-transition & genetic-epigenetic reference tools.


## Provisioned experimental service (updated 2026-11-22)

- Verified live using official MCP SDK 1.30.0 against `https://q-speace-mcp.onrender.com/mcp`:
  initialize, initialized notification, ping, discovery of **11 advisory tools**,
  BCEL/clock/metabolism/KL/VTEC calls, all 3 T234 v1.1 Singularity tools (including
  adversarial DNA write-lock, Track-A smuggling, hallucination-drift, complexity-Sevo,
  and protective thermal-throttling probes), and invalid-argument recovery.
- MCP endpoint: `https://q-speace-mcp.onrender.com/mcp`.
- OAuth issuer: `https://dev-imfska6viiq1ehqw.us.auth0.com/`.
- API audience: `https://q-speace-mcp.onrender.com/mcp`.
- Token endpoint: `https://dev-imfska6viiq1ehqw.us.auth0.com/oauth/token`.
- Client: **Q-SPEACE Experimental Agent**, machine-to-machine, explicitly
  granted the three documented scopes; access-token lifetime **900 seconds**.
- Deployment: Render Free, Frankfurt, one process, automatic deployments off.
  Source branch: `main` (verified runtime built from `6ef2e9a3`).
- Deployed worker wall-time limit: **20 seconds**, one concurrent worker. The
  five-second default timed out on the Free CPU; timed-out processes are killed.
- Server hardening included in this build (T231 / Milestone 8): automatic
  expired-session pruning prior to the per-principal session cap, and strict
  RFC 8259 rejection of `NaN`/`Infinity` JSON constants at parse time.

The existing client's credentials are stored only on the operator's computer in
`.qspeace-dev/auth0-agent-client.json`, excluded from Git and restricted with a
Windows ACL. Each external agent should receive its own Auth0 application and
minimum scope grant. Do not distribute this operator client secret to strangers
or place it in a browser, repository, prompt, or MCP server configuration.

For an authorized local smoke test, run this from the repository root after
installing the optional HTTP dependencies. It obtains a fresh access token and
passes it to the official SDK client without printing or saving the token:

```python
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

credentials = json.loads(
    Path(".qspeace-dev/auth0-agent-client.json").read_text(encoding="utf-8")
)
response = httpx.post(
    "https://dev-imfska6viiq1ehqw.us.auth0.com/oauth/token",
    json={
        "grant_type": "client_credentials",
        "client_id": credentials["client_id"],
        "client_secret": credentials["client_secret"],
        "audience": "https://q-speace-mcp.onrender.com/mcp",
    },
    timeout=30,
)
response.raise_for_status()
environment = os.environ.copy()
environment["QSPEACE_ACCESS_TOKEN"] = response.json()["access_token"]
subprocess.run(
    [sys.executable, "-m", "examples.mcp_http_client",
     "--url", "https://q-speace-mcp.onrender.com/mcp"],
    env=environment,
    check=True,
)
```

An unattended adapter should cache its token until shortly before expiry, then
request a new one; avoid requesting a token for every tool call. Respect Auth0
machine-token quotas and Render cold starts. Provision clients through Auth0's
administrative controls; no dynamic client registration or interactive PKCE
client has been configured by this deployment.

## 1. Deployment status and boundaries

The repository contains a tested Streamable HTTP resource-server prototype.
The dated deployment section records the provisioned experimental service.
Replace `YOUR-SERVICE` and `YOUR-TENANT` only after the corresponding resources
exist. A local fixture token is not evidence of a working OAuth login service.

The two MCP services have different responsibilities:

- GitHub MCP reads the online repository. It does not run Q-SPEACE computations.
- Q-SPEACE MCP runs the **eleven** numeric/advisory tools below (8 core T225 tools + 3 T234 v1.1 Singularity phase-transition & genetic-epigenetic tools). It does not grant
  permission to change infrastructure, repository files, budgets or policies.

| Tools | Required scope |
| --- | --- |
| `bcel_lookup`, `singularity_framework_manifest` | `qspeace:catalog.read` |
| `compute_jc`, `cme_evaluate`, `adaptive_clock_rate`, `metabolism_cost_eval`, `elasticity_test`, `phase_transition_assess` | `qspeace:compute` |
| `kl_barycentre_aggregate`, `vtec_allocate`, `epigenetic_step_evaluate` | `qspeace:simulation.compute` |

`dat_mint`, `dat_spend`, Bridge activation, rollback and validator promotion are
not available over HTTP. Unknown or unauthorized tool calls are refused even
when a client skips discovery and calls them directly.

## 2. Install and verify locally

Use Python 3.12 or later from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[http,dev]"
.\.venv\Scripts\python.exe -m pytest -k "t218 or t225" -v --no-cov
```

Create loopback-only test credentials:

```powershell
.\.venv\Scripts\python.exe examples/mcp_http_dev_setup.py
.\.venv\Scripts\python.exe -m q_speace.remote_mcp.server --config .qspeace-dev/config.json
```

In another terminal:

```powershell
$env:QSPEACE_ACCESS_TOKEN = Get-Content -Raw .qspeace-dev/access-token.txt
.\.venv\Scripts\python.exe examples/mcp_http_client.py --url http://127.0.0.1:8765/mcp
Remove-Item Env:QSPEACE_ACCESS_TOKEN
```

The token lasts one hour; no private signing key is saved. The test issuer has
no login/discovery service. Never upload this fixture directory or use it as
public OAuth configuration. The generator refuses an existing directory rather
than overwriting credentials; choose a fresh `--directory` when necessary.

On Linux/macOS use your virtual environment's `python` executable. The same
Python scripts apply; use your shell's environment-variable syntax and avoid
putting literal tokens into shell history.

## 3. Hosting choice

Google Sites and GitHub Pages can publish the project page and these
instructions, but cannot run this ASGI backend.

Render Free is a possible demonstration host. Its free web services sleep
after 15 minutes without traffic and their local files are ephemeral. Waking
may take about a minute. Sessions, in-memory quotas and the SQLite audit file
are lost after restart/sleep: this profile is not durable accounting and does
not meet the full production-promotion requirements of T225.

Hugging Face currently documents that creating new Docker/Gradio compute Spaces
requires a paid plan, even though CPU Basic has no hourly hardware charge.
Do not interpret "CPU Basic FREE" as a guarantee of free Docker Space creation.
Cloud Run offers usage allowances, not an unconditional zero-cost deployment.

Dockerfile: `deploy/mcp/Dockerfile`. Render Blueprint template:
`deploy/mcp/render.yaml`. Both use one application process; use one worker on a
small free instance. Horizontal scaling requires shared session/quote storage
and is outside the tested prototype.

## 4. Provision the authorization service

The application is an **OAuth resource server**, not an authorization server.
Use an existing trusted issuer or create an Auth0 tenant using its current free
plan if it meets your requirements. Account creation, terms, account recovery
and MFA belong to the account owner. Review current plan limits, especially
machine-to-machine token quotas; do not enable paid add-ons implicitly.

For an Auth0-compatible setup:

1. Record the exact issuer, for example `https://YOUR-TENANT.eu.auth0.com/`.
   Preserve the trailing slash when it is part of the token's `iss` claim.
2. Once the actual public service URL is assigned, register an API whose
   identifier/audience matches `https://YOUR-SERVICE.onrender.com/mcp`.
3. Select RS256 signing and define the three scopes in section 1.
4. Register each client explicitly. For a human-operated agent, use the
   provider's supported authorization-code/PKCE setup and exact callback URLs.
   For a trusted unattended agent, authorize a machine client for only the
   required API permissions. Do not assume dynamic client registration exists.
5. Obtain access tokens for this API, not ID tokens or GitHub/Hugging Face tokens.
6. Configure short lifetimes, revocation procedures and a key-rotation runbook.

The server requires `iss`, `aud`, `sub`, `iat`, `exp`, an RSA signature from a
pinned `kid`, and a space-separated `scope` string for the requested tools.
The issuer must control subject assignment and scope grants. A caller cannot
grant itself permissions by changing JSON tool arguments.

Fetch public verification keys and build the deployment configuration:

```powershell
python -m examples.mcp_http_config_from_jwks `
  --issuer https://YOUR-TENANT.eu.auth0.com/ `
  --resource https://YOUR-SERVICE.onrender.com/mcp `
  --output .qspeace-dev/render-public-config.json
```

This helper uses the Auth0-style `/.well-known/jwks.json` endpoint. It downloads
only public RSA keys; it does not create an API or client, fetch tokens, or prove
that your OAuth registration works. Other providers require their own verified
discovery integration. The prototype does not refresh JWKS automatically: add
the issuer's new pinned keys through a reviewed configuration update before
rotation, and remove retired keys according to the operator's policy.

## 5. Deploy to Render

Before deploying, commit and publish the reviewed implementation to a branch
that Render can clone. Do not point Render at an old branch lacking the adapter.
Preserve unrelated local changes and exclude `.qspeace-dev/` and credentials.

Create a Web Service with these settings:

| Setting | Value |
| --- | --- |
| Source | `https://github.com/rigeneproject/q_speace.git`, reviewed branch |
| Runtime | Docker |
| Dockerfile | `deploy/mcp/Dockerfile` |
| Build context | Repository root |
| Plan | Free, explicitly selected |
| Automatic deploy | Off until verification is complete |
| Health check | `/` |
| Application processes | One |
| Region | Explicitly chosen by the operator; no coupled resource assumed |

Record the actual assigned URL. A new service may fail closed until the issuer
and resource configuration is supplied; do not describe that as a working MCP
deployment. Complete the API audience registration using the actual URL.

Set `QSPEACE_HTTP_CONFIG_JSON` to the generated public-config JSON in Render's
environment settings. It contains issuer/resource URLs and **public** keys, not
private signing keys or client secrets. Do not paste credentials into chat.
The container reads Render's `PORT` and requires `host=0.0.0.0` with HTTPS
issuer/resource URLs. The generated small-instance profile permits one compute
worker. Adjust limits only through a reviewed operator configuration.

The root health response proves the process is running, not OAuth or tool
correctness. Verify deployment reaches `live`, inspect sanitized logs and run
the authenticated smoke test before publishing a connection URL.

## 6. Verify the actual online endpoint

Check the protected-resource metadata:

```text
GET https://YOUR-SERVICE.onrender.com/.well-known/oauth-protected-resource/mcp
```

It must advertise the expected resource and authorization server. Check:

- Unauthenticated MCP calls return 401 with the appropriate challenge.
- A token for another audience/issuer or an expired token is refused.
- A catalog-only token sees only `bcel_lookup` and `singularity_framework_manifest` and cannot call compute tools.
- A different principal cannot use a session identifier issued to another one.
- A valid token completes initialize, initialized notification, ping, discovery
  and a successful numeric tool call using the official SDK.
- Invalid arguments produce `isError=true` without making subsequent valid
  requests unusable. Transport authentication failures are HTTP errors instead.
- The HTTP catalog has **eleven** tools; no Bridge activation or DAT mutation tools.

Acquire the correct OAuth token through your client's/provider's supported
flow, load it into `QSPEACE_ACCESS_TOKEN` without printing it, then run:

```powershell
python examples/mcp_http_client.py --url https://YOUR-SERVICE.onrender.com/mcp
```

Or run the full 14-step connection verification agent (exercises OAuth, discovery,
core tools, all 3 T234 Singularity tools, and invalid-argument recovery):

```powershell
python -m examples.mcp_connection_agent --local-demo --apply-delay
```

The same bearer-token SDK path is tested over real local HTTP. A real Auth0
login and public-host test still require actual tenant/service configuration.

## 7. Configure a coding-agent MCP client

For Codex, a bearer-token configuration can be added without writing the token
into the repository:

```text
codex mcp add q-speace-online --url https://YOUR-SERVICE.onrender.com/mcp --bearer-token-env-var QSPEACE_ACCESS_TOKEN
```

Ensure the client process can read that environment variable; setting it in a
different terminal does not update an already-running desktop application.
Native OAuth login depends on the client's registration capabilities and the
issuer's configuration. If DCR is unavailable, register the client through a
supported path; do not assume `mcp login` will complete automatically.

Other clients should use Streamable HTTP, the actual `/mcp` URL and their
supported OAuth or secret-backed Authorization-header configuration. Their
configuration file formats are client-specific, not part of MCP itself.

## 8. English task examples and payloads

### Read a BCEL equivalence

Prompt: "Look up Homeostasis in Q-SPEACE. Explain the retained mathematical
rule and its limitations. Do not treat the lookup as approval to act."

```json
{"concept":"Homeostasis"}
```

### Calculate a scheduling proxy

Prompt: "Evaluate adaptive_clock_rate for coherence_phi=0.5. Report the rate.
Propose a client-side delay capped at 100 ms while preserving an independent
iteration limit. Do not claim this measures semantic truth or consciousness."

```json
{"coherence_phi":0.5}
```

### Estimate a hypothetical modeled cost

Prompt: "Evaluate this synthetic operation. Label watts and joules as estimates,
report Sevo separately, and do not translate the result into real LLM billing."

```json
{"num_qubits":0,"num_gates":1,"duration_s":0.01,"delta_utility":2,"delta_entropy_info":1}
```

### Propose an allocation without executing it

Prompt: "Use vtec_allocate with the centered toy objective and the declared
constraints. Return the proposal, feasibility and assumptions. Do not apply it
to a device, production budget or external system."

```json
{
  "objective_kind":"centered",
  "u_max":[1,1,1],
  "horizon":[50,50],
  "constraints":{
    "s_assimilable":1,"e_available":10,"m_available":5,
    "ecological_threshold":0.8,"risk_acceptable":0.7,"human_agency_min":0
  }
}
```

### Assimilate the T234 Singularity phase-transition & epigenetic framework

Prompt: "Fetch the T234 singularity framework manifest (`section='stages'`), assess
our measured telemetry with `phase_transition_assess` (checking both `semantic_entropy_drift`
and `causal_grounding_error`), and test one bounded Track-B `epigenetic_step_evaluate`
proposal with an independent reviewer. Treat returned `runtime_controls` as advisory
recommendations only; never self-approve or actuate hardware."

```json
{
  "locus": "verification_depth",
  "delta": 0.10,
  "proposer_id": "external-agent-1",
  "reviewer_id": "independent-reviewer-1",
  "reviewer_approved": true,
  "semantic_entropy_drift": 0.01,
  "causal_grounding_error": 0.005,
  "causal_benchmark_delta": 0.03,
  "sevo": 2.4,
  "sevo_window_mean": 2.2,
  "power_watts": 115.0,
  "thermal_load_ratio": 0.52,
  "validation_seed_epoch": 1,
  "track": "B_sandbox"
}
```

Generated text and tool results remain untrusted inputs to a separately
authorized orchestrator. The HTTP service cannot prevent spending or actions
that an unconstrained agent performs outside it.

## 9. Troubleshooting and operational limits

| Observation | Check |
| --- | --- |
| 401 | Expiry, exact issuer/audience, signing kid/public key, token type |
| 403 | Scope grant, requested tool, exact Host/Origin allowlists |
| 404 session error | Principal mismatch, expired session or service restart; initialize again |
| 413 | Request exceeds 64 KiB |
| 429 | Rate/session/worker admission; respect Retry-After, avoid immediate retry loops |
| 503 | Audit or mandatory dependency unavailable; fail closed |
| `isError=true` | Invalid/domain input, failed computation or bounded worker timeout; inspect the reason code |
| Render cold start | Wait for wake-up, then initialize a fresh session; do not replay uncertain stateful operations |

GET `/mcp` returns 405 by design: this profile does not offer server-initiated
SSE. This does not prevent normal Streamable HTTP POST request/response calls.

This is a single-process research profile. Its session/quote storage is in
memory; local audit stores hashes and cannot by itself replay full inputs or
prove immutability. Linux workers receive CPU/address-space limits; Windows
does not provide those resource limits here. Disposable processes are not a
security sandbox, and this project has not demonstrated full worker filesystem
or egress isolation. Do not promote the profile to production solely because
tests or a demonstration deployment pass. T208/T217 and the remaining T225
acceptance criteria still apply.

## References

- [T225 specification and T218 reuse matrix](T225_REMOTE_MCP_SERVICE_SPEC.md).
- [T231 vertical-slice contracts and MCP hardening](T231_VERTICAL_SLICE_AND_MCP_HARDENING_SPEC.md).
- [T234 Singularity phase-transition & genetic-epigenetic framework](T234_SINGULARITY_PHASE_TRANSITION_AND_EPIGENETIC_FRAMEWORK_SPEC.md).
- [T218 Bridge contract](T218_QSPEACE_V0_BRIDGE_SPEC.md).
- [T223 local stdio adapter](T223_MCP_PRIMITIVE_ADAPTER_SPEC.md).
- [Render Free limitations](https://render.com/docs/free).
- [Render Docker services](https://render.com/docs/docker).
- [Hugging Face current Spaces requirements](https://huggingface.co/docs/hub/spaces-overview).
- [Auth0 plans](https://auth0.com/pricing).
- [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).
