"""TDD Slice 1: EvidenceBundle impact_ratio schema — seam harness/harness.py."""

from harness.harness import EvidenceBundle


def test_evidence_bundle_has_impact_ratio_fields() -> None:
    ev = EvidenceBundle()
    # Prefactor: new fields must exist with defaults
    assert hasattr(ev, "impact_ratio")
    assert hasattr(ev, "impacted_nodes")
    assert hasattr(ev, "changed_lines")
    assert ev.impact_ratio is None
    assert ev.impacted_nodes == 0
    assert ev.changed_lines == 0
    # setting works
    ev.impact_ratio = 17.5
    ev.impacted_nodes = 35
    ev.changed_lines = 2
    assert ev.impact_ratio == 17.5


def test_evidence_bundle_impact_ratio_serializes_in_trajectory() -> None:
    ev = EvidenceBundle(impact_ratio=2.5, impacted_nodes=5, changed_lines=2)
    # asdict must include new fields for trajectory.jsonl
    from dataclasses import asdict

    d = asdict(ev)
    assert "impact_ratio" in d
    assert d["impact_ratio"] == 2.5
    assert d["impacted_nodes"] == 5
    assert d["changed_lines"] == 2
