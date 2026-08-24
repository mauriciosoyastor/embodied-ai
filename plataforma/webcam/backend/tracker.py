"""ByteTrack ligero — MOT IoU greedy stub S2-A (expand, sin comportamiento nuevo).

Interfaz para S2-B: `ByteTrack.update(boxes) -> track_ids`.
Headless sin OpenCV, <1ms. S2-A: asigna nuevo track_id incremental
(no re-id real), mantiene contrato. S2-B lo hará persistente IoU>0.5 + edad 30.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ByteTrack:
    """Tracker IoU greedy stub — S2-A expand.

    Atributos para config centralizada (inyectados desde config.py).
    S2-B implementará matching real IoU>0.5 + LRU; este stub mantiene API.
    """

    max_age: int = 30
    iou_threshold: float = 0.5
    _next_id: int = field(default=1, init=False, repr=False)
    _is_stub: bool = field(default=True, init=False, repr=False)

    @property
    def is_stub(self) -> bool:
        return self._is_stub

    def update(self, boxes: list[object] | None) -> list[int]:
        """Asigna track_id incremental por box (stub, sin persistencia)."""
        if not boxes:
            return []
        ids: list[int] = []
        for _ in boxes:
            ids.append(self._next_id)
            self._next_id += 1
            if self._next_id > 10_000:
                self._next_id = 1
        return ids

    def reset(self) -> None:
        self._next_id = 1


def get_tracker() -> ByteTrack:
    """Factory S2-A — stub siempre, S2-B lo hará real con config."""
    from plataforma.webcam.backend.config import LRU_SIZE, TRACK_MAX_AGE

    _ = LRU_SIZE  # reservado para S2-B LRU64
    return ByteTrack(max_age=TRACK_MAX_AGE)
