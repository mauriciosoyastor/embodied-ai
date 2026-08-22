"""Protocol Bridge/Adapter — interfaz común para MuJoCo hoy, Gazebo/PX4 mañana."""

from typing import Protocol

from plataforma.sim.models import CmdVel, SimMetrics, SimObservation


class SimAdapter(Protocol):
    """Contrato que todo adapter debe cumplir."""

    def get_observation(self) -> SimObservation:
        """Devuelve estado actual SI/world-frame."""
        ...

    def send_cmd_vel(self, cmd: CmdVel) -> None:
        """Envía comando velocidad clamp; conversión a ruedas interna."""
        ...

    def get_metrics(self) -> SimMetrics:
        """Métricas del motor."""
        ...

    def step(self, dt_ms: float = 100.0) -> SimObservation:
        """Avanza sim un dt y devuelve nueva observación."""
        ...
