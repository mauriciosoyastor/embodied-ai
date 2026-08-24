"""Interfaz pública de inferencia — S2-A + v2 pose/depth/VLM."""

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
from plataforma.webcam.backend.inference.pose import (
    Keypoint,
    Pose,
    PoseDetector,
    _postprocess_pose,
    get_pose_detector,
)
from plataforma.webcam.backend.inference.vlm import (
    LeyendaEscena,
    VLMClient,
    get_vlm_client,
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
    "Keypoint",
    "LeyendaEscena",
    "Pose",
    "PoseDetector",
    "Profundidad",
    "VLMClient",
    "YoloDetector",
    "_postprocess_pose",
    "classify_gesture",
    "get_depth_estimator",
    "get_gesture_recognizer",
    "get_pose_detector",
    "get_vlm_client",
    "get_yolo_detector",
    "letterbox",
    "non_max_suppression",
]
