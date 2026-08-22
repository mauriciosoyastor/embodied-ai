"""MissionState — dataclass wrapper para pydantic-graph ctx.state."""

from dataclasses import dataclass, field

from plataforma.sim.whiteboard import WhiteboardState


@dataclass
class MissionState:
    """StateT para GraphRunContext — whiteboard mutable tipado."""

    whiteboard: WhiteboardState = field(default_factory=WhiteboardState)

    @property
    def estado(self) -> str:
        return self.whiteboard.estado

    @estado.setter
    def estado(self, value: str) -> None:
        # validación laxa — Pydantic valida al serializar
        self.whiteboard.estado = value  # type: ignore[assignment]
