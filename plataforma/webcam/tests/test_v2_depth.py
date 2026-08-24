"""Tests v2 depth MiDaS small 256 — headless con frames sintéticos.

Sin modelo ONNX ni cámara — valida stub, estructura Profundidad y median 3x3.
"""

from __future__ import annotations

import pathlib
from typing import Any

import numpy as np

from plataforma.webcam.backend.config import DEPTH_CONF, DEPTH_ENABLED
from plataforma.webcam.backend.inference.depth import (
    BoxCenter,
    DepthEstimator,
    Profundidad,
    _normalize_depth,
    _sample_z_rel_median,
    get_depth_estimator,
)


def _fake_frame(h: int = 480, w: int = 640) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, size=(h, w, 3), dtype=np.uint8)


def _fake_boxes(n: int = 2) -> list[dict[str, Any]]:
    boxes: list[dict[str, Any]] = []
    for i in range(n):
        x = 0.1 + i * 0.3
        y = 0.2 + i * 0.1
        boxes.append(
            {
                "x": float(x),
                "y": float(y),
                "w": 0.2,
                "h": 0.3,
                "cls": "person",
                "conf": 0.9,
            }
        )
    return boxes


def test_depth_config_valores() -> None:
    assert isinstance(DEPTH_CONF, float)
    assert 0.0 < DEPTH_CONF <= 1.0
    assert isinstance(DEPTH_ENABLED, bool)
    assert DEPTH_ENABLED is True


def test_depth_estimator_stub_sin_imagen() -> None:
    est = DepthEstimator(None)
    assert est.is_stub is True
    assert est.estimate(None, _fake_boxes()) == []
    assert est.estimate(_fake_frame(), _fake_boxes()) == []
    # boxes vacías también stub
    assert est.estimate(_fake_frame(), []) == []
    assert est.estimate(_fake_frame(), None) == []  # type: ignore[arg-type]


def test_get_depth_estimator_stub_headless() -> None:
    est = get_depth_estimator(models_dir=pathlib.Path("/tmp/inexistente_xyz_depth"))
    assert est.is_stub is True
    assert est.estimate(_fake_frame(), _fake_boxes()) == []


def test_profundidad_estructura_rango() -> None:
    bc = BoxCenter(x=0.5, y=0.5)
    p = Profundidad(frame_id=7, box_center=bc, z_rel=0.42, z_m=None)
    assert 0.0 <= p.box_center.x <= 1.0
    assert 0.0 <= p.box_center.y <= 1.0
    assert 0.0 <= p.z_rel <= 1.0
    assert p.z_m is None
    assert p.frame_id == 7


def test_normalize_depth_clamp() -> None:
    raw = np.array([[0.0, 5.0, 10.0]], dtype=np.float32)
    norm = _normalize_depth(raw)
    assert norm.shape == raw.shape
    assert float(np.min(norm)) == 0.0
    assert float(np.max(norm)) == 1.0
    # todos iguales → zeros
    raw2 = np.full((2, 2), 3.0, dtype=np.float32)
    norm2 = _normalize_depth(raw2)
    assert np.all(norm2 == 0.0)


def test_sample_z_rel_median_centro() -> None:
    # depth 256x256 con gradiente: valor = x/255
    depth = np.tile(np.linspace(0, 1, 256, dtype=np.float32), (256, 1))
    # centro 0.5,0.5 → dx~127 → median ~0.5
    z = _sample_z_rel_median(depth, 0.5, 0.5)
    assert 0.0 <= z <= 1.0
    assert abs(z - 0.5) < 0.02
    # esquina 0,0
    z0 = _sample_z_rel_median(depth, 0.0, 0.0)
    assert 0.0 <= z0 <= 0.05
    # esquina 1,1
    z1 = _sample_z_rel_median(depth, 1.0, 1.0)
    assert 0.95 <= z1 <= 1.0


