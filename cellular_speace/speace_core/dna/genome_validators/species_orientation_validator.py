"""Validator for the species_orientation genome block."""
from __future__ import annotations
import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml

_THIS = Path(__file__).resolve()
# Layout: .../speace_core/dna/genome_validators/species_orientation_validator.py
# Target: .../speace_core/dna/genome/core/species_orientation.yaml
_CANON_PATH = _THIS.parent.parent / "genome" / "core" / "species_orientation.yaml"
CANONICAL = yaml.safe_load(_CANON_PATH.read_text(encoding="utf-8"))["species_orientation"]


class SpeciesOrientationViolation(Exception):
    pass


def _check_invariants(prev: List[str], new: List[str]) -> List[str]:
    violations: List[str] = []
    removed = set(prev) - set(new)
    if removed:
        violations.append("removed_invariants=" + ",".join(sorted(removed)))
    return violations


def _check_substrates(prev: List[str], new: List[str]) -> List[str]:
    new_set = set(new)
    allowed = set(CANONICAL["allowed_growth_substrates"])
    unknown = new_set - allowed
    if unknown:
        return ["unknown_substrates=" + ",".join(sorted(unknown))]
    return []


def _check_stages(prev: Dict[str, str], new: Dict[str, str]) -> List[str]:
    if not prev:
        return []
    new_keys = set(new.keys())
    prev_keys = set(prev.keys())
    if not prev_keys.issubset(new_keys):
        return ["removed_stages=" + ",".join(sorted(prev_keys - new_keys))]
    return []


def validate(prev_orientation: Dict[str, Any], new_orientation: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    if not new_orientation:
        violations.append("species_orientation_missing")
        return violations
    if new_orientation.get("name") != prev_orientation.get("name"):
        violations.append("species_orientation_name_changed")
    if new_orientation.get("status") not in ("foundational_guidance", "active"):
        violations.append("species_orientation_status_invalid")
    invariants = new_orientation.get("invariants", []) or []
    prev_invariants = prev_orientation.get("invariants", []) or []
    violations.extend(_check_invariants(prev_invariants, invariants))
    substrates = new_orientation.get("allowed_growth_substrates", []) or []
    prev_substrates = prev_orientation.get("allowed_growth_substrates", []) or []
    violations.extend(_check_substrates(substrates, prev_substrates))
    if set(prev_substrates) - set(substrates):
        violations.append("removed_canonical_substrates=" + ",".join(sorted(set(prev_substrates) - set(substrates))))
    stages = (new_orientation.get("developmental_direction") or {})
    prev_stages = (prev_orientation.get("developmental_direction") or {})
    violations.extend(_check_stages(prev_stages, stages))
    return violations


def validate_genome_file(genome_path: Path) -> Tuple[bool, List[str]]:
    doc = yaml.safe_load(genome_path.read_text(encoding="utf-8")) or {}
    sp = doc.get("species_orientation")
    if not sp:
        return False, ["species_orientation_missing_in_genome"]
    v = validate(CANONICAL, sp)
    return (not v), v


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


if __name__ == "__main__":
    import sys
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"C:\cellular_speace\speace_core\dna\genome\default_genome.yaml"
    )
    ok, violations = validate_genome_file(p)
    print("[{}] {} valid={} violations={}".format(_now(), p, ok, violations))
    sys.exit(0 if ok else 1)
