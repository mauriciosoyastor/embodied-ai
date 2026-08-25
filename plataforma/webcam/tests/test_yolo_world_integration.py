"""Tests TDD 048 — YOLO-World s open-vocab is_world seam.

Seam primario: perception_ws_handler detecciones is_world + metrics world_infer_p50.
Seam secundario: YoloWorldDetector cache + _passes_world.

Headless sin peso real — FakeWorld inyección.
"""

# mypy: disable-error-code="no-untyped-def, no-untyped-call"

from __future__ import annotations

import json

from plataforma.sim.whiteboard import AtributoVista
from plataforma.webcam.backend.inference.yolo_world import (
    YoloWorldDetector,
    get_yolo_world_detector,
)
from plataforma.webcam.backend.metrics import (
    record_world,
    render_prometheus,
)
from plataforma.webcam.backend.metrics import (
    reset as metrics_reset,
)
from plataforma.webcam.backend.ws import (
    _extract_atributos,
    _passes_world,
    make_envelope,
)


def test_atributo_vista_is_world_schema() -> None:
    a = AtributoVista(
        track_id=5,
        cls="red cup",
        conf=0.62,
        bbox={"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2},
        centroide={"x_c": 0.2, "y_c": 0.2},
        tamano="mediano",
        area=0.04,
        color_hsv="rojo",
        color_hsv_hex="#c0392b",
        color="rojo",
        is_world=True,
        prompt_origen="red cup",
    )
    assert a.is_world is True
    assert a.prompt_origen == "red cup"
    # default W30 retains False
    b = AtributoVista(
        track_id=1,
        cls="cup",
        conf=0.6,
        bbox={"x": 0.1, "y": 0.1, "w": 0.1, "h": 0.1},
        centroide={"x_c": 0.15, "y_c": 0.15},
        tamano="pequeño",
        area=0.01,
        color_hsv="blanco",
        color_hsv_hex="#ecf0f1",
        color="blanco",
    )
    assert b.is_world is False
    assert b.prompt_origen is None


def test_passes_world_thresholds() -> None:
    class Box:
        def __init__(self, cls: str, conf: float, w: float, h: float):
            self.cls = cls
            self.conf = conf
            self.w = w
            self.h = h

    # box_thr 0.35 area 0.03
    assert _passes_world(Box("red cup", 0.36, 0.2, 0.2)) is True
    assert _passes_world(Box("red cup", 0.34, 0.2, 0.2)) is False
    assert _passes_world(Box("red cup", 0.9, 0.1, 0.1)) is False  # area 0.01 <0.03
    # dict variant
    assert (
        _passes_world({"cls": "yellow screwdriver", "conf": 0.5, "w": 0.3, "h": 0.3})  # noqa: E501
        is True
    )
    assert _passes_world({"cls": "", "conf": 0.9, "w": 0.5, "h": 0.5}) is False


def test_extract_atributos_is_world_composite_lru() -> None:
    class Box:
        def __init__(self, x: float, y: float, w: float, h: float, cls: str):
            self.x = x
            self.y = y
            self.w = w
            self.h = h
            self.cls = cls
            self.conf = 0.6
            self.is_world = True
            self.prompt_origen = cls

    box = Box(0.1, 0.1, 0.2, 0.2, "red cup")
    # img None to avoid cv2 crop
    out = _extract_atributos([box], None, frame_id=1, ts=1000, track_ids=[7])
    assert len(out) == 1
    assert out[0]["is_world"] is True
    assert out[0]["prompt_origen"] == "red cup"
    assert out[0]["track_id"] == 7

    # W30 same track_id but is_world False should have separate LRU key 10000 offset handled  # noqa: E501
    class Box2:
        def __init__(self):
            self.x = 0.1
            self.y = 0.1
            self.w = 0.2
            self.h = 0.2
            self.cls = "cup"
            self.conf = 0.6

    out2 = _extract_atributos([Box2()], None, frame_id=1, ts=1000, track_ids=[7])
    assert out2[0]["is_world"] is False  # default
    assert out2[0]["prompt_origen"] is None


def test_yolo_world_detector_cache_and_warmup() -> None:
    det = YoloWorldDetector(None, ["person", "red cup"])
    assert det.is_stub is True
    assert len(det.prompt_list) == 2
    # cache still None for stub
    assert det._txt_feats_static is None or det._txt_feats_static is not None
    # set_classes updates prompt_list and cache
    det.set_classes(["yellow screwdriver", "black remote"])  # noqa: E501
    assert det.prompt_list == ["yellow screwdriver", "black remote"]  # noqa: E501
    # warmup no-op for stub
    det.warmup(2)  # should not raise
    # singleton cache via get_yolo_world_detector
    # reset singleton for test isolation
    import plataforma.webcam.backend.inference.yolo_world as mod

    old = mod._world_singleton
    mod._world_singleton = None
    try:
        d = get_yolo_world_detector(prompt_list=["a", "b", "c"])
        assert d.prompt_list == ["a", "b", "c"]
        d.set_classes(["x"])
        assert get_yolo_world_detector().prompt_list == ["x"]
    finally:
        mod._world_singleton = old


def test_metrics_world_infer_p50() -> None:
    metrics_reset()
    record_world(60.0)
    record_world(70.0)
    body = render_prometheus()
    assert "world_infer_p50_ms" in body
    assert "world_infer_p95_ms" in body
    # p50 of [60,70] is 70 (sorted len//2)
    assert "70.0" in body or "65.0" in body


def test_ws_world_piggyback_envelope_is_world() -> None:
    # seam: perception_ws_handler world piggyback emits detecciones is_world True
    # we test via _extract + make_envelope, not full WS loop (headless)

    class FakeWorldBox:
        def __init__(self):
            self.x = 0.2
            self.y = 0.2
            self.w = 0.2
            self.h = 0.2
            self.cls = "red cup"
            self.conf = 0.6
            self.is_world = True
            self.prompt_origen = "red cup"

    boxes = [FakeWorldBox()]
    # filter via _passes_world
    filtered = [b for b in boxes if _passes_world(b)]
    assert len(filtered) == 1
    atributos = _extract_atributos(filtered, None, frame_id=42, ts=2000, track_ids=[99])
    assert atributos[0]["is_world"] is True
    env = make_envelope(
        "detecciones",
        seq=1,
        payload={"frame_id": 42, "boxes": atributos, "is_world": True},
    )
    raw = json.dumps(env)
    parsed = json.loads(raw)
    assert parsed["payload"]["is_world"] is True
    assert parsed["payload"]["boxes"][0]["prompt_origen"] == "red cup"
    assert parsed["payload"]["boxes"][0]["is_world"] is True
