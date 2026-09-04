"""TDD Slice 2a: detect_changes gate — HIGH/UNKNOWN → risk:high."""

from unittest.mock import patch

from harness.harness import build_evidence


def test_build_evidence_high_detect_marks_risk_high(monkeypatch) -> None:
    # Mock run_detect_changes to return HIGH
    with patch(
        "harness.harness.run_detect_changes",
        return_value={
            "impacted_nodes": 35,
            "changed_lines": 2,
            "high": True,
            "unknown": False,
            "raw": "HIGH 3 nodos",
        },
    ):
        ev, _ = build_evidence("test-high")
        assert ev.risk == "high"
        assert any("detect_changes" in u for u in ev.uncovered)
        assert ev.impacted_nodes == 35
        assert ev.changed_lines == 2


def test_build_evidence_unknown_detect_marks_risk_high() -> None:
    with patch(
        "harness.harness.run_detect_changes",
        return_value={
            "impacted_nodes": 12,
            "changed_lines": 1,
            "high": False,
            "unknown": True,
            "raw": "UNKNOWN riskNote",
        },
    ):
        ev, _ = build_evidence("test-unknown")
        assert ev.risk == "high"
        assert any("UNKNOWN" in u for u in ev.uncovered)


def test_build_evidence_low_detect_keeps_low() -> None:
    with patch(
        "harness.harness.run_detect_changes",
        return_value={
            "impacted_nodes": 1,
            "changed_lines": 10,
            "high": False,
            "unknown": False,
            "raw": "low",
        },
    ):
        ev, _ = build_evidence("test-low")
        # risk should be low/medium, not high due to detect
        assert ev.risk != "high" or "detect_changes" not in " ".join(ev.uncovered)
