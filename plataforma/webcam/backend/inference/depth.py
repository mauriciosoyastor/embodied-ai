"""Profundidad MiDaS small 256 — inferencia CPU 5Hz piggyback.

Runtime con onnxruntime lazy 1.29, intra_op=2 inter_op=1. Si modelo ausente
o image None, degrada a stub headless (estimate → []) manteniendo compat.

Modelo: models/midas_small_256.onnx (256x256, normalize /255)
Salida: Profundidad {frame_id, box_center:{x,y}, z_rel median 3x3 ∈[0,1], z_m:null}
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEPTH_INPUT_SIZE: int = 256
DEPTH_CONF_DEFAULT: float = 0.5


# ---------------------------------------------------------------------------
# Dominio
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoxCenter:
    """Centro bbox normalizado [0,1]."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Profundidad:
    """Profundidad relativa por bbox — z_rel ∈[0,1], z_m siempre null en v2."""

    frame_id: int
    box_center: BoxCenter
    z_rel: float
    z_m: float | None = None


# ---------------------------------------------------------------------------
# Helpers puros — testeables sin modelo
# ---------------------------------------------------------------------------


def _normalize_depth(depth: NDArray[np.floating]) -> NDArray[np.floating]:
    """Normaliza depth raw [H,W] → [0,1] per-frame (min-max)."""
    d = np.asarray(depth, dtype=np.float32)
    d_min = float(np.min(d))
    d_max = float(np.max(d))
    denom = d_max - d_min
    if denom < 1e-6:
        return np.zeros_like(d, dtype=np.float32)
    norm = (d - d_min) / (denom + 1e-9)
    return np.clip(norm, 0.0, 1.0).astype(np.float32)


