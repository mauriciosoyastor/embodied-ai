"""Configuraci├│n del m├│dulo webcam ÔÇö umbrales S2-A/B + v2 whitelist + VLM."""

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
# S2-A scaffold — MOT + LRU (mapa #88 G1/G2)
TRACK_MAX_AGE: int = 30
TRACK_IOU_THRESHOLD: float = 0.5
LRU_SIZE: int = 64
LRU_TTL_MS: int = 2000
# OTel / ThreadPinning S2
OTEL_ENABLED: bool = True
ONNX_INTRA_OP: int = 2
ONNX_INTER_OP: int = 1
# Wayfinder 109 — IMGSZ cableado revert a 640 (480 inestable real)  # noqa: E501
YOLO_IMGSZ: int = 640
# S3 — PromptList W30 / World-s (mapa #88 G1/G2) — 008 Destination: True jarvis 51MB  # noqa: E501
YOLO_WORLD_ENABLED: bool = True
YOLO_WORLD_DYNAMIC_BY_VOZ: bool = True
YOLO_WORLD_PROMPTLIST_STATIC: list[str] = [
    "person",
    "chair",
    "couch",
    "dining table",
    "bed",
    "toilet",
    "tv",
    "laptop",
    "keyboard",
    "mouse",
    "cell phone",
    "remote",
    "bottle",
    "cup",
    "wine glass",
    "bowl",
    "book",
    "backpack",
    "handbag",
    "potted plant",
]

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
        # W30 curada indoor (R2 + mapa #88 G1) — mismo yolo11n.onnx sin coste
        "tv",
        "bed",
        "dining table",
        "toilet",
        "potted plant",
        "microwave",
        "oven",
        "sink",
        "refrigerator",
        "clock",
        "vase",
        "toaster",
        "wine glass",
        "bowl",
        "scissors",
        "teddy bear",
        "toothbrush",
    }
)
