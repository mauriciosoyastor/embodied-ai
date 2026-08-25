"""YOLO11n ONNX — inferencia CPU S2-A (letterbox 640 + NMS + coords normalizadas).

Runtime real con onnxruntime. Si no hay modelo/sesión, degrada a stub
headless (predict → []) manteniendo compatibilidad con ws.py.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# IMGSZ cableado desde config (Wayfinder 109) — 480 da 28ms vs 49ms sin perder small  # noqa: E501
try:
    from plataforma.webcam.backend.config import YOLO_IMGSZ as _IMG_FROM_CFG
except Exception:
    _IMG_FROM_CFG = 640
IMGSZ: int = int(_IMG_FROM_CFG)
STRIDE: int = 32
PAD_VALUE: int = 114
CONF_DEFAULT: float = 0.5
IOU_DEFAULT: float = 0.7

COCO_NAMES: list[str] = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]

# ---------------------------------------------------------------------------
# Dominio
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Box:
    """Detección con coords normalizadas [0,1] (x,y = esquina sup-izq)."""

    x: float
    y: float
    w: float
    h: float
    cls: str
    conf: float


# ---------------------------------------------------------------------------
# Utilidades puras — testeables sin modelo
# ---------------------------------------------------------------------------


def letterbox(
    img: NDArray[np.uint8],
    size: int = IMGSZ,
    stride: int = STRIDE,
    pad_value: int = PAD_VALUE,
) -> tuple[NDArray[np.uint8], float, tuple[int, int]]:
    """Redimensiona con aspect ratio y padding gris hasta size×size.

    Returns: (padded, ratio, (pad_left, pad_top))
    """
    import cv2

    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nw = round(w * r)
    nh = round(h * r)
    dw = size - nw
    dh = size - nh
    # pad simétrico
    top = dh // 2
    bottom = dh - dh // 2
    left = dw // 2
    right = dw - dw // 2
    _ = stride  # compat firma, no usado para stride-alignment estricto en hito
    scaled = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    padded = cv2.copyMakeBorder(
        scaled,
        top,
        bottom,
        left,
        right,
        cv2.BORDER_CONSTANT,
        value=(pad_value, pad_value, pad_value),
    )
    return padded, r, (left, top)  # type: ignore[return-value]


def non_max_suppression(
    dets: NDArray[np.floating],
    iou_thr: float = IOU_DEFAULT,
) -> list[int]:
    """NMS clásico sobre dets (N,6)=[x1,y1,x2,y2,conf,cls_id].

    Retorna índices a conservar. Input vacío → [].
    """
    if dets.shape[0] == 0:
        return []
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = np.argsort(dets[:, 4])[::-1]
    keep: list[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        union = areas[i] + areas[order[1:]] - inter
        ovr = inter / np.maximum(union, 1e-9)
        order = order[1:][ovr <= iou_thr]
    return keep


def _postprocess(
    raw: NDArray[np.floating],
    ratio: float,
    pad: tuple[int, int],
    orig_w: int,
    orig_h: int,
    conf_thr: float,
    iou_thr: float,
) -> list[Box]:
    """Decodifica salida YOLO (84,8400) o (8400,84) → List[Box] normalizado."""
    # Normalizar shape a (8400,84)
    if raw.ndim == 3:
        # (1,84,8400)
        raw = raw[0]
    if raw.shape[0] == 84 and raw.shape[1] == 8400:
        raw = raw.T  # (8400,84)
    # raw ahora (N,84): 0-3 cx,cy,w,h ; 4-83 scores
    if raw.shape[1] < 6:
        return []
    boxes = raw[:, :4]
    scores = raw[:, 4:]
    cls_ids = np.argmax(scores, axis=1)
    cls_confs = np.max(scores, axis=1)
    keep_mask = cls_confs >= conf_thr
    if not np.any(keep_mask):
        return []
    boxes = boxes[keep_mask]
    cls_ids = cls_ids[keep_mask]
    cls_confs = cls_confs[keep_mask]
    # cx,cy,w,h → x1,y1,x2,y2 en espacio letterbox
    cx, cy, w, h = boxes.T
    px, py = pad
    x1 = (cx - w / 2 - px) / ratio
    y1 = (cy - h / 2 - py) / ratio
    x2 = (cx + w / 2 - px) / ratio
    y2 = (cy + h / 2 - py) / ratio
    # clamp a imagen original antes de normalizar
    x1 = np.clip(x1, 0, orig_w)
    y1 = np.clip(y1, 0, orig_h)
    x2 = np.clip(x2, 0, orig_w)
    y2 = np.clip(y2, 0, orig_h)
    dets = np.stack([x1, y1, x2, y2, cls_confs, cls_ids.astype(float)], axis=1)
    keep_idx = non_max_suppression(dets, iou_thr)
    out: list[Box] = []
    for i in keep_idx:
        d = dets[i]
        bw = float(d[2] - d[0])
        bh = float(d[3] - d[1])
        if bw <= 0 or bh <= 0:
            continue
        nx = float(d[0]) / float(orig_w)
        ny = float(d[1]) / float(orig_h)
        nw = bw / float(orig_w)
        nh = bh / float(orig_h)
        cid = int(d[5])
        label = COCO_NAMES[cid] if 0 <= cid < len(COCO_NAMES) else str(cid)
        conf = float(d[4])
        # clamp normalizado defensivo
        out.append(
            Box(
                x=max(0.0, min(1.0, nx)),
                y=max(0.0, min(1.0, ny)),
                w=max(0.0, min(1.0, nw)),
                h=max(0.0, min(1.0, nh)),
                cls=label,
                conf=max(0.0, min(1.0, conf)),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class YoloDetector:
    """Detector YOLO11n ONNX CPU. Degrada a stub si no hay modelo/ort."""

    def __init__(
        self,
        model_path: pathlib.Path | None = None,
        conf: float = CONF_DEFAULT,
        iou: float = IOU_DEFAULT,
    ) -> None:
        self.model_path = model_path
        self.conf = conf
        self.iou = iou
        self._session: object | None = None
        self.is_stub: bool = True
        if model_path is not None and model_path.exists():
            try:
                import onnxruntime as ort  # type: ignore

                opts = ort.SessionOptions()
                opts.graph_optimization_level = (
                    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                )
                opts.intra_op_num_threads = 2
                opts.inter_op_num_threads = 1
                try:
                    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL  # type: ignore
                except Exception:
                    pass
                self._session = ort.InferenceSession(
                    str(model_path),
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                self.is_stub = False
            except Exception:
                self._session = None
                self.is_stub = True

    def warmup(self, n: int = 10) -> None:
        """Compila grafos ONNX/TensorRT — 10 dummy 1×3×640×640 amortiza cold-start."""
        if self._session is None or self.is_stub:
            return
        try:
            dummy = np.random.randn(1, 3, IMGSZ, IMGSZ).astype(np.float32)
            sess = self._session  # type: ignore
            input_name: str = sess.get_inputs()[0].name  # type: ignore
            for _ in range(max(0, n)):
                sess.run(None, {input_name: dummy})  # type: ignore
        except Exception:
            return

    def predict(
        self,
        image: NDArray[np.uint8] | None = None,
        conf_thr: float | None = None,
    ) -> list[Box]:
        """Infiere boxes normalizadas. Sin imagen o sin sesión → [] stub."""
        if image is None:
            return []
        if self._session is None:
            return []
        thr = conf_thr if conf_thr is not None else self.conf
        try:
            import cv2
        except Exception:
            return []
        if image.ndim != 3 or image.shape[2] != 3:
            return []
        orig_h, orig_w = image.shape[:2]
        if orig_h == 0 or orig_w == 0:
            return []
        padded, ratio, pad = letterbox(image, size=IMGSZ)
        # BGR→RGB, /255, CHW, batch
        _ = cv2  # uso explícito para ruff
        rgb = padded[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(rgb, (2, 0, 1))[None]
        blob = np.ascontiguousarray(blob, dtype=np.float32)
        try:
            sess = self._session
            # need to satisfy mypy — session is InferenceSession-like
            input_name: str = sess.get_inputs()[0].name  # type: ignore
            raw_out = sess.run(None, {input_name: blob})[0]  # type: ignore
            raw_arr = np.asarray(raw_out)
            return _postprocess(raw_arr, ratio, pad, orig_w, orig_h, thr, self.iou)
        except Exception:
            return []


def get_yolo_detector(
    models_dir: pathlib.Path | None = None,
) -> YoloDetector:
    """Factory lazy — stub si models ausentes."""
    if models_dir is None:
        models_dir = pathlib.Path(__file__).parent.parent / "models"
    candidate = models_dir / "yolo11n.onnx"
    if candidate.exists():
        return YoloDetector(candidate)
    return YoloDetector(None)
