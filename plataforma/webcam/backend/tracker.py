"""ByteTrack ligero — MOT IoU greedy + LRU64 S2-B (persistente, <1ms).

S2-A scaffold era stub incremental; S2-B implementa matching IoU>0.5 + edad 30
+ LRU cache color_hsv IoU>0.85 TTL 2s para evitar recalcular histograma.
Headless sin OpenCV, pure python.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any


def _iou(a: dict[str, float], b: dict[str, float]) -> float:
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


@dataclass(slots=True)
class LRUCache:
    """LRU 64 con TTL 2s para color_hsv — evita recalcular histograma."""

    maxsize: int = 64
    ttl_ms: int = 2000
    _store: OrderedDict[int, dict[str, Any]] = field(
        default_factory=OrderedDict, init=False, repr=False
    )  # type: ignore
    hits: int = field(default=0, init=False)
    misses: int = field(default=0, init=False)

    def get(
        self, track_id: int, bbox: dict[str, float], now_ms: int | None = None
    ) -> dict[str, Any] | None:
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        entry = self._store.get(track_id)
        if entry is None:
            self.misses += 1
            return None
        # TTL
        if now_ms - int(entry.get("ts", 0)) > self.ttl_ms:
            self._store.pop(track_id, None)
            self.misses += 1
            return None
        # IoU >0.85 para reuse
        cached_bbox = entry.get("bbox")
        if not isinstance(cached_bbox, dict):
            self.misses += 1
            return None
        if _iou(cached_bbox, bbox) < 0.85:
            self.misses += 1
            return None
        # hit — mover al final (LRU)
        self._store.move_to_end(track_id)
        self.hits += 1
        return entry

    def put(
        self,
        track_id: int,
        bbox: dict[str, float],
        color_hsv: str,
        color_hex: str,
        ts: int | None = None,
    ) -> None:
        if ts is None:
            ts = int(time.time() * 1000)
        if track_id in self._store:
            self._store.move_to_end(track_id)
        self._store[track_id] = {
            "bbox": dict(bbox),
            "color_hsv": color_hsv,
            "color_hex": color_hex,
            "ts": ts,
        }
        if len(self._store) > self.maxsize:
            self._store.popitem(last=False)

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0


@dataclass(slots=True)
class ByteTrack:
    """Tracker IoU greedy persistente — S2-B.

    Mantiene tracks con edad max_age 30, matching IoU>0.5 greedy.
    S2-A stub solo incrementaba; este mantiene contrato + persistencia.
    """

    max_age: int = 30
    iou_threshold: float = 0.5
    _next_id: int = field(default=1, init=False, repr=False)
    _tracks: dict[int, dict[str, Any]] = field(
        default_factory=dict, init=False, repr=False
    )  # type: ignore
    _is_stub: bool = field(default=False, init=False, repr=False)
    lru: LRUCache = field(default_factory=LRUCache, init=False, repr=False)

    @property
    def is_stub(self) -> bool:
        return self._is_stub

    def _box_to_dict(self, b: Any) -> dict[str, float]:
        if isinstance(b, dict):
            return {
                "x": float(b.get("x", 0)),
                "y": float(b.get("y", 0)),
                "w": float(b.get("w", 0)),
                "h": float(b.get("h", 0)),
            }
        return {
            "x": float(getattr(b, "x", 0)),
            "y": float(getattr(b, "y", 0)),
            "w": float(getattr(b, "w", 0)),
            "h": float(getattr(b, "h", 0)),
        }

    def update(self, boxes: list[Any] | None) -> list[int]:
        """Asigna track_id persistente por IoU greedy; edad 30."""
        if not boxes:
            # envejecer tracks sin detecciones
            for tid in list(self._tracks.keys()):
                self._tracks[tid]["age"] = int(self._tracks[tid].get("age", 0)) + 1
                if self._tracks[tid]["age"] > self.max_age:
                    self._tracks.pop(tid, None)
            return []
        # dict bbox por idx
        new_bboxes: list[dict[str, float]] = [self._box_to_dict(b) for b in boxes]
        # matching greedy: por cada nueva box, buscar mejor track no asignado
        track_ids = list(self._tracks.keys())
        assigned: set[int] = set()
        result: list[int] = []
        # ordenar nuevas boxes por área descendente para estabilidad (opcional)
        order = sorted(
            range(len(new_bboxes)),
            key=lambda i: new_bboxes[i]["w"] * new_bboxes[i]["h"],
            reverse=True,
        )
        # mapa idx -> track_id asignado
        mapping: dict[int, int] = {}
        for idx in order:
            nb = new_bboxes[idx]
            best_tid: int | None = None
            best_iou = 0.0
            for tid in track_ids:
                if tid in assigned:
                    continue
                tb = self._tracks[tid].get("bbox")
                if not isinstance(tb, dict):
                    continue
                iou = _iou(tb, nb)
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_tid = tid
            if best_tid is not None:
                mapping[idx] = best_tid
                assigned.add(best_tid)
            else:
                nid = self._next_id
                self._next_id += 1
                if self._next_id > 10_000:
                    self._next_id = 1
                mapping[idx] = nid
                assigned.add(nid)
        # envejecer no asignados y crear/actualizar
        unseen = set(track_ids) - assigned
        for tid in unseen:
            self._tracks[tid]["age"] = int(self._tracks[tid].get("age", 0)) + 1
            if self._tracks[tid]["age"] > self.max_age:
                self._tracks.pop(tid, None)
        # resultado en orden original
        for i in range(len(new_bboxes)):
            tid = mapping[i]
            # actualizar track
            self._tracks[tid] = {"bbox": dict(new_bboxes[i]), "age": 0}
            result.append(tid)
        return result

    def reset(self) -> None:
        self._next_id = 1
        self._tracks.clear()
        self.lru.clear()


_tracker_singleton: ByteTrack | None = None


def get_tracker() -> ByteTrack:
    """Singleton S2-B — persiste cross-frame, reseteable en tests."""
    global _tracker_singleton
    if _tracker_singleton is None:
        from plataforma.webcam.backend.config import (
            LRU_SIZE,
            LRU_TTL_MS,
            TRACK_IOU_THRESHOLD,
            TRACK_MAX_AGE,
        )

        _tracker_singleton = ByteTrack(
            max_age=TRACK_MAX_AGE, iou_threshold=TRACK_IOU_THRESHOLD
        )
        _tracker_singleton.lru = LRUCache(maxsize=LRU_SIZE, ttl_ms=LRU_TTL_MS)
    return _tracker_singleton
