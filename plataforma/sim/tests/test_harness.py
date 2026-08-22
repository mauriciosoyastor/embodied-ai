"""Harness headless TDD — baseline verde sin red ni MuJoCo."""

import pytest
from pydantic_ai.models.test import TestModel

from plataforma.sim.fake_adapter import FakeAdapter
from plataforma.sim.models import CmdVel


def test_fake_adapter_obs_advances_on_step() -> None:
    adapter = FakeAdapter()
    obs0 = adapter.get_observation()
    assert obs0.frame_id == 0
    adapter.send_cmd_vel(CmdVel(v_x=0.5, omega_z=0.0))
    obs1 = adapter.step(dt_ms=100.0)
    assert obs1.frame_id == 1
    assert obs1.x > obs0.x  # avanzó en x
    assert obs1.v_x == pytest.approx(0.5)
    metrics = adapter.get_metrics()
    assert metrics.steps == 1
    assert metrics.steps_per_s == pytest.approx(10.0)


def test_cmd_vel_clamp_via_pydantic() -> None:
    # Pydantic valida clamp — valores fuera de rango deben elevar ValidationError
    with pytest.raises(Exception):
        CmdVel(v_x=2.0, omega_z=0.0)  # >1.0
    with pytest.raises(Exception):
        CmdVel(v_x=0.0, omega_z=2.0)  # >1.5


def test_orquestador_headless_con_testmodel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida harness orquestador sin red — monkeypatch dummy key para TestModel."""
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    monkeypatch.setenv("OPENCODE_API_KEY", "dummy-key")

    # import lazy para no acoplar hard a fase-1 en CI si falta deps
    import sys

    sys.path.insert(0, "fase-1")
    from orchestrator import (  # type: ignore[import-not-found]
        DecisionAgentica,
        HardwareContext,
        crear_orquestador,
    )

    agent = crear_orquestador()
    custom = DecisionAgentica(
        accion="avanzar", razon="test harness", nivel_confianza=0.9
    )
    with agent.override(model=TestModel(custom_output_args=custom)):
        deps = HardwareContext(sensor_activo=True, bateria_nivel=80.0)
        result = agent.run_sync("evaluar", deps=deps)
        assert result.output.accion == "avanzar"
        # bridge a sim: decisión → CmdVel
        cmd = (
            CmdVel(v_x=0.5, omega_z=0.0)
            if result.output.accion == "avanzar"
            else CmdVel(v_x=0.0, omega_z=0.0)
        )
        adapter = FakeAdapter()
        adapter.send_cmd_vel(cmd)
        obs = adapter.step()
        assert obs.v_x == pytest.approx(0.5)
