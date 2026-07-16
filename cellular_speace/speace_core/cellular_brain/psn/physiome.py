from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from speace_core.cellular_brain.psn.models import (
    SignalOntologyEntry,
    ReceptorProfile,
    TissueMetabolicBudget,
    SynapseKey,
)


class ConstitutionalViolationError(RuntimeError):
    """Raised when a runtime operation violates a constitutional invariant."""


class Physiome:
    """Complete, runtime-accessible description of the organism's physiology.

    Loaded from the Physiological Genome YAML files at startup.
    Immutable for constitutional sections at runtime.
    """

    def __init__(self, genome_dir: str | Path):
        self._genome_dir = Path(genome_dir)
        self._data: Dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        """Load all YAML files from the genome directory."""
        manifest_path = self._genome_dir / "physiological_genome.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Physiological Genome manifest not found: {manifest_path}"
            )

        with open(manifest_path, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)

        pg = manifest.get("physiological_genome", {})
        includes = pg.get("includes", [])

        for inc in includes:
            inc_path = self._genome_dir / inc
            if not inc_path.exists():
                raise FileNotFoundError(
                    f"Genome definition not found: {inc_path} (referenced from manifest)"
                )
            with open(inc_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data is not None:
                self._data.update(data)

        self._loaded = True

    def validate(self) -> List[str]:
        """Cross-validate the loaded Physiome. Returns list of violations."""
        violations = []
        if not self._loaded:
            violations.append("Physiome not loaded")
            return violations

        organs = self._data.get("organs", {})
        systems = self._data.get("systems", {})
        tissues = self._data.get("tissues", {})
        cells = self._data.get("cells", {})
        signals = self._data.get("signals", {})
        molecules_data = self._data.get("molecules", {})

        # Every organ belongs to a valid system
        for oid, odef in organs.items():
            sys_id = odef.get("system")
            if sys_id and sys_id not in systems:
                violations.append(f"Organ '{oid}' references unknown system '{sys_id}'")
            for tid in odef.get("tissues", []):
                if tid not in tissues:
                    violations.append(f"Organ '{oid}' references unknown tissue '{tid}'")

        # Build a set of valid identifiers: molecule names + signal IDs (constitutional + epigenetic)
        valid_identifiers = set(molecules_data.keys())
        valid_identifiers.update(signals.keys())
        valid_identifiers.update(signals.get("epigenetic", {}).keys())
        # Remove the "epigenetic" category key itself (not a signal)
        valid_identifiers.discard("epigenetic")

        # Every tissue references valid cell types and valid identifiers
        for tid, tdef in tissues.items():
            for ct in tdef.get("cell_types", []):
                if ct not in cells:
                    violations.append(f"Tissue '{tid}' references unknown cell type '{ct}'")
            for ident in tdef.get("consumes", []) + tdef.get("produces", []):
                if ident not in valid_identifiers:
                    violations.append(f"Tissue '{tid}' references unknown identifier '{ident}'")

        # Every cell type references valid identifiers
        for cid, cdef in cells.items():
            for ident in cdef.get("consumes", []) + cdef.get("produces", []):
                if ident not in valid_identifiers:
                    violations.append(f"Cell '{cid}' references unknown identifier '{ident}'")

        return violations

    # ── Accessors ───────────────────────────────────────────────

    @property
    def version(self) -> str:
        return self._data.get("physiological_genome_version", "0.0.0")

    @property
    def systems(self) -> Dict[str, Any]:
        return self._data.get("systems", {})

    @property
    def organs(self) -> Dict[str, Any]:
        return self._data.get("organs", {})

    @property
    def tissues_by_id(self) -> Dict[str, Any]:
        return self._data.get("tissues", {})

    @property
    def cells(self) -> Dict[str, Any]:
        return self._data.get("cells", {})

    @property
    def molecules(self) -> Dict[str, Any]:
        return self._data.get("molecules", {})

    @property
    def signals(self) -> Dict[str, Any]:
        return self._data.get("signals", {})

    @property
    def constitutional_signals(self) -> Dict[str, Any]:
        sigs = self.signals
        out = dict(sigs)
        out.pop("epigenetic", None)
        return out

    @property
    def epigenetic_signals(self) -> Dict[str, Any]:
        return self.signals.get("epigenetic", {})

    @property
    def routing(self) -> Dict[str, Any]:
        rd = self._data.get("routing", {})
        if not rd:
            rd = self._data.get("neural_endocrine_routes", {})
        return rd

    @property
    def receptors(self) -> Dict[str, Dict[str, ReceptorProfile]]:
        raw = self._data.get("receptors", {})
        result: Dict[str, Dict[str, ReceptorProfile]] = {}
        for tissue_id, recs in raw.items():
            result[tissue_id] = {}
            for rec_id, rec_data in recs.items():
                result[tissue_id][rec_id] = ReceptorProfile(
                    affinity=rec_data.get("affinity", 0.5),
                    effect=rec_data.get("effect", "modulation"),
                    desensitization_rate=rec_data.get("desensitization_rate", 0.001),
                    metabolic_cost=rec_data.get("metabolic_cost", 0.005),
                )
        return result

    @property
    def metabolic_profiles(self) -> Dict[str, Any]:
        return self._data.get("metabolic_profiles", {})

    @property
    def homeostatic_setpoints(self) -> Dict[str, Any]:
        return self._data.get("homeostatic_setpoints", {})

    @property
    def meta_interoception(self) -> Dict[str, Any]:
        return self._data.get("meta_interoception", {})

    @property
    def predictive_body_model(self) -> Dict[str, Any]:
        return self._data.get("predictive_body_model", {})

    @property
    def psn_config(self) -> Dict[str, Any]:
        return self._data.get("psn", {})

    @property
    def growth_rules(self) -> Dict[str, Any]:
        return self._data.get("growth", {})

    @property
    def policies(self) -> Dict[str, Any]:
        return self._data.get("policies", {})

    @property
    def invariants(self) -> List[str]:
        pg = self._data.get("physiological_genome", {})
        return pg.get("invariants", [])

    def get_ontology_entry(self, signal_id: str) -> Optional[SignalOntologyEntry]:
        """Look up a signal by ID in constitutional or epigenetic signals."""
        constitutional = self.constitutional_signals
        if signal_id in constitutional:
            raw = constitutional[signal_id]
        else:
            epi = self.epigenetic_signals
            if signal_id in epi:
                raw = epi[signal_id]
            else:
                return None

        rng = raw.get("range", [0.0, 1.0])
        return SignalOntologyEntry(
            id=signal_id,
            molecule=raw.get("molecule", []),
            bus=raw.get("bus", "endocrine"),
            type=raw.get("type", "stream"),
            range=rng if isinstance(rng, list) else list(rng),
            unit=raw.get("unit", "fraction"),
            decay=raw.get("decay", 0.95),
            baseline=raw.get("baseline", 0.5),
            polarity=raw.get("polarity", "neutral"),
            vital=raw.get("vital", False),
            event_duration=raw.get("event_duration", 0),
            upper_alarm=raw.get("upper_alarm"),
            lower_alarm=raw.get("lower_alarm"),
            description=raw.get("description", ""),
        )

    def get_molecule(self, molecule_id: str) -> Optional[Dict[str, Any]]:
        return self.molecules.get(molecule_id)

    def get_metabolic_budget(self, tissue_id: str) -> TissueMetabolicBudget:
        profiles = self.metabolic_profiles
        per_tissue = profiles.get("per_tissue", {})
        raw = per_tissue.get(tissue_id, {})
        return TissueMetabolicBudget(
            base_budget=raw.get("base_budget", 0.05),
            low_power_threshold=raw.get("low_power_threshold", 0.7),
            critical_threshold=raw.get("critical_threshold", 0.3),
            publish_cost=raw.get("publish_cost", 0.02),
            sense_cost=raw.get("sense_cost", 0.03),
            subscribe_cost=raw.get("subscribe_cost", 0.01),
        )

    def is_molecule_registered(self, molecule_id: str) -> bool:
        return molecule_id in self.molecules

    def is_signal_registered(self, signal_id: str) -> bool:
        return (
            signal_id in self.constitutional_signals
            or signal_id in self.epigenetic_signals
        )

    def get_setpoint(self, signal_id: str) -> Optional[Dict[str, Any]]:
        return self.homeostatic_setpoints.get(signal_id)
