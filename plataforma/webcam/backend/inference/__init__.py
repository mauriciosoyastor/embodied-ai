"""Interfaz pública de inferencia — S2-A (real) desacoplada de FSM + depth MiDaS."""

from __future__ import annotations

from plataforma.webcam.backend.inference.depth import (
    BoxCenter,
    DepthEstimator,
    Profundidad,
    get_depth_estimator,
)
from plataforma.webcam.backend.inference.gesture import (
    ALLOWED_LABELS,
    GestoReconocido,
    GestureLabel,
    GestureRecognizer,
    classify_gesture,
    get_gesture_recognizer,
)
from plataforma.webcam.backend.inference.yolo import (
    Box,
    YoloDetector,
    get_yolo_detector,
    letterbox,
    non_max_suppression,
)

__all__ = [
    "ALLOWED_LABELS",
    "Box",
    "BoxCenter",
    "DepthEstimator",
    "GestureLabel",
    "GestoReconocido",
    "GestureRecognizer",
    "Profundidad",
    "YoloDetector",
    "classify_gesture",
    "get_depth_estimator",
    "get_gesture_recognizer",
    "get_yolo_detector",
    "letterbox",
    "non_max_suppression",
]
