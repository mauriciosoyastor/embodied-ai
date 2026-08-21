"""FSM de misión webcam — S2-C handle_gesto con histéresis y latch ABORTED.

Contratos D5 (#43) / D6 (#44) y spec S2-C (#52):
- Estados: IDLE → RUNNING ↔ PAUSED → ABORTED → IDLE (via reset)
- Mapeo: thumbs_up → RUNNING, open_palm → PAUSED, fist → ABORTED, none = no-op
- Histéresis: N=5 frames consecutivos mismo label con conf>=0.7 (~500 ms @10 Hz)
- Latch: ABORTED enclava, ignora thumbs_up/open_palm hasta reset()
- evento_observacion: hook no-op, no dispara transición
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Literal

GestureLabel = Literal["open_palm", "fist", "thumbs_up", "none"]
ALLOWED_LABELS: frozenset[str] = frozenset({"open_palm", "fist", "thumbs_up", "none"})

HYSTERESIS_N: int = 5
CONF_THRESHOLD: float = 0.7


class Estado(enum.Enum):
    """Estados de misión — máquina IDLE→RUNNING↔PAUSED→ABORTED→IDLE."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ABORTED = "ABORTED"


@dataclass(frozen=True, slots=True)
class GestoReconocido:
    """Evento de dominio desacoplado de MediaPipe — consume handle_gesto."""

    label: GestureLabel
    conf: float
    frame_id: int
    ts: int


class MissionFSM:
    """FSM pura de misión con histéresis y latch ABORTED.

    Uso headless:
        fsm = MissionFSM()
        estado = fsm.handle_gesto(GestoReconocido(...))
    """

    def __init__(self, estado_inicial: Estado = Estado.IDLE) -> None:
        self.estado: Estado = estado_inicial
        self._last_label: GestureLabel | None = None
        self._count: int = 0

    # ------------------------------------------------------------------
    # Histéresis interna
    # ------------------------------------------------------------------

    def _reset_hysteresis(self) -> None:
        self._last_label = None
        self._count = 0

    def _clear_after_transition(self) -> None:
        self._last_label = None
        self._count = 0

    def _update_hysteresis(self, label: GestureLabel) -> bool:
        """Actualiza contador consecutivo y retorna True si N alcanzado."""
        if label == self._last_label:
            self._count += 1
        else:
            self._last_label = label
            self._count = 1
        return self._count >= HYSTERESIS_N

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def handle_gesto(self, event: GestoReconocido) -> Estado:
        """Transición pura con histéresis y latch ABORTED.

        - conf < 0.7 o label==none → no-op + reset histéresis
        - ABORTED latch → ignora thumbs_up/open_palm aunque N satisfecho
        - Prioridad ABORTED > PAUSED > RUNNING (fist siempre aborta)
        """
        # no-op: none o confianza baja → reset y retornar estado actual
        if event.label == "none" or event.conf < CONF_THRESHOLD:
            self._reset_hysteresis()
            return self.estado

        # Validación defensiva: label fuera de ALLOWED → no-op
        if event.label not in ALLOWED_LABELS:
            self._reset_hysteresis()
            return self.estado

        # Latch ABORTED: enclavado hasta reset() explícito
        if self.estado == Estado.ABORTED:
            # Actualizamos histéresis para mantener counters coherentes,
            # pero no transitamos a RUNNING/PAUSED aunque se alcance N.
            self._update_hysteresis(event.label)
            return self.estado

        # Histéresis normal
        ready = self._update_hysteresis(event.label)
        if not ready:
            return self.estado

        # Histéresis satisfecha → aplicar mapeo con prioridad
        if event.label == "fist":
            self.estado = Estado.ABORTED
            self._clear_after_transition()
        elif event.label == "open_palm":
            self.estado = Estado.PAUSED
            self._clear_after_transition()
        elif event.label == "thumbs_up":
            self.estado = Estado.RUNNING
            self._clear_after_transition()
        else:
            # none ya filtrado arriba; defensivo
            self._reset_hysteresis()
        return self.estado

    def reset(self) -> Estado:
        """Resetea latch ABORTED → IDLE y limpia histéresis."""
        self._reset_hysteresis()
        self.estado = Estado.IDLE
        return self.estado

    def on_observacion(self, *args: object, **kwargs: object) -> None:
        """Hook para evento_observacion YOLO (person conf>0.6 area>15%).

        Solo telemetría/log — no dispara transición. No-op intencional.
        Firma variádica para aceptar dict o kwargs sin acoplar caller.
        """
        _ = args
        _ = kwargs
        return None
