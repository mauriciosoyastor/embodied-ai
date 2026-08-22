"""Tests para MujocoAdapter — física real MuJoCo."""

from plataforma.sim.models import CmdVel
from plataforma.sim.mujoco_adapter import MujocoAdapter


def test_mujoco_adapter_inicializacion() -> None:
    adapter = MujocoAdapter()
    obs = adapter.get_observation()
    assert obs.x == 0.0
    assert obs.y == 0.0
    assert obs.frame_id == 0


def test_mujoco_adapter_step_movimiento() -> None:
    adapter = MujocoAdapter()
    adapter.send_cmd_vel(CmdVel(v_x=0.5, omega_z=0.1))
    obs = adapter.step(dt_ms=100.0)
    metrics = adapter.get_metrics()

    assert obs.frame_id == 1
    assert metrics.steps == 1
    assert metrics.steps_per_s > 0.0
    # Con velocidad lineal positiva, la posición x debería avanzar
    assert obs.x >= 0.0


def test_mujoco_adapter_multi_step_loop() -> None:
    adapter = MujocoAdapter()
    adapter.send_cmd_vel(CmdVel(v_x=0.2, omega_z=0.0))
    for _ in range(5):
        obs = adapter.step(dt_ms=100.0)
    assert obs.frame_id == 5
    assert adapter.get_metrics().steps == 5
