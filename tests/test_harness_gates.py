"""TDD Capas 2+3: human_gate en high + review_gate local."""

from unittest.mock import patch

from harness.harness import (
    EvidenceBundle,
    TrajectoryEntry,
    has_open_gate,
    review_gate,
    run_harness,
)


def _ev(**kw) -> EvidenceBundle:
    base = {
        "tests_failed": 0,
        "domain_assertions": {"ok": True},
        "risk": "low",
        "risk_reason": "sensores ok",
        "impact_ratio": 0.0,
    }
    base.update(kw)
    return EvidenceBundle(**base)


def test_run_harness_high_deja_gate_abierto() -> None:
    """Capa 2: risk high → entrada human_gate needed=True en traza."""
    seen: list[TrajectoryEntry] = []
    ev = _ev(risk="high", risk_reason="blast radius HIGH sin confirmar")
    with (
        patch("harness.harness.build_evidence", return_value=(ev, "log")),
        patch(
            "harness.harness.append_trajectory",
            side_effect=lambda e: seen.append(e),
        ),
    ):
        run_harness("test", "sandbox-edit", False, "gate01")
    gates = [e for e in seen if e.phase == "human_gate"]
    assert len(gates) == 1
    assert gates[0].human_gate.needed is True
    assert gates[0].verdict == "needs-human"


def test_run_harness_low_no_deja_gate() -> None:
    """Capa 2: risk low/medium → sin gate (medium va a N=3 en /golden-auto)."""
    seen: list[TrajectoryEntry] = []
    ev = _ev(risk="medium", risk_reason="cobertura parcial")
    with (
        patch("harness.harness.build_evidence", return_value=(ev, "log")),
        patch(
            "harness.harness.append_trajectory",
            side_effect=lambda e: seen.append(e),
        ),
    ):
        run_harness("test", "sandbox-edit", False, "gate02")
    assert [e for e in seen if e.phase == "human_gate"] == []


def test_review_gate_veredictos() -> None:
    """Capa 3: NEEDS-HUMAN / APPROVE_WITH_NOTES / APPROVE."""
    high = _ev(risk="high", risk_reason="x", impact_ratio=17.5)
    assert review_gate(high)["verdict"] == "NEEDS-HUMAN"
    broken = _ev(tests_failed=2)
    assert review_gate(broken)["verdict"] == "NEEDS-HUMAN"
    assert "tests_failed=2" in review_gate(broken)["reasons"]
    medium = _ev(risk="medium", risk_reason="parcial")
    assert review_gate(medium)["verdict"] == "APPROVE_WITH_NOTES"
    assert review_gate(_ev()) == {
        "verdict": "APPROVE",
        "reasons": [],
    }


def test_has_open_gate_abre_y_cierra(tmp_path) -> None:
    """Capa 2: gate abierto hasta approve (gate de merge)."""
    import json

    traj = tmp_path / "trajectory.jsonl"
    gate = {
        "run_id": "r1",
        "phase": "human_gate",
        "human_gate": {"needed": True, "reason": "high"},
    }
    ok = {
        "run_id": "r1",
        "phase": "human_gate",
        "human_gate": {"needed": False, "approved_by": "humano"},
    }
    traj.write_text(json.dumps(gate) + "\n", encoding="utf-8")
    with patch("harness.harness.TRAJECTORY", traj):
        assert has_open_gate("r1") is True
        assert has_open_gate("otro") is False
        traj.write_text(
            json.dumps(gate) + "\n" + json.dumps(ok) + "\n",
            encoding="utf-8",
        )
        assert has_open_gate("r1") is False
