"""Interfaz pública de inferencia — S2-A (real) desacoplada de FSM + pose v2."""

from __future__ import annotations

from plataforma.webcam.backend.inference.gesture import (
    ALLOWED_LABELS,
    GestoReconocido,
    GestureLabel,
    GestureRecognizer,
    classify_gesture,
    get_gesture_recognizer,
)
from plataforma.webcam.backend.inference.pose import (
    Keypoint,
    Pose,
    PoseDetector,
    _postprocess_pose,
    get_pose_detector,
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
    "GestureLabel",
    "GestoReconocido",
    "GestureRecognizer",
    "Keypoint",
    "Pose",
    "PoseDetector",
    "YoloDetector",
    "_postprocess_pose",
    "classify_gesture",
    "get_gesture_recognizer",
    "get_pose_detector",
    "get_yolo_detector",
    "letterbox",
    "non_max_suppression",
]
