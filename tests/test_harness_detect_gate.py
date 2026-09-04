"""TDD Slice 2a: detect_changes gate — HIGH/UNKNOWN → risk:high."""

from unittest.mock import MagicMock, patch

from harness.harness import build_evidence, run_detect_changes


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


def test_run_detect_changes_unknown_option_no_falso_high() -> None:
    """Regresión run 0a7b6a8f: 'unknown option --json' no es risk UNKNOWN."""
    fake = MagicMock()
    fake.stdout = "error: unknown option '--json'\n"
    fake.stderr = ""
    fake.returncode = 1
    with patch("harness.harness.subprocess.run", return_value=fake):
        res = run_detect_changes()
    assert res["high"] is False
    assert res["unknown"] is False
    assert res["infra_error"] is True


def test_run_detect_changes_multi_repo_reintenta_con_repo() -> None:
    """Caso 2026-09-04: multi-repo exige --repo; reintento resuelve a low."""
    multi = MagicMock()
    multi.stdout = ""
    multi.stderr = "Multiple repositories indexed. Available: embodied-ai"
    multi.returncode = 1
    clean = MagicMock()
    clean.stdout = "No changes detected."
    clean.stderr = ""
    clean.returncode = 0
    with patch("harness.harness.subprocess.run") as run:
        run.side_effect = [multi, clean]
        res = run_detect_changes()
    assert res["high"] is False
    assert res["unknown"] is False
    assert run.call_count == 2
    assert "--repo" in run.call_args[0][0]


def test_build_evidence_infra_no_marca_high() -> None:
    with patch(
        "harness.harness.run_detect_changes",
        return_value={
            "impacted_nodes": 0,
            "changed_lines": 0,
            "high": False,
            "unknown": False,
            "infra_error": True,
            "raw": "error: unknown option '--json'",
        },
    ):
        ev, _ = build_evidence("test-infra")
        assert ev.risk != "high"
        assert any("infra" in u for u in ev.uncovered)