def _sample_z_rel_median(
    depth_norm: NDArray[np.floating],
    cx_norm: float,
    cy_norm: float,
) -> float:
    """Median 3x3 en centro bbox mapeado a depth 256x256."""
    h, w = depth_norm.shape[:2]
    # clamp normalizado
    cx_norm = max(0.0, min(1.0, cx_norm))
    cy_norm = max(0.0, min(1.0, cy_norm))
    dx = int(round(cx_norm * (w - 1)))
    dy = int(round(cy_norm * (h - 1)))
    # ventana 3x3 clampeada
    x0 = max(0, dx - 1)
    x1 = min(w, dx + 2)
    y0 = max(0, dy - 1)
    y1 = min(h, dy + 2)
    patch = depth_norm[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0
    median = float(np.median(patch))
    return max(0.0, min(1.0, median))


def _boxes_to_centers(
    boxes: list[Any] | None,
) -> list[tuple[float, float]]:
    """Extrae centros normalizados (cx,cy) de boxes heterogéneos."""
    if not boxes:
        return []
    centers: list[tuple[float, float]] = []
    for b in boxes:
        try:
            if isinstance(b, dict):
                x = float(b.get("x", 0.0))
                y = float(b.get("y", 0.0))
                w = float(b.get("w", 0.0))
                h = float(b.get("h", 0.0))
                cx = x + w / 2.0
                cy = y + h / 2.0
            elif isinstance(b, (list, tuple)) and len(b) >= 4:
                x, y, w, h = float(b[0]), float(b[1]), float(b[2]), float(b[3])
                cx = x + w / 2.0
                cy = y + h / 2.0
            else:
                # objeto con attrs x,y,w,h (Box-like)
                x = float(getattr(b, "x", 0.0))
                y = float(getattr(b, "y", 0.0))
                w = float(getattr(b, "w", 0.0))
                h = float(getattr(b, "h", 0.0))
                cx = x + w / 2.0
                cy = y + h / 2.0
            centers.append((max(0.0, min(1.0, cx)), max(0.0, min(1.0, cy))))
        except Exception:
            continue
    return centers


# ---------------------------------------------------------------------------
# Estimador
# ---------------------------------------------------------------------------


class DepthEstimator:
    """Estimador MiDaS small 256 ONNX CPU. Stub si no hay modelo."""

    def __init__(
        self,
        model_path: pathlib.Path | None = None,
        conf: float = DEPTH_CONF_DEFAULT,
    ) -> None:
        self.model_path = model_path
        self.conf = conf
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
                # ORT_SEQUENTIAL minimiza jitter con 5Hz piggyback
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

    def estimate(
        self,
        image: NDArray[np.uint8] | None,
        boxes: list[Any] | None = None,
        frame_id: int = 0,
    ) -> list[Profundidad]:
        """Estima profundidad relativa por bbox. Stub → [].

        Args:
            image: BGR uint8 [H,W,3] o None.
            boxes: lista de bbox normalizados [0,1] {x,y,w,h} o Box objects.
            frame_id: correlación con frame Envelope.

        Returns:
            Lista Profundidad por cada box (mismo orden), z_rel ∈[0,1], z_m=None.
        """
        if image is None:
            return []
        if boxes is None or len(boxes) == 0:
            return []
        if self._session is None:
            return []
        if image.ndim != 3 or image.shape[2] != 3:
            return []
        if image.shape[0] == 0 or image.shape[1] == 0:
            return []
        try:
            import cv2
        except Exception:
            return []

        centers = _boxes_to_centers(boxes)
        if not centers:
            return []

        # preprocess 256x256 normalize /255 CHW
        try:
            resized = cv2.resize(
                image,
                (DEPTH_INPUT_SIZE, DEPTH_INPUT_SIZE),
                interpolation=cv2.INTER_LINEAR,
            )
            _ = cv2  # ruff
            rgb = resized[:, :, ::-1].astype(np.float32) / 255.0
            blob = np.transpose(rgb, (2, 0, 1))[None]
            blob = np.ascontiguousarray(blob, dtype=np.float32)
        except Exception:
            return []

        try:
            sess = self._session
            input_name: str = sess.get_inputs()[0].name  # type: ignore
            raw_out = sess.run(None, {input_name: blob})[0]  # type: ignore
            arr = np.asarray(raw_out)
            # normalizar a [256,256] — soporta [1,1,256,256] o [1,256,256] o [256,256]
            if arr.ndim == 4:
                # [1,1,256,256]
                depth = arr[0, 0]
            elif arr.ndim == 3:
                # [1,256,256] o [1,1,256] edge
                if arr.shape[0] == 1:
                    depth = arr[0]
                else:
                    depth = arr[0]
                    if depth.ndim > 2:
                        depth = depth[0]
            elif arr.ndim == 2:
                depth = arr
            else:
                depth = np.squeeze(arr)
                if depth.ndim != 2:
                    return []
            if depth.shape[0] != DEPTH_INPUT_SIZE or depth.shape[1] != DEPTH_INPUT_SIZE:
                # resize defensivo si modelo devuelve distinto tamaño
                try:
                    depth = cv2.resize(
                        depth.astype(np.float32), (DEPTH_INPUT_SIZE, DEPTH_INPUT_SIZE)
                    )
                except Exception:
                    return []
            depth_norm = _normalize_depth(depth)
            out: list[Profundidad] = []
            for cx, cy in centers:
                z_rel = _sample_z_rel_median(depth_norm, cx, cy)
                out.append(
                    Profundidad(
                        frame_id=int(frame_id),
                        box_center=BoxCenter(x=float(cx), y=float(cy)),
                        z_rel=float(max(0.0, min(1.0, z_rel))),
                        z_m=None,
                    )
                )
            return out
        except Exception:
            return []

    # alias compat predict
    def predict(
        self,
        image: NDArray[np.uint8] | None = None,
        boxes: list[Any] | None = None,
        frame_id: int = 0,
    ) -> list[Profundidad]:
        return self.estimate(image, boxes, frame_id)


def get_depth_estimator(
    models_dir: pathlib.Path | None = None,
) -> DepthEstimator:
    """Factory lazy — stub si models/midas_small_256.onnx ausente."""
    if models_dir is None:
        models_dir = pathlib.Path(__file__).parent.parent / "models"
    candidate = models_dir / "midas_small_256.onnx"
    if candidate.exists():
        return DepthEstimator(candidate)
    return DepthEstimator(None)
