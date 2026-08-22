"""WhiteboardState — spec Pydantic para 010, memoria only, single-writer."""

from typing import Literal

from pydantic import BaseModel, Field

from plataforma.sim.models import SimMetrics, SimObservation

try:
    import sys

    sys.path.insert(0, "fase-1")
    from orchestrator import DecisionAgentica  # type: ignore[import-not-found]
except ImportError:
    # fallback stub para prototype sin fase-1 instalado
    from pydantic import BaseModel as _BM

    class DecisionAgentica(_BM):  # type: ignore[no-redef]
        accion: str
        razon: str
        nivel_confianza: float


class GestoReconocido(BaseModel):
    """Evento dominio espejo CONTEXT.md:56 — label N=5 histéresis fuera."""

    label: Literal["open_palm", "fist", "thumbs_up", "none"] = Field(
        description="gesto"
    )
    conf: float = Field(ge=0.0, le=1.0, description="confianza")
    frame_id: int = Field(description="frame id origen")
    ts: float = Field(description="unix ms")


class WhiteboardState(BaseModel):
    """Intercambio entre nodos graph — sin transcript (voz queda en webcam)."""

    estado: Literal["SIM_IDLE", "SIM_RUNNING", "SIM_PAUSED", "SIM_ABORTED"] = Field(
        default="SIM_IDLE", description="estado FSM sim"
    )
    frame_id: int = Field(default=0, description="tick 10Hz")
    last_gesto: GestoReconocido | None = Field(default=None, description="último gesto")
    last_observation: SimObservation | None = Field(
        default=None, description="última obs"
    )
    last_decision: DecisionAgentica | None = Field(
        default=None, description="última decisión LLM"
    )
    metrics: SimMetrics | None = Field(default=None, description="métricas sim")
