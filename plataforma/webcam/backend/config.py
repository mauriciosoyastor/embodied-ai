"""Configuración del módulo webcam — umbrales S2-A/B + pose v2."""

from __future__ import annotations

YOLO_CONF: float = 0.5
GESTURE_CONF: float = 0.7
POSE_CONF: float = 0.5
POSE_ENABLED: bool = True
YOLO_MAX_HZ: int = 10
GESTURE_MAX_HZ: int = 30
LEAKY_QUEUE_SIZE: int = 1
WS_BUFFERED_AMOUNT_LIMIT: int = 64 * 1024  # 64KB
JPEG_QUALITY: int = 75
MAX_FRAME_SIZE: int = 640
