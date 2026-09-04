"""TDD Capa 1-bis: guardián PDG fail-open — fresco sin reindex, stale repara."""

from unittest.mock import MagicMock, patch

from harness.harness import build_evidence, ensure_fresh_pdg


def test_fresh_green_no_reindex() -> None:
    """HEAD == lastCommit → fresh sin invocar subprocess."""
    with (
        patch("harness.harness._git_head", return_value="abc123"),
        patch("harness.harness._index_last_commit", return_value="abc123"),
        patch("harness.harness.subprocess.run") as run,
    ):
        res = ensure_fresh_pdg()
    assert res["fresh"] is True
    assert res["reindexed"] is False
    run.assert_not_called()


def test_stale_repara_con_reindex() -> None:
    """HEAD 2 ahead → analyze --index-only --pdg y fresh."""
    fake_rev = MagicMock()
    fake_rev.returncode = 0
    fake_rev.stdout = "2\n"
    fake_analyze = MagicMock()
    fake_analyze.returncode = 0
    fake_analyze.stdout = "indexed"
    fake_analyze.stderr = ""
    with (
        patch("harness.harness._git_head", return_value="HEAD999"),
        patch("harness.harness._index_last_commit", return_value="BASE111"),
        patch("harness.harness.subprocess.run") as run,
    ):
        run.side_effect = [fake_rev, fake_analyze]
        res = ensure_fresh_pdg(timeout_s=30)
    assert res["fresh"] is True
    assert res["reindexed"] is True
    assert run.call_count == 2
    analyze_cmd = run.call_args[0][0]
    assert analyze_cmd[:3] == ["node", ".gitnexus/run.cjs", "analyze"]


def test_infra_stale_es_medium_no_high() -> None:
    """Analyze roto → uncovered pdg stale, risk medium jamás high."""
    with (
        patch(
            "harness.harness.ensure_fresh_pdg",
            return_value={
                "fresh": False,
                "behind": 2,
                "reindexed": False,
                "infra": "analyze timeout 120s",
            },
        ),
        patch(
            "harness.harness.run_pytest",
            return_value=({"ok": True}, "log"),
        ),
        patch("harness.harness.run_ruff", return_value={"ok": True}),
        patch("harness.harness.run_mypy", return_value={"ok": True}),
        patch(
            "harness.harness.domain_assertions",
            return_value={"ok": True, "failures": []},
        ),
        patch(
            "harness.harness.run_detect_changes",
            return_value={
                "impacted_nodes": 0,
                "changed_lines": 0,
                "high": False,
                "unknown": False,
                "raw": "low",
            },
        ),
    ):
        ev, _ = build_evidence("test-pdg-infra")
    assert ev.risk == "medium"
    assert any("pdg stale" in u for u in ev.uncovered)
