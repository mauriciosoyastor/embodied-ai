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
_world_samples: list[float] = []
_inference_samples: list[float] = []
_total_samples: list[float] = []
_fps_samples: list[float] = []
_dropped_frames_total: int = 0
_start_ms: int = int(time.time() * 1000)
# Voz: fast-path determinista (intent) vs slow-path LLM/VLM (proveedor).
_voz_fast: Counter[str] = Counter()
_voz_slow: Counter[str] = Counter()
_voz_offline: int = 0


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


def record_world(ms: float) -> None:
    _world_samples.append(float(ms))
    if len(_world_samples) > 200:
        _world_samples.pop(0)


def record_inference(ms: float) -> None:
    _inference_samples.append(float(ms))
    if len(_inference_samples) > 200:
        _inference_samples.pop(0)


def record_total(ms: float) -> None:
    _total_samples.append(float(ms))
    if len(_total_samples) > 200:
        _total_samples.pop(0)


def record_fps(fps: float) -> None:
    _fps_samples.append(float(fps))
    if len(_fps_samples) > 200:
        _fps_samples.pop(0)


def record_dropped_frame(n: int = 1) -> None:
    global _dropped_frames_total
    _dropped_frames_total += int(n)


def record_voz_fast(intent: str) -> None:
    """Un turno resuelto sin LLM (0ms, 0 tokens): saludo/meta/charla/s3/g3."""
    _voz_fast[str(intent)] += 1


def record_voz_slow(proveedor: str) -> None:
    """Un turno que llegó a la cadena LLM/VLM (latencia + tokens)."""
    _voz_slow[str(proveedor)] += 1


def record_offline(activo: bool) -> None:
    """1 si Groq está skipeado (OFFLINE_MODE), 0 si la nube responde."""
    global _voz_offline
    _voz_offline = 1 if activo else 0


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
    lines.append("# HELP world_infer_p50_ms YOLO-World infer p50 048")
    lines.append("# TYPE world_infer_p50_ms gauge")
    lines.append(f"world_infer_p50_ms {_p50(_world_samples):.1f}")
    lines.append("# HELP world_infer_p95_ms YOLO-World infer p95")
    lines.append("# TYPE world_infer_p95_ms gauge")
    lines.append(f"world_infer_p95_ms {_p95(_world_samples):.1f}")
    lines.append("# HELP inference_time_ms p50 total infer")
    lines.append("# TYPE inference_time_ms gauge")
    lines.append(f"inference_time_ms {_p50(_inference_samples):.1f}")
    lines.append("# HELP total_time_ms p50 glass-to-glass")
    lines.append("# TYPE total_time_ms gauge")
    lines.append(f"total_time_ms {_p50(_total_samples):.1f}")
    lines.append("# HELP fps gauge")
    lines.append("# TYPE fps gauge")
    lines.append(f"fps {_p50(_fps_samples):.1f}")
    lines.append("# HELP dropped_frames_total LeakyQueue drops")
    lines.append("# TYPE dropped_frames_total counter")
    lines.append(f"dropped_frames_total {_dropped_frames_total}")
    lines.append("# HELP voz_fast_path_total Turnos voz sin LLM por intencion")
    lines.append("# TYPE voz_fast_path_total counter")
    for intent in ("saludo", "charla", "meta", "s3_atributos", "g3_silencio"):
        lines.append(f'voz_fast_path_total{{intent="{intent}"}} {_voz_fast[intent]}')
    for intent, cnt in _voz_fast.items():
        if intent not in ("saludo", "charla", "meta", "s3_atributos", "g3_silencio"):
            lines.append(f'voz_fast_path_total{{intent="{intent}"}} {cnt}')
    lines.append("# HELP voz_slow_path_total Turnos voz via LLM/VLM por proveedor")
    lines.append("# TYPE voz_slow_path_total counter")
    for prov in ("ollama", "groq", "groq-fallback", "hf", "gemini", "openai", "mock"):
        lines.append(f'voz_slow_path_total{{proveedor="{prov}"}} {_voz_slow[prov]}')
    for prov, cnt in _voz_slow.items():
        if prov not in (
            "ollama",
            "groq",
            "groq-fallback",
            "hf",
            "gemini",
            "openai",
            "mock",
        ):
            lines.append(f'voz_slow_path_total{{proveedor="{prov}"}} {cnt}')
    lines.append("# HELP voz_offline_mode 1 si Groq skipeado (OFFLINE_MODE)")
    lines.append("# TYPE voz_offline_mode gauge")
    lines.append(f"voz_offline_mode {_voz_offline}")
    lines.append(f"uptime_ms {int(time.time() * 1000 - _start_ms)}")
    return "\n".join(lines) + "\n"


def reset() -> None:
    global _cache_hits, _cache_misses, _dropped_frames_total, _voz_offline
    _cache_hits = 0
    _cache_misses = 0
    _dropped_frames_total = 0
    _voz_offline = 0
    _voz_fast.clear()
    _voz_slow.clear()
    _ttl_expirations.clear()
    _glass_samples.clear()
    _yolo_samples.clear()
    _world_samples.clear()
    _inference_samples.clear()
    _total_samples.clear()
    _fps_samples.clear()
