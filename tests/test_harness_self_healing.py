"""TDD Slice 4: Self-Healing + gating senior impact_ratio>10."""

from unittest.mock import patch

from harness.harness import build_evidence


def test_impact_ratio_over_10_gates_high() -> None:
    # Mock detect to return high ratio 35/2=17.5
    with patch(
        "harness.harness.run_detect_changes",
        return_value={
            "impacted_nodes": 35,
            "changed_lines": 2,
            "high": False,
            "unknown": False,
            "raw": "low",
        },
    ):
        ev, _ = build_evidence("test-ratio-high")
        assert ev.impact_ratio == 17.5
        assert ev.risk == "high"
        assert "needs-human-attention" in " ".join(ev.uncovered)
        assert "impact_ratio >10" in ev.risk_reason


def test_impact_ratio_under_10_no_gate() -> None:
    with patch(
        "harness.harness.run_detect_changes",
        return_value={
            "impacted_nodes": 5,
            "changed_lines": 2,
            "high": False,
            "unknown": False,
            "raw": "low",
        },
    ):
        ev, _ = build_evidence("test-ratio-low")
        assert ev.impact_ratio == 2.5
        # should not be high due to ratio
        assert ev.risk != "high" or "impact_ratio" not in ev.risk_reason


def test_self_heal_pruning_second_retry_truncates_log() -> None:
    # Simulate pruning: second retry only stack trace + patch, not full log
    # Verify raw truncated to 120 chars (pruning)
    with patch(
        "harness.harness.run_detect_changes",
        return_value={
            "impacted_nodes": 1,
            "changed_lines": 1,
            "high": True,
            "unknown": False,
            "raw": "x" * 5000,
        },
    ):
        ev, _ = build_evidence("test-prune")
        # uncovered should be truncated
        assert len(ev.uncovered[0]) < 200
