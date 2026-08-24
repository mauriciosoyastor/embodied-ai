"""Configuración del módulo webcam — umbrales S2-A/B + v2 whitelist + VLM."""

from __future__ import annotations

YOLO_CONF: float = 0.5
YOLO_AREA_MIN: float = 0.03
YOLO_PERSON_CONF: float = 0.60
YOLO_PERSON_AREA_MIN: float = 0.15
GESTURE_CONF: float = 0.7
POSE_CONF: float = 0.5
POSE_ENABLED: bool = True
DEPTH_CONF: float = 0.5
DEPTH_ENABLED: bool = True
VLM_ENABLED: bool = True
VLM_INTERVAL: int = 30
YOLO_MAX_HZ: int = 10
GESTURE_MAX_HZ: int = 30
LEAKY_QUEUE_SIZE: int = 1
WS_BUFFERED_AMOUNT_LIMIT: int = 64 * 1024  # 64KB
JPEG_QUALITY: int = 75
MAX_FRAME_SIZE: int = 640

YOLO_WHITELIST: frozenset[str] = frozenset(
    {
        "person",
        "chair",
        "couch",
        "bottle",
        "cup",
        "cell phone",
        "laptop",
        "keyboard",
        "mouse",
        "book",
        "backpack",
        "handbag",
        "remote",
    }
)
