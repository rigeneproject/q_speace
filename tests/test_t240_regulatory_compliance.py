"""T240: Tests for EU AI Act / NIST / ISO 42001 compliance mapping, Annex IV pack, Art. 73 incident schema & SBOM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.singularity import (
    DEFAULT_RISK_REGISTER,
    EU_AI_ACT_CONTROL_MATRIX,
    build_annex_iv_compliance_pack,
    build_runtime_sbom,
    build_serious_incident_report,
    verify_compliance_pack_integrity,
    verify_incident_record_integrity,
    verify_privacy_by_default_controls,
)


def test_t240_control_matrix_risk_register_privacy_sbom_and_art73_incident() -> None:
    # 1. Control matrix covers Art. 5 through Art. 73 and external legal obligations.
    clauses = " ".join(c.eu_ai_act_clause for c in EU_AI_ACT_CONTROL_MATRIX)
    for expected in (
        "Art. 5",
        "Art. 9",
        "Art. 10",
        "Annex IV",
        "Art. 12",
        "Art. 14",
        "Art. 15",
        "Art. 73",
    ):
        assert expected in clauses
    assert len(DEFAULT_RISK_REGISTER) >= 5

    # 2. Privacy-by-default check passes (hashed prompts + raw-text redaction).
    privacy = verify_privacy_by_default_controls()
    assert privacy["passed"] is True
    assert privacy["request_record_omits_raw_prompt_by_default"] is True
    assert privacy["brain_audit_redacts_raw_text_when_enabled"] is True

    # 3. Runtime SBOM conforms to CycloneDX 1.5 structure and includes numpy/pydantic.
    sbom = build_runtime_sbom()
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["component_count"] > 0
    names = {c["name"].lower() for c in sbom["components"]}
    assert "numpy" in names

    # 4. EU AI Act Art. 73 serious-incident record is tamper-evident & requires human submission.
    rec = build_serious_incident_report(
        incident_id="INC-2026-001",
        node_id="micro-node-eu-01",
        severity="high",
        category="layer0_thermal_interlock",
        summary="Layer-0 thermal e-stop engaged during stress test; rollback succeeded.",
        layer0_interlock_engaged=True,
        rollback_executed=True,
    )
    rec_dict = rec.to_dict()
    assert verify_incident_record_integrity(rec_dict) is True
    assert rec.human_review_required is True
    assert rec.auto_submission_permitted is False

    tampered_rec = dict(rec_dict)
    tampered_rec["severity"] = "low"
    assert verify_incident_record_integrity(tampered_rec) is False

    with pytest.raises(ValueError, match="non-empty"):
        build_serious_incident_report(
            incident_id="",
            node_id="n1",
            severity="low",
            category="c",
            summary="s",
            layer0_interlock_engaged=False,
            rollback_executed=False,
        )


def test_t240_annex_iv_compliance_pack_integrity_bcel_and_cli(tmp_path: Path) -> None:
    # 1. Zero new MCP tools added (T236 baseline preserved).
    assert len(TOOL_REGISTRY) == 14
    assert len(HTTP_TOOL_SCOPES) == 12

    # 2. BCEL entries & English technical guide exist.
    catalog = BCELCatalog()
    assert catalog.is_functional(
        "Regulatory compliance mapping, Annex IV technical pack, and incident reporting schema (T240)"
    )
    assert (
        catalog.get(
            "Automated self-certification or legal CE-marking by software (T240)"
        ).classification
        == "accidental"
    )
    guide = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "T240_REGULATORY_COMPLIANCE_AND_ANNEX_IV_GUIDE_EN.md"
    )
    assert guide.exists()

    # 3. Build Annex IV compliance pack and verify tamper-evident SHA-256 + non-self-certification.
    out_file = tmp_path / "annex_iv_pack.json"
    pack = build_annex_iv_compliance_pack(
        node_id="speace-micro-eu-audit",
        seeds=(11, 23),
        output_path=out_file,
    )
    payload = pack.to_dict()
    assert pack.overall_technical_readiness is True
    assert pack.legal_certification_granted is False
    assert pack.ce_marking_granted is False
    assert pack.self_approval_permitted is False
    assert pack.mcp_actuation_permitted is False
    assert verify_compliance_pack_integrity(payload) is True
    json.dumps(payload, allow_nan=False)

    # Tampering invalidates pack_sha256.
    tampered = dict(payload)
    tampered["legal_certification_granted"] = True
    assert verify_compliance_pack_integrity(tampered) is False

    # 4. CLI round-trip.
    cli_out = tmp_path / "cli_annex_iv.json"
    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            "micro-node",
            "compliance-pack",
            "--node-id",
            "cli-eu-01",
            "--seeds",
            "11,23",
            "--output",
            str(cli_out),
        ],
    )
    assert res.exit_code == 0, res.output
    summary = json.loads(res.output)
    assert summary["overall_technical_readiness"] is True
    assert summary["legal_certification_granted"] is False
    assert summary["ce_marking_granted"] is False
    assert cli_out.exists()
    written = json.loads(cli_out.read_text(encoding="utf-8"))
    assert verify_compliance_pack_integrity(written) is True