def test_depth_estimate_via_mock_session_boxes_dict() -> None:
    """Inyecta sesión mock para ejercitar estimate end-to-end sin archivo onnx."""

    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInput()]

        def run(self, _a: Any, _b: Any) -> list[Any]:
            # depth raw 256x256 gradiente horizontal 0..10
            depth = np.tile(np.linspace(0, 10, 256, dtype=np.float32), (256, 1))
            raw = depth[None, None, :, :]  # [1,1,256,256]
            return [raw]

    est = DepthEstimator(None)
    est._session = MockSession()
    est.is_stub = False
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    boxes = [{"x": 0.4, "y": 0.4, "w": 0.2, "h": 0.2}]
    out = est.estimate(frame, boxes, frame_id=42)
    assert len(out) == 1
    p = out[0]
    assert isinstance(p, Profundidad)
    assert p.frame_id == 42
    assert 0.0 <= p.z_rel <= 1.0
    assert p.z_m is None
    assert 0.0 <= p.box_center.x <= 1.0
    assert 0.0 <= p.box_center.y <= 1.0
    # centro ~0.5 → z_rel ~0.5
    assert abs(p.z_rel - 0.5) < 0.05


def test_depth_estimate_multiple_boxes_median() -> None:
    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInput()]

        def run(self, _a: Any, _b: Any) -> list[Any]:
            # depth constante por filas: vertical gradiente 0..1
            col = np.linspace(0, 1, 256, dtype=np.float32)[:, None]
            depth = np.tile(col, (1, 256))
            raw = depth[None, None, :, :]
            return [raw]

    est = DepthEstimator(None)
    est._session = MockSession()
    est.is_stub = False
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    boxes = [
        {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2},  # centro y~0.2 → z bajo
        {"x": 0.6, "y": 0.6, "w": 0.2, "h": 0.2},  # centro y~0.7 → z alto
    ]
    out = est.estimate(frame, boxes, frame_id=1)
    assert len(out) == 2
    assert out[0].z_rel < out[1].z_rel
    for p in out:
        assert 0.0 <= p.z_rel <= 1.0
        assert p.z_m is None


def test_depth_estimate_rechaza_frame_invalido() -> None:
    est = DepthEstimator(None)

    class MockInputInner:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInputInner()]

        def run(self, *_: Any) -> list[Any]:
            raise AssertionError("no debería llamarse")

    est._session = MockSession()  # type: ignore[assignment]
    est.is_stub = False
    bad = np.zeros((640, 640), dtype=np.uint8)  # 2D sin canal
    assert est.estimate(bad, _fake_boxes()) == []
    assert est.estimate(None, _fake_boxes()) == []


def test_depth_estimate_boxes_box_objects() -> None:
    """Soporta Box-like objects con attrs x,y,w,h."""

    class MockBox:
        def __init__(self, x: float, y: float, w: float, h: float) -> None:
            self.x = x
            self.y = y
            self.w = w
            self.h = h

    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInput()]

        def run(self, _a: Any, _b: Any) -> list[Any]:
            depth = np.zeros((256, 256), dtype=np.float32)
            depth[100:156, 100:156] = 10.0
            raw = depth[None, None, :, :]
            return [raw]

    est = DepthEstimator(None)
    est._session = MockSession()
    est.is_stub = False
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    boxes = [MockBox(0.4, 0.4, 0.2, 0.2)]
    out = est.estimate(frame, boxes, frame_id=9)
    assert len(out) == 1
    assert 0.0 <= out[0].z_rel <= 1.0


def test_depth_export_via_inference_init() -> None:
    import plataforma.webcam.backend.inference as inf

    assert hasattr(inf, "DepthEstimator")
    assert hasattr(inf, "get_depth_estimator")
    assert hasattr(inf, "Profundidad")
    assert hasattr(inf, "BoxCenter")


def test_descargar_modelos_depth_url_y_arg() -> None:
    from plataforma.webcam.backend.descargar_modelos import DEPTH_URL, parse_args

    assert isinstance(DEPTH_URL, str)
    assert DEPTH_URL.startswith("https://")
    assert "midas" in DEPTH_URL.lower() or "depth" in DEPTH_URL.lower()
    args = parse_args(["--depth-url", "https://example.com/custom.onnx"])
    assert args.depth_url == "https://example.com/custom.onnx"
    args2 = parse_args([])
    assert args2.depth_url == DEPTH_URL
