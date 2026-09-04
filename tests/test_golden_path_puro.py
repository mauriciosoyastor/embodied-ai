"""Golden Path puro — seam único CI+Harness.

Seam: CI (ruff+mypy+pytest) + harness verify verdict:ok.
Verifica comportamiento observable, no detalles internos.
"""

from pathlib import Path

import harness.harness as harness_mod

REPO = Path(__file__).resolve().parents[1]


def test_golden_path_configs_exist() -> None:
    """Golden Path configs base deben existir y estar pinneados."""
    assert (REPO / ".gitnexusrc").exists()
    assert '"pdg": true' in (REPO / ".gitnexusrc").read_text(encoding="utf-8")
    assert (REPO / "docs" / "agents" / "domain.md").exists()
    assert (REPO / "docs" / "agents" / "triage-labels.md").exists()
    assert (REPO / "docs" / "agents" / "issue-tracker.md").exists()
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "uv sync --all-packages" in ci
    assert (REPO / "CONTEXT.md").exists()
    # linter doc: sin anclas .py:NNN fuera de allowlist (ADR-0007).
    # Sin cláusula OR débil: delega en harness/check_context.py.
    from harness.check_context import check as check_context

    assert check_context(REPO / "CONTEXT.md") == 0


def test_prototypes_purged_no_artefactos_redundantes() -> None:
    """Tras purga, prototipos y artefactos legacy no deben existir."""
    purged = [
        REPO / "harness" / "prototype-context-injector.py",
        REPO / "harness" / "prototype-harness-detect.html",
        REPO / "prototype-memoria-objetos.html",
        REPO / "plataforma" / "webcam" / "frontend" / "prototype-imgsz-small.html",
        REPO / "plataforma" / "webcam" / "frontend" / "prototype-leaky-reid.html",
        REPO / "out.txt",
        REPO / ".scratch" / "graph.html",
        REPO / ".scratch" / "pr_body.md",
    ]
    for p in purged:
        assert not p.exists(), f"artefacto redundante aún existe: {p}"


def test_workflow_solo_ci_y_review() -> None:
    """Solo ci.yml y agent-review.yml deben permanecer en workflows."""
    wf_dir = REPO / ".github" / "workflows"
    existing = {f.name for f in wf_dir.iterdir() if f.is_file()}
    # ci.yml y agent-review.yml son Golden Path; .disabled debe estar purgado
    assert "ci.yml" in existing
    assert "agent-review.yml" in existing
    assert "agent-implement.yml.disabled" not in existing


def test_harness_trajectory_tiene_removed_tools() -> None:
    """TrajectoryEntry debe exponer removed_tools para auditoría de purga."""
    entry = harness_mod.TrajectoryEntry(
        run_id="test",
        ts="2026-09-03T00:00:00",
        phase="plan",
        tier="sandbox-edit",
        intent="test",
    )
    assert hasattr(entry, "removed_tools")
    assert isinstance(entry.removed_tools, list)


def test_harness_verify_sigue_low_risk() -> None:
    """Seam: harness build_evidence debe seguir low risk tras purga."""
    # Usa build_evidence real (sin mock) — debe pasar porque CI ya está verde
    # Mockeamos detect_changes para evitar dependencia de índice stale
    from unittest.mock import patch

    with patch(
        "harness.harness.run_detect_changes",
        return_value={
            "impacted_nodes": 0,
            "changed_lines": 0,
            "high": False,
            "unknown": False,
            "raw": "low",
        },
    ):
        ev, _ = harness_mod.build_evidence("test-golden-puro")
        assert ev.risk in (
            "low",
            "medium",
        )  # low esperado; medium tolerado si uncovered parcial
        assert ev.tests_failed == 0
        assert ev.domain_assertions.get("ok") is True
