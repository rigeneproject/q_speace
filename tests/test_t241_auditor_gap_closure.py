"""T241: Tests for Auditor Gap Closure (Model Governance Registry, CRA policy, versioned SBOM, FRIA & QMS templates)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.singularity import (
    CRA_SUPPLY_CHAIN_POLICY,
    DEFAULT_MODEL_GOVERNANCE_REGISTRY,
    MODEL_DEPRECATION_POLICY,
    MODEL_SELECTION_CRITERIA,
    EpigeneticFaultError,
    build_annex_iv_compliance_pack,
    build_runtime_sbom,
    validate_model_governance_selection,
    verify_compliance_pack_integrity,
)


def test_t241_model_governance_registry_and_fail_closed_deprecation() -> None:
    assert len(DEFAULT_MODEL_GOVERNANCE_REGISTRY) >= 4
    assert MODEL_SELECTION_CRITERIA["required_evaluation_protocol"]
    assert MODEL_DEPRECATION_POLICY["fail_closed_on_deprecated_or_prohibited"] is True

    # Approved internal stub & local research model succeed.
    stub = validate_model_governance_selection("qspeace-stub-deterministic")
    assert stub.lifecycle_status == "approved_deterministic_stub"
    qwen = validate_model_governance_selection("Qwen/Qwen2.5-3B-Instruct")
    assert qwen.lifecycle_status == "approved_research_local"

    # External untrusted MCP caller requires explicit opt-in flag.
    with pytest.raises(EpigeneticFaultError, match="allow_external_mcp_caller=True"):
        validate_model_governance_selection("external-mcp-agent-llm")
    ext = validate_model_governance_selection(
        "external-mcp-agent-llm", allow_external_mcp_caller=True
    )
    assert ext.lifecycle_status == "external_mcp_caller_untrusted"

    # Deprecated and unregistered models are blocked fail-closed.
    with pytest.raises(EpigeneticFaultError, match="lifecycle_status='deprecated'"):
        validate_model_governance_selection("legacy-uncalibrated-llm-v0")
    with pytest.raises(EpigeneticFaultError, match="unregistered model"):
        validate_model_governance_selection("unknown-shadow-llm-99b")


def test_t241_versioned_sbom_cra_policy_templates_bcel_and_compliance_pack() -> None:
    # 1. Versioned CycloneDX 1.5 SBOM includes serialNumber, metadata.component, and sbom_sha256.
    sbom = build_runtime_sbom()
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["serialNumber"].startswith("urn:uuid:")
    assert sbom["metadata"]["component"]["name"] == "q-speace"
    assert len(sbom["sbom_sha256"]) == 64

    # 2. CRA policy, SECURITY.md, FRIA & QMS templates exist on disk.
    repo_root = Path(__file__).resolve().parents[1]
    assert (repo_root / CRA_SUPPLY_CHAIN_POLICY["security_policy_path"]).exists()
    assert (repo_root / "docs" / "compliance" / "FRIA_TEMPLATE_EN.md").exists()
    assert (repo_root / "docs" / "compliance" / "QMS_DEPLOYER_CHECKLIST_EN.md").exists()

    # 3. BCEL entries recorded for T241.
    catalog = BCELCatalog()
    assert catalog.is_functional(
        "Model governance registry, CRA security policy, and FRIA/QMS deployer templates (T241)"
    )
    assert (
        catalog.get(
            "Repository-certified organizational QMS or automated FRIA sign-off (T241)"
        ).classification
        == "accidental"
    )

    # 4. Compliance pack embeds all 4 auditor-gap sections and enforces non-self-certification flags.
    pack = build_annex_iv_compliance_pack(node_id="speace-micro-t241", seeds=(11, 23))
    payload = pack.to_dict()
    assert pack.spec == "T240+T241"
    assert pack.qms_externally_certified is False
    assert pack.fria_completed_by_deployer is False
    assert len(pack.model_governance["registry"]) >= 4
    assert pack.cra_supply_chain_policy["coordinated_disclosure_window_days"] == 90
    assert pack.fria_template["template_id"] == "T241-FRIA-v1"
    assert pack.qms_deployer_checklist["template_id"] == "T241-QMS-CHECKLIST-v1"
    assert verify_compliance_pack_integrity(payload) is True
    json.dumps(payload, allow_nan=False)

    # Attempting to forge QMS certification or FRIA completion fails integrity verification.
    forged_qms = dict(payload)
    forged_qms["qms_externally_certified"] = True
    assert verify_compliance_pack_integrity(forged_qms) is False

    forged_fria = dict(payload)
    forged_fria["fria_completed_by_deployer"] = True
    assert verify_compliance_pack_integrity(forged_fria) is False
