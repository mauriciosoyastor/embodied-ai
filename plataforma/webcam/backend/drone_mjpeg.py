"""Adapter MJPEG XIAO S3 Sense → /ws/percepcion (Ticket 01 handoff drone-reid).

 consume el WS existente sin modificar `ws.py` core:
 - QVGA continuo para pilotar (~150ms glass-to-glass).
 - Snapshot VGA bajo demanda cuando YOLO ve `person` con conf alta.
 - Politica leaky N=1: solo el frame mas reciente (sin lag acumulado).

Sin dependencias nuevas: stdlib + tipos del backend.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from plataforma.webcam.backend.config import YOLO_PERSON_CONF

_SOI = b"\xff\xd8\xff"
_EOI = b"\xff\xd9"


def split_mjpeg_frames(stream: bytes) -> list[bytes]:
    """Parte un chunk MJPEG en frames JPEG (SOI..EOI). Sin pares → []."""
    frames: list[bytes] = []
    start = 0
    while True:
        soi = stream.find(_SOI, start)
        if soi < 0:
            break
        eoi = stream.find(_EOI, soi + len(_SOI))
        if eoi < 0:
            break
        frames.append(stream[soi : eoi + len(_EOI)])
        start = eoi + len(_EOI)
    return frames


class LeakyFrame[T]:
    """Leaky sincrono N=1 para el lado ingesta (mirror de LeakyQueue)."""

    def __init__(self) -> None:
        self._deque: deque[T] = deque(maxlen=1)

    def push(self, item: T) -> bool:
        """Guarda; retorna True si descarto el previo."""
        discarded = len(self._deque) == 1
        self._deque.append(item)
        return discarded

    def pop(self) -> T | None:
        if not self._deque:
            return None
        return self._deque.popleft()


def should_snapshot_vga(
    detecciones: list[dict[str, Any]],
    conf_min: float = YOLO_PERSON_CONF,
) -> bool:
    """True si hay `person` con conf >= umbral: pide snapshot VGA ReID."""
    for det in detecciones:
        if str(det.get("cls")) != "person":
            continue
        try:
            conf = float(det.get("conf", 0.0))
        except (TypeError, ValueError):
            continue
        if conf >= conf_min:
            return True
    return False
