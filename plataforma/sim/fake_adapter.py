"""FakeAdapter — sin simulador real, 10Hz mock, cinemática diferencial dummy."""

import math
import time

from plataforma.sim.models import CmdVel, SimMetrics, SimObservation


class FakeAdapter:
    """Adapter sin motor físico — respeta Protocol para tests/demos."""

    def __init__(self) -> None:
        self._x: float = 0.0
        self._y: float = 0.0
        self._yaw: float = 0.0
        self._v_x: float = 0.0
        self._omega_z: float = 0.0
        self._frame_id: int = 0
        self._steps: int = 0
        self._wall_ms: float = 0.0
        self._last_dt: float = 100.0

    def send_cmd_vel(self, cmd: CmdVel) -> None:
        # clamp ya validado por Pydantic; fallback clamp defensivo
        self._v_x = max(-1.0, min(1.0, cmd.v_x))
        self._omega_z = max(-1.5, min(1.5, cmd.omega_z))

    def get_observation(self) -> SimObservation:
        return SimObservation(
            x=self._x,
            y=self._y,
            yaw=self._yaw,
            v_x=self._v_x,
            v_y=0.0,
            omega_z=self._omega_z,
            ts=time.time() * 1000.0,
            frame_id=self._frame_id,
        )

    def get_metrics(self) -> SimMetrics:
        sps = 1000.0 / self._last_dt if self._last_dt > 0 else 0.0
        return SimMetrics(
            steps=self._steps,
            wall_time_ms=self._wall_ms,
            dt_ms=self._last_dt,
            steps_per_s=sps,
        )

    def step(self, dt_ms: float = 100.0) -> SimObservation:
        """Avanza pose por dt usando cinemática diferencial simple."""
        dt_s = dt_ms / 1000.0
        # integración yaw y posición world-frame
        self._yaw += self._omega_z * dt_s
        # normaliza yaw a [-pi, pi] para mypy/estabilidad
        self._yaw = math.atan2(math.sin(self._yaw), math.cos(self._yaw))
        self._x += self._v_x * math.cos(self._yaw) * dt_s
        self._y += self._v_x * math.sin(self._yaw) * dt_s
        self._frame_id += 1
        self._steps += 1
        self._wall_ms += dt_ms
        self._last_dt = dt_ms
        return self.get_observation()
