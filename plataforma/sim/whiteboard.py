"""WhiteboardState — spec Pydantic 010, memoria only, single-writer + v2."""

from __future__ import annotations

import time
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


class IdentidadVista(BaseModel):
    """Vista per-frame 033/034 + 040-042 memoria objetos — 5 estados con TTL vecino."""

    id: str = Field(description="nanoid galería o unk_*")
    nombre: str = Field(description="nombre galería o desconocido")
    cosine: float = Field(ge=0.0, le=2.0, description="distancia coseno 0..2")
    conf: float = Field(ge=0.0, le=1.0, description="conf 1-cosine o detector")
    estado: Literal[
        "confirmado", "posible", "ambiguo", "provisional", "desconocido"
    ] = Field(
        description="zona 0.42/0.55 N=3 + ambiguo white EMA*0.2 + provisional TENTATIVE"
    )
    box: dict[str, float] | None = Field(
        default=None, description="YOLO person box normalizada"
    )
    face_box: dict[str, float] | None = Field(
        default=None, description="BlazeFace bbox normalizada"
    )
    frame_id: int = Field(default=0, description="frame origen")
    ts: float = Field(default=0.0, description="unix ms")


# ---------------------------------------------------------------------------
# v2 Percepción Enriquecida
# ---------------------------------------------------------------------------


class LeyendaVista(BaseModel):
    """Leyenda de escena — replica LeyendaEscena VLM para whiteboard."""

    caption: str = Field(description="caption es-AR 1 frase")
    objects: list[str] = Field(default_factory=list, description="objetos whitelist")
    conf: float = Field(ge=0.0, le=1.0, description="conf 0-1")
    ts: float = Field(description="unix ms")
    provider: str = Field(default="mock", description="groq|hf|gemini|mock")
    frame_id: int = Field(default=0, description="frame origen")


class PercepcionVista(BaseModel):
    """Agregado v2 — TTL por campo, single-writer memoria."""

    frame_id: int = Field(default=0, description="tick correlación")
    detecciones: list[dict[str, float]] = Field(
        default_factory=list, description="boxes filtradas whitelist"
    )
    posturas: list[dict[str, object]] = Field(
        default_factory=list, description="posturas 17kp normalizados"
    )
    profundidades: list[dict[str, object]] = Field(
        default_factory=list, description="profundidades z_rel por bbox"
    )
    leyenda: LeyendaVista | None = Field(default=None, description="leyenda VLM 1Hz")

    # timestamps por campo para TTL
    ts_detecciones: float = Field(default=0.0, description="unix ms detecciones")
    ts_posturas: float = Field(default=0.0, description="unix ms posturas")
    ts_profundidades: float = Field(default=0.0, description="unix ms profundidades")
    ts_leyenda: float = Field(default=0.0, description="unix ms leyenda")

    # TTLs v2 (spec #81): 0.1 / 1.0 / 1.0 / 2.0 s
    TTL_DETECCIONES: float = 0.1
    TTL_POSTURAS: float = 1.0
    TTL_PROFUNDIDADES: float = 1.0
    TTL_LEYENDA: float = 2.0

    def is_detecciones_fresh(self, now: float | None = None) -> bool:
        if now is None:
            now = time.time()
        if not self.detecciones:
            return False
        return (now - self.ts_detecciones) <= self.TTL_DETECCIONES

    def is_posturas_fresh(self, now: float | None = None) -> bool:
        if now is None:
            now = time.time()
        if not self.posturas:
            return False
        return (now - self.ts_posturas) <= self.TTL_POSTURAS

    def is_profundidades_fresh(self, now: float | None = None) -> bool:
        if now is None:
            now = time.time()
        if not self.profundidades:
            return False
        return (now - self.ts_profundidades) <= self.TTL_PROFUNDIDADES

    def is_leyenda_fresh(self, now: float | None = None) -> bool:
        if now is None:
            now = time.time()
        if self.leyenda is None:
            return False
        return (now - self.ts_leyenda) <= self.TTL_LEYENDA


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
    last_identidades: list[IdentidadVista] | None = Field(
        default=None, description="ReID viva 033/034 — lista 0-3 client-side"
    )
    percepcion_vista: PercepcionVista | None = Field(
        default=None, description="v2 PercepcionVista con TTLs"
    )

    def update_percepcion(
        self,
        frame_id: int | None = None,
        detecciones: list[dict[str, float]] | None = None,
        posturas: list[dict[str, object]] | None = None,
        profundidades: list[dict[str, object]] | None = None,
        leyenda: LeyendaVista | None = None,
    ) -> bool:
        """Actualiza PercepcionVista; ABORTED overlay-only no muta."""
        if self.estado == "SIM_ABORTED":
            return False
        if self.percepcion_vista is None:
            self.percepcion_vista = PercepcionVista()

        now = time.time()
        if frame_id is not None:
            self.percepcion_vista.frame_id = frame_id
        if detecciones is not None:
            self.percepcion_vista.detecciones = detecciones
            self.percepcion_vista.ts_detecciones = now
        if posturas is not None:
            self.percepcion_vista.posturas = posturas
            self.percepcion_vista.ts_posturas = now
        if profundidades is not None:
            self.percepcion_vista.profundidades = profundidades
            self.percepcion_vista.ts_profundidades = now
        if leyenda is not None:
            self.percepcion_vista.leyenda = leyenda
            self.percepcion_vista.ts_leyenda = now
        return True
