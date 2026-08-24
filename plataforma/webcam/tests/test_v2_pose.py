"""Tests v2 pose — headless con frames sintéticos (letterbox, NMS, stub, mock).

Sin modelo ONNX ni cámara — valida pre/post-proceso y compat headless.
"""

from __future__ import annotations

import pathlib
from typing import Any

import numpy as np

from plataforma.webcam.backend.config import POSE_CONF, POSE_ENABLED
from plataforma.webcam.backend.inference.pose import (
    Keypoint,
    Pose,
    PoseDetector,
    _postprocess_pose,
    get_pose_detector,
)


def _fake_frame(h: int = 480, w: int = 640) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, size=(h, w, 3), dtype=np.uint8)


def test_pose_config_valores() -> None:
    assert isinstance(POSE_CONF, float)
    assert 0.0 < POSE_CONF <= 1.0
    assert isinstance(POSE_ENABLED, bool)
    assert POSE_ENABLED is True


def test_pose_detector_stub_sin_imagen() -> None:
    det = PoseDetector(None)
    assert det.is_stub is True
    assert det.predict(None) == []
    assert det.predict(_fake_frame()) == []


def test_get_pose_detector_stub_headless() -> None:
    det = get_pose_detector(models_dir=pathlib.Path("/tmp/inexistente_xyz_pose"))
    assert det.is_stub is True
    assert det.predict(_fake_frame()) == []


def test_pose_keypoint_rango() -> None:
    kp = Keypoint(x=0.5, y=0.5, conf=0.9)
    assert 0.0 <= kp.x <= 1.0
    assert 0.0 <= kp.y <= 1.0
    assert 0.0 <= kp.conf <= 1.0


def test_pose_box_normalizado_rango() -> None:
    kps = tuple(Keypoint(x=0.5, y=0.5, conf=0.9) for _ in range(17))
    p = Pose(x=0.1, y=0.2, w=0.3, h=0.4, conf=0.9, keypoints=kps)
    for v in (p.x, p.y, p.w, p.h, p.conf):
        assert 0.0 <= v <= 1.0
    assert len(p.keypoints) == 17


def test_pose_postprocess_sintetico_via_stub_inyectado() -> None:
    """Valida _postprocess_pose con salida sintética pose (56,8400)."""
    raw = np.zeros((1, 56, 8400), dtype=np.float32)
    # detección 0: cx=320,cy=320,w=100,h=100, conf=0.9
    raw[0, 0, 0] = 320.0
    raw[0, 1, 0] = 320.0
    raw[0, 2, 0] = 100.0
    raw[0, 3, 0] = 100.0
    raw[0, 4, 0] = 0.9
    # keypoints 17*3 =51 valores desde índice 5; poner 2 con coords centrales
    for k in range(17):
        raw[0, 5 + k * 3, 0] = 320.0
        raw[0, 5 + k * 3 + 1, 0] = 320.0
        raw[0, 5 + k * 3 + 2, 0] = 0.95
    poses = _postprocess_pose(
        raw, ratio=1.0, pad=(0, 0), orig_w=640, orig_h=640, conf_thr=0.5, iou_thr=0.7
    )
    assert len(poses) == 1
    p = poses[0]
    assert 0.0 <= p.x <= 1.0 and 0.0 <= p.y <= 1.0
    assert p.conf == 0.9 or abs(p.conf - 0.9) < 1e-5
    assert len(p.keypoints) == 17
    for kp in p.keypoints:
        assert 0.0 <= kp.x <= 1.0
        assert 0.0 <= kp.y <= 1.0


def test_pose_postprocess_filtra_conf_baja() -> None:
    raw = np.zeros((1, 56, 8400), dtype=np.float32)
    raw[0, 0, 0] = 320.0
    raw[0, 1, 0] = 320.0
    raw[0, 2, 0] = 100.0
    raw[0, 3, 0] = 100.0
    raw[0, 4, 0] = 0.2  # bajo umbral
    poses = _postprocess_pose(
        raw, ratio=1.0, pad=(0, 0), orig_w=640, orig_h=640, conf_thr=0.5, iou_thr=0.7
    )
    assert poses == []


def test_pose_predict_con_sesion_mock() -> None:
    """Inyecta sesión mock para ejercitar predict end-to-end sin archivo onnx."""

    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInput()]

        def run(self, _a: Any, _b: Any) -> list[Any]:
            raw = np.zeros((1, 56, 8400), dtype=np.float32)
            raw[0, 0, 0] = 320.0
            raw[0, 1, 0] = 320.0
            raw[0, 2, 0] = 200.0
            raw[0, 3, 0] = 200.0
            raw[0, 4, 0] = 0.88
            for k in range(17):
                raw[0, 5 + k * 3, 0] = 320.0
                raw[0, 5 + k * 3 + 1, 0] = 320.0
                raw[0, 5 + k * 3 + 2, 0] = 0.9
            return [raw]

    det = PoseDetector(None)
    det._session = MockSession()
    det.is_stub = False
    frame = _fake_frame(480, 640)
    poses = det.predict(frame, conf_thr=0.5)
    assert len(poses) == 1
    p = poses[0]
    assert isinstance(p, Pose)
    assert 0.0 <= p.x <= 1.0
    assert 0.0 <= p.w <= 1.0
    assert 0.0 <= p.conf <= 1.0
    assert len(p.keypoints) == 17


def test_pose_predict_nms_headless_mock_solapados() -> None:
    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self) -> list[Any]:
            return [MockInput()]

        def run(self, _a: Any, _b: Any) -> list[Any]:
            raw = np.zeros((1, 56, 8400), dtype=np.float32)
            for i, conf in enumerate([0.9, 0.85]):
                raw[0, 0, i] = 320.0
                raw[0, 1, i] = 320.0
                raw[0, 2, i] = 100.0
                raw[0, 3, i] = 100.0
                raw[0, 4, i] = float(conf)
                for k in range(17):
                    raw[0, 5 + k * 3, i] = 320.0
                    raw[0, 5 + k * 3 + 1, i] = 320.0
                    raw[0, 5 + k * 3 + 2, i] = 0.9
            return [raw]

    det = PoseDetector(None)
    det._session = MockSession()
    det.is_stub = False
    poses = det.predict(_fake_frame(640, 640), conf_thr=0.5)
    assert len(poses) == 1
    assert abs(poses[0].conf - 0.9) < 1e-5


def test_pose_predict_rechaza_frame_invalido() -> None:
    det = PoseDetector(None)
    bad = np.zeros((640, 640), dtype=np.uint8)
    det._session = object()
    det.is_stub = False
    assert det.predict(bad) == []


def test_pose_export_via_inference_init() -> None:
    import plataforma.webcam.backend.inference as inf

    assert hasattr(inf, "PoseDetector")
    assert hasattr(inf, "get_pose_detector")
    assert hasattr(inf, "Pose")
    assert hasattr(inf, "Keypoint")
