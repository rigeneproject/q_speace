"""Unit tests for TFTPspGeneLibrary and the on-disk catalogue."""

import pytest

from speace_core.dna.tft_gene import TFTPspGeneSet
from speace_core.dna.tftpsp_library import TFTPspGeneLibrary, _default_library


@pytest.fixture(scope="module")
def lib() -> TFTPspGeneLibrary:
    return TFTPspGeneLibrary.from_file()


def test_catalogue_loads_33_genes(lib):
    assert len(lib) == 33
    assert all(g.tft_index == i + 1 for i, g in enumerate(lib.all()))


def test_emergency_gene_is_only_epshcpe(lib):
    emergency = lib.emergency_genes()
    assert len(emergency) == 1
    assert emergency[0].gene_id == "tftpsp_023_epshcpe"
    assert emergency[0].short_label == "EPSHCPE-TFT"
    # It must declare a lock_open rule, otherwise it isn't truly an
    # emergency gene.
    assert any(r.effect == "lock_open" for r in emergency[0].epigenetic_mechanisms)


def test_bcel_resolvable_subset(lib):
    resolvable = lib.bcel_resolvable()
    assert 1 <= len(resolvable) <= 10
    for gene, bcel_name in resolvable:
        assert gene.bcel_equivalent is not None
        assert isinstance(bcel_name, str)
        assert bcel_name  # non-empty


def test_with_and_without_bcel_partition(lib):
    with_bcel = lib.with_bcel()
    without_bcel = lib.without_bcel()
    assert len(with_bcel) + len(without_bcel) == 33
    # TFT-1, TFT-2, TFT-3 are descriptive-only by spec
    assert lib.get("tftpsp_001_tft") in without_bcel
    assert lib.get("tftpsp_002_tsfrutf") in without_bcel


def test_priority_ordering(lib):
    top3 = lib.by_priority(descending=True)[:3]
    assert {g.gene_id for g in top3} == {
        "tftpsp_008_dna_tft",
        "tftpsp_001_tft",
        "tftpsp_006_cfu",
    }


def test_by_tft_index_and_short_label(lib):
    assert lib.by_tft_index(33).gene_id == "tftpsp_033_aiscdsagi"
    assert lib.by_short_label("EPSHCPE-TFT").tft_index == 23


def test_by_domain_tag(lib):
    crisis = lib.by_domain_tag("crisis")
    assert any(g.gene_id == "tftpsp_018_5pc" for g in crisis)
    assert any(g.gene_id == "tftpsp_023_epshcpe" for g in crisis)


def test_filter_criteria(lib):
    # Genes with priority >= 0.7 and a BCEL mapping
    high_priority_bcel = lib.filter(priority_ge=0.7, has_bcel=True)
    for g in high_priority_bcel:
        assert g.priority >= 0.7
        assert g.bcel_equivalent is not None

    # Genes that activate on the 'crisis' tag (either via
    # activation_condition or via epigenetic rule).
    crisis_genes = lib.filter(trigger_tag="crisis")
    assert lib.get("tftpsp_018_5pc") in crisis_genes
    assert lib.get("tftpsp_023_epshcpe") in crisis_genes

    # Genes that have a 'supports' interaction
    supporters = lib.filter(relation="supports")
    assert any(g.gene_id == "tftpsp_008_dna_tft" for g in supporters)


def test_default_library_is_cached():
    a = _default_library()
    b = _default_library()
    assert a is b


def test_load_missing_file_raises(tmp_path):
    from pathlib import Path
    with pytest.raises(FileNotFoundError):
        TFTPspGeneLibrary.from_file(tmp_path / "missing.yaml")


def test_load_invalid_yaml_raises(tmp_path):
    from pathlib import Path
    bad = tmp_path / "bad.yaml"
    bad.write_text("tftpsp:\n  genes:\n    - gene_id: bad\n", encoding="utf-8")
    with pytest.raises(Exception):
        TFTPspGeneLibrary.from_file(bad)


def test_schema_roundtrip(tmp_path):
    """Persist a small valid gene set and reload it."""
    payload = {
        "tftpsp": {
            "enabled": True,
            "genes": [
                {
                    "gene_id": "tftpsp_roundtrip_a",
                    "tft_index": 1,
                    "name": "Roundtrip A",
                    "short_label": "RT-A",
                    "function": "roundtrip test",
                },
                {
                    "gene_id": "tftpsp_roundtrip_b",
                    "tft_index": 2,
                    "name": "Roundtrip B",
                    "short_label": "RT-B",
                    "function": "roundtrip test 2",
                    "priority": 0.42,
                },
            ],
        }
    }
    import yaml as _yaml
    p = tmp_path / "roundtrip.yaml"
    p.write_text(_yaml.safe_dump(payload), encoding="utf-8")
    lib = TFTPspGeneLibrary.from_file(p)
    assert len(lib) == 2
    assert lib.get("tftpsp_roundtrip_b").priority == pytest.approx(0.42)


def test_gene_set_disabled_via_yaml(tmp_path):
    payload = {"tftpsp": {"enabled": False, "genes": []}}
    import yaml as _yaml
    p = tmp_path / "disabled.yaml"
    p.write_text(_yaml.safe_dump(payload), encoding="utf-8")
    lib = TFTPspGeneLibrary.from_file(p)
    assert lib.enabled is False
    assert len(lib) == 0
    assert lib.emergency_genes() == []


def test_validation_rejects_missing_function(tmp_path):
    payload = {
        "tftpsp": {
            "enabled": True,
            "genes": [
                {"gene_id": "tftpsp_x", "tft_index": 1, "name": "x", "short_label": "x"}
                # missing 'function'
            ],
        }
    }
    import yaml as _yaml
    p = tmp_path / "bad2.yaml"
    p.write_text(_yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(Exception):
        TFTPspGeneLibrary.from_file(p)