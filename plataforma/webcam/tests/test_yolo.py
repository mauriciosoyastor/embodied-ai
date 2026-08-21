"""Tests S2-A YOLO — headless con frames sintéticos (letterbox, NMS, stub).

Sin modelo ONNX ni cámara — valida pre/post-proceso puros y compat Box/ws.
"""

from __future__ import annotations

import pathlib
from types import SimpleNamespace
from typing import Any

import numpy as np

from plataforma.webcam.backend.inference.yolo import (
    Box,
    YoloDetector,
    _postprocess,
    get_yolo_detector,
    letterbox,
    non_max_suppression,
)


def _fake_frame(h: int = 480, w: int = 640) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, size=(h, w, 3), dtype=np.uint8)


def test_letterbox_produce_640_y_ratio() -> None:
    img = _fake_frame(480, 640)
    padded, ratio, pad = letterbox(img, size=640)
    assert padded.shape[0] == 640
    assert padded.shape[1] == 640
    assert padded.shape[2] == 3
    assert 0 < ratio <= 1.0
    assert isinstance(pad, tuple) and len(pad) == 2


def test_letterbox_vertical_frame_padding() -> None:
    img = _fake_frame(720, 1280)  # 16:9
    padded, ratio, _pad = letterbox(img, size=640)
    assert padded.shape == (640, 640, 3)
    assert ratio == min(640 / 720, 640 / 1280)


def test_letterbox_small_frame_upscale() -> None:
    img = _fake_frame(100, 100)
    padded, ratio, _pad = letterbox(img, size=640)
    assert padded.shape == (640, 640, 3)
    assert ratio == 6.4


def test_nms_vacio() -> None:
    dets = np.zeros((0, 6), dtype=np.float32)
    assert non_max_suppression(dets, iou_thr=0.7) == []


def test_nms_unico() -> None:
    dets = np.array([[10, 10, 50, 50, 0.9, 0.0]], dtype=np.float32)
    assert non_max_suppression(dets) == [0]


def test_nms_filtra_solapados() -> None:
    dets = np.array(
        [
            [10, 10, 50, 50, 0.9, 0.0],
            [12, 12, 52, 52, 0.8, 0.0],  # overlap alta → suprimido
            [100, 100, 150, 150, 0.85, 0.0],  # separado → conserva
        ],
        dtype=np.float32,
    )
    keep = non_max_suppression(dets, iou_thr=0.7)
    assert 0 in keep
    assert 2 in keep
    # el segundo tiene IoU >0.7 con el primero → fuera
    assert 1 not in keep


def test_nms_no_suprime_si_iou_bajo() -> None:
    dets = np.array(
        [
            [0, 0, 10, 10, 0.9, 0.0],
            [20, 20, 30, 30, 0.8, 0.0],
        ],
        dtype=np.float32,
    )
    keep = non_max_suppression(dets, iou_thr=0.7)
    assert set(keep) == {0, 1}


def test_box_normalizado_rango() -> None:
    b = Box(x=0.1, y=0.2, w=0.3, h=0.4, cls="person", conf=0.9)
    for v in (b.x, b.y, b.w, b.h, b.conf):
        assert 0.0 <= v <= 1.0
    assert isinstance(b.cls, str)


def test_yolo_detector_stub_sin_imagen() -> None:
    det = YoloDetector(None)
    assert det.is_stub is True
    assert det.predict(None) == []
    # con frame sintético pero sin sesión → []
    assert det.predict(_fake_frame()) == []


def test_get_yolo_detector_stub_headless() -> None:
    det = get_yolo_detector(models_dir=pathlib.Path("/tmp/inexistente_xyz"))
    assert det.is_stub is True
    assert det.predict(_fake_frame()) == []


def test_yolo_postprocess_sintetico_via_stub_inyectado() -> None:
    """Valida _postprocess con salida YOLO sintética (sin onnxruntime)."""
    # Simular 2 detecciones: una conf alta clase 0 (person), otra baja filtrada
    # raw shape (1,84,8400) — solo 2 filas con señal
    raw = np.zeros((1, 84, 8400), dtype=np.float32)
    # detección 0: cx=320,cy=320,w=100,h=100, score clase 0 =0.9
    raw[0, 0, 0] = 320.0
    raw[0, 1, 0] = 320.0
    raw[0, 2, 0] = 100.0
    raw[0, 3, 0] = 100.0
    raw[0, 4, 0] = 0.9  # person
    # detección 1: misma zona pero clase 1 score 0.2 (bajo umbral)
    raw[0, 0, 1] = 330.0
    raw[0, 1, 1] = 330.0
    raw[0, 2, 1] = 100.0
    raw[0, 3, 1] = 100.0
    raw[0, 5, 1] = 0.2  # bicycle pero conf baja
    boxes = _postprocess(
        raw, ratio=1.0, pad=(0, 0), orig_w=640, orig_h=640, conf_thr=0.5, iou_thr=0.7
    )
    assert len(boxes) == 1
    b = boxes[0]
    assert b.cls == "person"
    assert 0.0 <= b.x <= 1.0 and 0.0 <= b.y <= 1.0
    assert b.conf == 0.9 or abs(b.conf - 0.9) < 1e-5


