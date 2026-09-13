"""Comandos drone por gestos mano con failsafe (Ticket 03 handoff drone-reid).

Vocabulario 057 fase 1 indoor (literales de `backend/inference/gesture.py`):
 - fist → acercar (paso fijo lento; al soltar → quieto)
 - open_palm → alejar (paso fijo lento; al soltar → quieto)
 - none → quieto flotando (deadman)
 - thumbs_up x2 en 3s → aterrizar (x1 no-op; vuelo atado hasta 10 limpios)

Seguridad (053): sin heartbeat 500ms → corta motores (retorna None).
Latch ABORTED → ignora todo hasta reset externo (retorna None).
FSM separa registro vs vuelo: este modulo SOLO corre en modo vuelo; en
modo registro los labels los sigue consumiendo `MissionFSM.handle_gesto`.

Puro y headless: la capa WS inyecta `heartbeat_ok`/`aborted` y serializa
el cmd resultante. Sin importar ws.py/fsm.py.
"""

from __future__ import annotations

HEARTBEAT_TIMEOUT_MS = 500
LAND_WINDOW_MS = 3000
LAND_COUNT = 2

_GESTURE_CMD: dict[str, str] = {
    "fist": "acercar",
    "open_palm": "alejar",
    "none": "quieto",
}


class Heartbeat:
    """Watchdog 500ms: sin marca reciente el enlace se considera caido."""

    def __init__(self, timeout_ms: int = HEARTBEAT_TIMEOUT_MS) -> None:
        self.timeout_ms = timeout_ms
        self._last_ms: int | None = None

    def mark(self, now_ms: int) -> None:
        self._last_ms = now_ms

    def expired(self, now_ms: int) -> bool:
        if self._last_ms is None:
            return True
        return now_ms - self._last_ms > self.timeout_ms


class LandingArbiter:
    """Pide confirmacion x2 en ventana: 1 pulgar no hace nada."""

    def __init__(
        self, window_ms: int = LAND_WINDOW_MS, count: int = LAND_COUNT
    ) -> None:
        self.window_ms = window_ms
        self.count = count
        self._hits: list[int] = []

    def observe(self, label: str, now_ms: int) -> bool:
        """Registra gesto; True solo cuando completa el aterrizaje."""
        if label != "thumbs_up":
            self._hits.clear()
            return False
        cutoff = now_ms - self.window_ms
        self._hits = [t for t in self._hits if t >= cutoff]
        self._hits.append(now_ms)
        if len(self._hits) >= self.count:
            self._hits.clear()
            return True
        return False


def resolve_drone_cmd(
    label: str,
    *,
    now_ms: int,
    heartbeat_ok: bool,
    aborted: bool,
    arbiter: LandingArbiter,
) -> str | None:
    """Mapea gesto → comando en modo vuelo. None = no-op / motores cortados."""
    if aborted or not heartbeat_ok:
        return None
    if label == "thumbs_up":
        return "aterrizar" if arbiter.observe(label, now_ms) else None
    cmd = _GESTURE_CMD.get(label)
    if cmd is None:
        return None
    arbiter.observe(label, now_ms)
    return cmd
