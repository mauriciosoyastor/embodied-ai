"""OTel / Prometheus métricas S2-D — cache_hit_ratio, ttl_expirations, glass_to_glass.

Sin dependencia externa, expone texto Prometheus para GET /metrics.
S2-B LRU y S2-C Zero-Copy y S1 AtributoVista alimentan contadores.
"""

from __future__ import annotations

import time
from collections import Counter

# contadores en memoria
_cache_hits: int = 0
_cache_misses: int = 0
_ttl_expirations: Counter[str] = Counter()
_glass_samples: list[float] = []
_yolo_samples: list[float] = []
_start_ms: int = int(time.time() * 1000)


def record_cache_hit() -> None:
    global _cache_hits
    _cache_hits += 1


def record_cache_miss() -> None:
    global _cache_misses
    _cache_misses += 1


def record_ttl_expiration(field: str) -> None:
    _ttl_expirations[field] += 1


def record_glass(ms: float) -> None:
    _glass_samples.append(float(ms))
    if len(_glass_samples) > 200:
        _glass_samples.pop(0)


def record_yolo(ms: float) -> None:
    _yolo_samples.append(float(ms))
    if len(_yolo_samples) > 200:
        _yolo_samples.pop(0)


def _p50(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[len(s) // 2]


def _p95(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = int(len(s) * 0.95)
    return s[min(idx, len(s) - 1)]


def render_prometheus() -> str:
    try:
        from plataforma.webcam.backend.tracker import get_tracker

        t = get_tracker()
        hits = t.lru.hits
        misses = t.lru.misses
        total = hits + misses
        ratio = t.lru.hit_ratio if total else 0.0
    except Exception:
        hits, misses, ratio = _cache_hits, _cache_misses, 0.0
        total = hits + misses
        ratio = hits / total if total else 0.0

    lines: list[str] = []
    lines.append("# HELP cache_hit_ratio LRU hit ratio S2-B")
    lines.append("# TYPE cache_hit_ratio gauge")
    lines.append(f"cache_hit_ratio {ratio:.3f}")
    lines.append("# HELP cache_hits total hits")
    lines.append("# TYPE cache_hits counter")
    lines.append(f"cache_hits {hits}")
    lines.append("# HELP cache_misses total misses")
    lines.append("# TYPE cache_misses counter")
    lines.append(f"cache_misses {misses}")
    lines.append("# HELP ttl_expirations TTL expirations por campo")
    lines.append("# TYPE ttl_expirations counter")
    for field, cnt in _ttl_expirations.items():
        lines.append(f'ttl_expirations{{field="{field}"}} {cnt}')
    if not _ttl_expirations:
        lines.append('ttl_expirations{field="color_hsv"} 0')
        lines.append('ttl_expirations{field="z_rel"} 0')
    lines.append("# HELP glass_to_glass_p50_ms Glass-to-Glass p50")
    lines.append("# TYPE glass_to_glass_p50_ms gauge")
    lines.append(f"glass_to_glass_p50_ms {_p50(_glass_samples):.1f}")
    lines.append("# HELP glass_to_glass_p95_ms Glass-to-Glass p95")
    lines.append("# TYPE glass_to_glass_p95_ms gauge")
    lines.append(f"glass_to_glass_p95_ms {_p95(_glass_samples):.1f}")
    lines.append("# HELP yolo_infer_p50_ms YOLO infer p50")
    lines.append("# TYPE yolo_infer_p50_ms gauge")
    lines.append(f"yolo_infer_p50_ms {_p50(_yolo_samples):.1f}")
    lines.append(f"uptime_ms {int(time.time() * 1000 - _start_ms)}")
    return "\n".join(lines) + "\n"


def reset() -> None:
    global _cache_hits, _cache_misses
    _cache_hits = 0
    _cache_misses = 0
    _ttl_expirations.clear()
    _glass_samples.clear()
    _yolo_samples.clear()
