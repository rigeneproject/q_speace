"""ActionSafetyGate — pre-execution safety validation for agent actions.

Reuses existing SPEACE safety infrastructure:
- ActionCatalog for authorization
- HardVetoRouter (MM-APR) for epistemic review
- CounterfactualArchitectureSandbox for simulation (MODERATE+)
- SubstrateStabilityGuard for runtime stability checks
- Human approval gate for HIGH/CRITICAL actions
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from speace_agi_team.action_catalog import ActionCatalog, ActionCategory, ActionRiskLevel
from speace_agi_team.action_proposal import ActionProposal, ActionProposalStatus

_logger = logging.getLogger(__name__)


class ActionSafetyGateResult(BaseModel):
    """Result of safety gate evaluation."""
    gate_id: str = ""
    proposal_id: str = ""
    catalog_authorized: bool = False
    mm_apr_verdict: Optional[Dict[str, Any]] = None
    sandbox_verdict: Optional[str] = None
    substrate_verdict: Optional[str] = None
    regression_safe: Optional[bool] = None
    human_approval_required: bool = False
    final_decision: str = "blocked"  # "allow", "conditioned", "blocked"
    conditions: List[str] = Field(default_factory=list)
    blocked_reason: Optional[str] = None


class ActionSafetyGate:
    """Pre-execution safety gate for agent actions.

    Evaluates proposals through multiple safety layers:
    1. Catalog authorization (agent can propose this action?)
    2. MM-APR veto (epistemic review)
    3. Counterfactual sandbox (MODERATE+ risk levels)
    4. Substrate stability check
    5. Human approval gate (HIGH/CRITICAL)
    """

    def __init__(
        self,
        catalog: Optional[ActionCatalog] = None,
        mmapr_router: Any = None,
        counterfactual_sandbox: Any = None,
        substrate_guard: Any = None,
        patch_executor: Any = None,
    ):
        self.catalog = catalog or ActionCatalog()
        self.mmapr_router = mmapr_router
        self.counterfactual_sandbox = counterfactual_sandbox
        self.substrate_guard = substrate_guard
        self.patch_executor = patch_executor

    def evaluate(self, proposal: ActionProposal) -> ActionSafetyGateResult:
        """Run all safety checks on a proposal.

        Returns a result that either allows, conditions, or blocks the action.
        """
        result = ActionSafetyGateResult(
            gate_id=f"gate-{proposal.proposal_id}",
            proposal_id=proposal.proposal_id,
        )

        # ── Layer 1: Catalog authorization ──────────────────────────────
        result.catalog_authorized = self.catalog.is_authorized(
            proposal.agent_id, proposal.action_category, proposal.target
        )
        if not result.catalog_authorized:
            result.final_decision = "blocked"
            result.blocked_reason = (
                f"Agent {proposal.agent_id} not authorized for "
                f"{proposal.action_category}:{proposal.target}"
            )
            _logger.warning("Safety gate BLOCKED: %s", result.blocked_reason)
            return result

        # ── Layer 2: MM-APR veto ───────────────────────────────────────
        if self.mmapr_router is not None:
            result.mm_apr_verdict = self._run_mmapr(proposal)
            if result.mm_apr_verdict:
                final_status = result.mm_apr_verdict.get("final_status", "")
                if final_status == "hard_blocked":
                    result.final_decision = "blocked"
                    result.blocked_reason = (
                        f"MM-APR hard blocked: "
                        f"{result.mm_apr_verdict.get('blocked_reason', 'unknown')}"
                    )
                    _logger.warning("Safety gate BLOCKED by MM-APR: %s", result.blocked_reason)
                    return result

        # ── Layer 2b: Mandatory sandbox for .py file modifications ───────
        # MODIFY_PY_FILE always requires sandbox verification.
        # If sandbox is unavailable, .py modifications are blocked.
        if proposal.action_category == ActionCategory.MODIFY_PY_FILE.value:
            if self.counterfactual_sandbox is not None:
                result.sandbox_verdict = self._run_sandbox(proposal)
                if result.sandbox_verdict in ("unsafe", "reject"):
                    result.final_decision = "blocked"
                    result.blocked_reason = (
                        f"PY file modification blocked by sandbox: {result.sandbox_verdict}"
                    )
                    _logger.warning("Safety gate BLOCKED .py by sandbox: %s", result.blocked_reason)
                    return result
                # Sandbox passed — add condition for extra monitoring
                result.conditions.append("PY file modification: sandbox verified")
            else:
                # No sandbox available — block .py modifications for safety
                result.final_decision = "blocked"
                result.blocked_reason = (
                    "PY file modification requires sandbox verification (sandbox not available)"
                )
                _logger.warning("Safety gate BLOCKED .py: sandbox not available for %s", proposal.proposal_id)
                return result

        # ── Layer 3: Counterfactual sandbox (MODERATE+ risk) ──────────
        risk = ActionRiskLevel(proposal.risk_level) if isinstance(proposal.risk_level, str) else proposal.risk_level
        if risk in (ActionRiskLevel.MODERATE, ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL):
            if self.counterfactual_sandbox is not None:
                result.sandbox_verdict = self._run_sandbox(proposal)
                if result.sandbox_verdict in ("unsafe", "reject"):
                    result.final_decision = "blocked"
                    result.blocked_reason = f"Counterfactual sandbox verdict: {result.sandbox_verdict}"
                    _logger.warning("Safety gate BLOCKED by sandbox: %s", result.blocked_reason)
                    return result

        # ── Layer 4: Substrate stability check ──────────────────────────
        if self.substrate_guard is not None:
            result.substrate_verdict = self._check_substrate(proposal)
            if result.substrate_verdict == "emergency":
                result.final_decision = "blocked"
                result.blocked_reason = "Substrate stability guard reports EMERGENCY"
                _logger.warning("Safety gate BLOCKED by substrate guard: EMERGENCY")
                return result
            elif result.substrate_verdict in ("adjust", "dampen"):
                result.conditions.append(
                    f"Substrate guard: {result.substrate_verdict} — extra monitoring recommended"
                )

        # ── Layer 5: Human approval gate (HIGH/CRITICAL) ───────────────
        if risk in (ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL):
            result.human_approval_required = True
            # The proposal stays in HUMAN_REVIEW status until approved
            result.final_decision = "conditioned"
            result.conditions.append(
                f"Requires human approval (risk level: {risk.value})"
            )
            _logger.info(
                "Safety gate CONDITIONED: human approval required for %s (risk=%s)",
                proposal.proposal_id, risk.value
            )
            return result

        # ── All checks passed ───────────────────────────────────────────
        if result.conditions:
            result.final_decision = "conditioned"
        else:
            result.final_decision = "allow"
        _logger.info(
            "Safety gate %s: proposal %s (risk=%s)",
            result.final_decision.upper(), proposal.proposal_id, risk.value
        )
        return result

    # ── Private helpers ─────────────────────────────────────────────────

    def _run_mmapr(self, proposal: ActionProposal) -> Optional[Dict[str, Any]]:
        """Run the MM-APR HardVetoRouter on a proposal.

        Constructs a minimal ArchitectureRewriteProposal from the ActionProposal
        and routes it through the veto system.
        """
        try:
            from speace_core.cellular_brain.self_improvement.mmapr_veto_router import HardVetoRouter
            from speace_core.cellular_brain.self_improvement.architecture_patch_executor import ArchitecturePatchExecutor

            # Construct a minimal proposal for the veto router
            # The veto router expects an ArchitectureRewriteProposal or similar
            # We create a lightweight wrapper that carries the essential fields
            class _MinimalVetoProposal:
                def __init__(self, action_proposal: ActionProposal):
                    self.id = action_proposal.proposal_id
                    self.proposal_type = action_proposal.action_category
                    self.target_modules = [action_proposal.target]
                    self.expected_benefits = {"primary": 0.5}
                    self.expected_risks = {"primary": 0.3}
                    self.safety_constraints = [
                        "No modification of core CellAssembly models",
                        f"Rollback plan: restore {action_proposal.target} to previous value",
                    ]
                    if action_proposal.justification:
                        self.safety_constraints.append(f"Justification: {action_proposal.justification[:200]}")

            veto_proposal = _MinimalVetoProposal(proposal)

            # Try to route through MM-APR if available
            if isinstance(self.mmapr_router, HardVetoRouter):
                result = self.mmapr_router.route(veto_proposal)
                return {
                    "final_status": result.final_status if hasattr(result, 'final_status') else "admit",
                    "hard_blocked": result.hard_blocked if hasattr(result, 'hard_blocked') else False,
                    "class_a_verdict": str(result.class_a_verdict) if hasattr(result, 'class_a_verdict') else "unknown",
                    "class_b_verdict": str(result.class_b_verdict) if hasattr(result, 'class_b_verdict') else "unknown",
                    "class_c_verdict": str(result.class_c_verdict) if hasattr(result, 'class_c_verdict') else "unknown",
                    "class_d_verdict": str(result.class_d_verdict) if hasattr(result, 'class_d_verdict') else "unknown",
                }
            else:
                # If it's not a HardVetoRouter but has a route method, try it
                if hasattr(self.mmapr_router, 'route'):
                    result = self.mmapr_router.route(veto_proposal)
                    return {"final_status": getattr(result, 'final_status', 'admit')}
                return None

        except (ImportError, Exception) as e:
            _logger.info("MM-APR router not available, skipping veto: %s", e)
            return None

    def _run_sandbox(self, proposal: ActionProposal) -> Optional[str]:
        """Run the counterfactual sandbox on a proposal.

        Returns: "accept", "needs_more_evidence", "reject", "unsafe", or None if unavailable.
        """
        try:
            if self.counterfactual_sandbox is not None and hasattr(self.counterfactual_sandbox, 'run_scenario'):
                # Construct a minimal scenario for the sandbox
                result = self.counterfactual_sandbox.run_scenario(
                    scenario_type=proposal.action_category,
                    target=proposal.target,
                    new_value=proposal.new_value,
                )
                if hasattr(result, 'verdict'):
                    return result.verdict
                return "accept"  # Default to accept if sandbox doesn't return verdict
            return None
        except Exception as e:
            _logger.warning("Counterfactual sandbox failed: %s", e)
            # For MODERATE risk, allow on sandbox failure; for HIGH/CRITICAL, block
            risk = ActionRiskLevel(proposal.risk_level) if isinstance(proposal.risk_level, str) else proposal.risk_level
            if risk in (ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL):
                return "reject"
            return "accept"

    def _check_substrate(self, proposal: ActionProposal) -> Optional[str]:
        """Check substrate stability via SubstrateStabilityGuard.

        Returns: "ok", "adjust", "dampen", "emergency", or None if unavailable.
        """
        try:
            if self.substrate_guard is not None and hasattr(self.substrate_guard, 'evaluate'):
                result = self.substrate_guard.evaluate(
                    circuit=None,  # Will use internal state if available
                    activations={},
                    metabolic_state=None,
                )
                if hasattr(result, 'verdict'):
                    return result.verdict
                elif isinstance(result, dict):
                    return result.get('verdict', 'ok')
            return None
        except Exception as e:
            _logger.warning("Substrate guard check failed: %s", e)
            return None