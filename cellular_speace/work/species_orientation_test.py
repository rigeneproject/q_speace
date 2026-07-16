"""Verifica completa del validator e dell'integrazione species_orientation."""
import json
from pathlib import Path
import yaml

REPORT_DIR = Path(r"C:\cellular_speace\reports\actions\04_species_orientation")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
results = {"tests": {}}

def add(name, ok, detail):
    results["tests"][name] = {"ok": bool(ok), "detail": str(detail)}
    print("[{}] {}: {}".format("OK" if ok else "FAIL", name, detail))

# 1) YAML esiste ed è valido
sp_path = Path(r"C:\cellular_speace\speace_core\dna\genome\core\species_orientation.yaml")
default_path = Path(r"C:\cellular_speace\speace_core\dna\genome\default_genome.yaml")
sp = yaml.safe_load(sp_path.read_text(encoding="utf-8"))
add("species_orientation_yaml_loads", isinstance(sp.get("species_orientation"), dict),
    "keys={}".format(list(sp["species_orientation"].keys())))

# 2) Default genome referenzia species_orientation
default_doc = yaml.safe_load(default_path.read_text(encoding="utf-8"))
add("default_genome_references_orientation", isinstance(default_doc.get("species_orientation"), dict),
    "present_in_default={}".format(isinstance(default_doc.get("species_orientation"), dict)))

# 3) Validator module
from speace_core.dna.genome_validators import (
    CANONICAL, validate, validate_genome_file, SpeciesOrientationViolation,
)
add("validator_module_imports", True, "CANONICAL_name={}".format(CANONICAL["name"]))

# 4) Default genome validates against canonical
ok, violations = validate_genome_file(default_path)
add("default_genome_validates", ok, "violations={}".format(violations))

# 5) Negative cases
bad = {
    "name": "NotSPEACE",  # would be rejected
    "status": "active",
    "invariants": [],
    "allowed_growth_substrates": ["unknown_substrate"],
    "developmental_direction": {"stage_0": "x"},  # missing other stages
}
v = validate(CANONICAL, bad)
add("bad_orientation_rejected", len(v) > 0, "violations={}".format(v))

# 6) Adding a canonical substrate + extra invariant is allowed
extra_ok = {
    "name": CANONICAL["name"],
    "status": "foundational_guidance",
    "invariants": CANONICAL["invariants"] + ["Custom invariant accepted."],
    "allowed_growth_substrates": CANONICAL["allowed_growth_substrates"] + ["domestic_pc_nodes"],
    "developmental_direction": dict(CANONICAL["developmental_direction"]),
}
v = validate(CANONICAL, extra_ok)
add("extra_invariant_substrate_accepted", len(v) == 0, "violations={}".format(v))

results["summary"] = {
    "total": len(results["tests"]),
    "passed": sum(1 for v in results["tests"].values() if v["ok"]),
    "failed": sum(1 for v in results["tests"].values() if not v["ok"]),
}
(REPORT_DIR / "species_orientation_validation.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nSummary: {}".format(results["summary"]))