def test_yolo_predict_con_sesion_mock() -> None:
    """Inyecta sesión mock para ejercitar predict end-to-end sin archivo onnx."""

    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInput()]

        def run(self, _a: Any, _b: Any) -> list[Any]:
            raw = np.zeros((1, 84, 8400), dtype=np.float32)
            # una detección centrada
            raw[0, 0, 0] = 320.0
            raw[0, 1, 0] = 320.0
            raw[0, 2, 0] = 200.0
            raw[0, 3, 0] = 200.0
            raw[0, 4, 0] = 0.88
            return [raw]

    det = YoloDetector(None)
    det._session = MockSession()
    det.is_stub = False
    frame = _fake_frame(480, 640)
    boxes = det.predict(frame, conf_thr=0.5)
    assert len(boxes) == 1
    b = boxes[0]
    assert isinstance(b, Box)
    assert b.cls == "person"
    assert 0.0 <= b.x <= 1.0
    assert 0.0 <= b.w <= 1.0
    assert 0.0 <= b.conf <= 1.0


def test_yolo_predict_nms_headless_mock_solapados() -> None:
    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInput()]

        def run(self, _a: Any, _b: Any) -> list[Any]:
            raw = np.zeros((1, 84, 8400), dtype=np.float32)
            # dos detecciones casi idénticas con clase 0
            for i, conf in enumerate([0.9, 0.85]):
                raw[0, 0, i] = 320.0
                raw[0, 1, i] = 320.0
                raw[0, 2, i] = 100.0
                raw[0, 3, i] = 100.0
                raw[0, 4, i] = float(conf)
            return [raw]

    det = YoloDetector(None)
    det._session = MockSession()
    det.is_stub = False
    boxes = det.predict(_fake_frame(640, 640), conf_thr=0.5)
    # NMS debe dejar solo 1
    assert len(boxes) == 1
    assert abs(boxes[0].conf - 0.9) < 1e-5


def test_yolo_infer_ws_boxes_normalizadas_via_mock() -> None:
    """Compat ws.py: boxes normalizadas tras predict mock deben pasar clamp [0,1]."""

    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInput()]

        def run(self, _a: Any, _b: Any) -> list[Any]:
            raw = np.zeros((1, 84, 8400), dtype=np.float32)
            raw[0, 0, 0] = 320.0
            raw[0, 1, 0] = 320.0
            raw[0, 2, 0] = 640.0
            raw[0, 3, 0] = 480.0
            raw[0, 4, 0] = 0.95
            return [raw]

    # Monkeypatch get_yolo_detector para retornar mock con sesión
    import plataforma.webcam.backend.inference.yolo as yolo_mod

    orig = yolo_mod.get_yolo_detector

    def _mock_get(models_dir: pathlib.Path | None = None) -> YoloDetector:
        _ = models_dir
        d = YoloDetector(None)
        d._session = MockSession()
        d.is_stub = False
        return d

    yolo_mod.get_yolo_detector = _mock_get
    try:
        # ws.run_inference usa get_yolo_detector lazy
        import plataforma.webcam.backend.ws as ws_mod

        dummy = (
            "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
            "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgy"
            "IRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
            "MjL/wAARCAAEAAQADASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAU"
            "EAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQE"
            "AAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
        )
        boxes, gesto = ws_mod.run_inference(
            jpeg_b64=dummy,
            frame_id=1,
            ts=1700000000000,
        )
        assert isinstance(boxes, list)
        assert gesto["frame_id"] == 1
        # boxes del ws ya están clamp [0,1] si existen
        for b in boxes:
            assert 0.0 <= b["x"] <= 1.0
    finally:
        yolo_mod.get_yolo_detector = orig
        # sanity: helper creado con SimpleNamespace cumple Box
        _ = SimpleNamespace(x=0)


def test_yolo_predict_rechaza_frame_invalido() -> None:
    det = YoloDetector(None)
    # array gris sin canales
    bad = np.zeros((640, 640), dtype=np.uint8)
    det._session = object()
    det.is_stub = False
    # aunque haya sesión, imagen inválida → []
    assert det.predict(bad) == []
