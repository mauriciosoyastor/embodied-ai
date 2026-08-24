"""YOLO11n-pose ONNX — inferencia CPU v2 (letterbox 640 + NMS + keypoints).

Runtime con onnxruntime lazy, intra_op_num_threads=2. Si no hay modelo/sesión,
degrada a stub headless (predict → []) manteniendo compatibilidad.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from plataforma.webcam.backend.inference.yolo import (
    IMGSZ,
    letterbox,
    non_max_suppression,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

POSE_CONF_DEFAULT: float = 0.5
POSE_IOU_DEFAULT: float = 0.7
POSE_KP_NUM: int = 17


# ---------------------------------------------------------------------------
# Dominio
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Keypoint:
    """Keypoint normalizado [0,1]."""

    x: float
    y: float
    conf: float


@dataclass(frozen=True, slots=True)
class Pose:
    """Pose con bbox normalizada + 17 keypoints."""

    x: float
    y: float
    w: float
    h: float
    conf: float
    keypoints: tuple[Keypoint, ...]


# ---------------------------------------------------------------------------
# Post-proceso puro — testeable sin modelo
# ---------------------------------------------------------------------------


def _postprocess_pose(
    raw: NDArray[np.floating],
    ratio: float,
    pad: tuple[int, int],
    orig_w: int,
    orig_h: int,
    conf_thr: float,
    iou_thr: float,
) -> list[Pose]:
    """Decodifica salida YOLO pose → List[Pose] normalizado.

    raw puede ser (1,56,8400) o (1,84,8400) — soporta ambos; si no hay
    keypoints suficientes, genera keypoints dummy centrados.
    """
    if raw.ndim == 3:
        raw = raw[0]
    # raw shape (C, N) o (N, C) — normalizar a (N, C)
    if raw.ndim != 2:
        return []
    # Si C==8400 y N==56/84, trasponer
    if raw.shape[0] in (56, 84) and raw.shape[1] == 8400:
        raw = raw.T  # (8400, 56)
    elif raw.shape[0] == 8400 and raw.shape[1] in (56, 84):
        pass  # ya es (8400, 56)
    else:
        # intento genérico: si primera dim pequeña (<100), trasponer
        if raw.shape[0] < raw.shape[1] and raw.shape[0] < 100:
            raw = raw.T
    if raw.shape[0] == 0 or raw.shape[1] < 5:
        return []
    # bbox cx,cy,w,h en 0:4
    boxes = raw[:, :4]
    # scores: para pose, canal 4 suele ser conf person; si hay clases, argmax
    # heurística: si C==56 → conf en col 4; si C==84 → max 4:
    if raw.shape[1] == 56:
        cls_confs = raw[:, 4]
        # clip 0-1
        cls_ids_dummy = np.zeros_like(cls_confs, dtype=np.int64)
        _ = cls_ids_dummy
        keep_mask = cls_confs >= conf_thr
        filtered_boxes = boxes[keep_mask]
        filtered_confs = cls_confs[keep_mask]
        # keypoints: 5:56 → 17*3
        kp_raw = raw[keep_mask, 5:] if raw.shape[1] > 5 else np.zeros((0, 0))
    else:
        # fallback genérico tipo YOLO detect (84 canales)
        scores = raw[:, 4:]
        # si scores tiene muchas columnas con keypoints, solo primera es conf
        # para test, tratar col 0 como conf person
        if scores.shape[1] >= 1:
            if scores.shape[1] > 1:
                cls_confs_generic = np.max(scores[:, :1], axis=1)
            else:
                cls_confs_generic = scores[:, 0]
            # si hay 80 clases COCO (84-4), tomar max de 0-80
            if scores.shape[1] >= 80:
                cls_confs_generic = np.max(scores[:, :80], axis=1)
        else:
            cls_confs_generic = np.zeros(raw.shape[0], dtype=np.float32)
        keep_mask = cls_confs_generic >= conf_thr
        filtered_boxes = boxes[keep_mask]
        filtered_confs = cls_confs_generic[keep_mask]
        # keypoints dummy si no hay canal pose
        kp_raw = np.zeros((filtered_boxes.shape[0], 0), dtype=np.float32)

    if filtered_boxes.shape[0] == 0:
        return []
    cx, cy, w, h = filtered_boxes.T
    px, py = pad
    x1 = (cx - w / 2 - px) / ratio
    y1 = (cy - h / 2 - py) / ratio
    x2 = (cx + w / 2 - px) / ratio
    y2 = (cy + h / 2 - py) / ratio
    x1 = np.clip(x1, 0, orig_w)
    y1 = np.clip(y1, 0, orig_h)
    x2 = np.clip(x2, 0, orig_w)
    y2 = np.clip(y2, 0, orig_h)
    # NMS sobre dets [x1,y1,x2,y2,conf,cls]
    dets = np.stack(
        [x1, y1, x2, y2, filtered_confs, np.zeros_like(filtered_confs)],
        axis=1,
    )
    keep_idx = non_max_suppression(dets, iou_thr)
    out: list[Pose] = []
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
        conf = float(d[4])
        # keypoints: si kp_raw tiene datos, decodificar; si no, dummy centro
        kps: list[Keypoint] = []
        if kp_raw.shape[0] > i and kp_raw.shape[1] >= POSE_KP_NUM * 3:
            # fila mapeada: keep_idx conserva orden NMS
            # obtener fila kp del índice filtrado
            # NMS opera sobre dets en mismo orden que kp_raw
            row = kp_raw[i]
            for k in range(POSE_KP_NUM):
                kx_raw = float(row[k * 3])
                ky_raw = float(row[k * 3 + 1])
                kc_raw = float(row[k * 3 + 2]) if k * 3 + 2 < len(row) else 1.0
                # keypoints en coordenadas letterbox → des-pad y des-ratio
                kx = (kx_raw - px) / ratio
                ky = (ky_raw - py) / ratio
                # normalizar
                kx_n = kx / float(orig_w) if orig_w else 0.0
                ky_n = ky / float(orig_h) if orig_h else 0.0
                kx_n = max(0.0, min(1.0, kx_n))
                ky_n = max(0.0, min(1.0, ky_n))
                kc = max(0.0, min(1.0, kc_raw))
                # si conf es >1 (pixel), clamps ya; si es bajo, queda
                kps.append(Keypoint(x=kx_n, y=ky_n, conf=kc))
        else:
            # dummy keypoints centrados
            for _ in range(POSE_KP_NUM):
                kps.append(
                    Keypoint(
                        x=max(0.0, min(1.0, nx + nw / 2)),
                        y=max(0.0, min(1.0, ny + nh / 2)),
                        conf=0.0,
                    )
                )
        out.append(
            Pose(
                x=max(0.0, min(1.0, nx)),
                y=max(0.0, min(1.0, ny)),
                w=max(0.0, min(1.0, nw)),
                h=max(0.0, min(1.0, nh)),
                conf=max(0.0, min(1.0, conf)),
                keypoints=tuple(kps),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class PoseDetector:
    """Detector YOLO11n-pose ONNX CPU. Stub si no hay modelo."""

    def __init__(
        self,
        model_path: pathlib.Path | None = None,
        conf: float = POSE_CONF_DEFAULT,
        iou: float = POSE_IOU_DEFAULT,
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
                self._session = ort.InferenceSession(
                    str(model_path),
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                self.is_stub = False
            except Exception:
                self._session = None
                self.is_stub = True

    def predict(
        self,
        image: NDArray[np.uint8] | None = None,
        conf_thr: float | None = None,
    ) -> list[Pose]:
        """Infiere poses normalizadas. Sin imagen o sin sesión → [] stub."""
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
        _ = cv2
        rgb = padded[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(rgb, (2, 0, 1))[None]
        blob = np.ascontiguousarray(blob, dtype=np.float32)
        try:
            sess = self._session
            input_name: str = sess.get_inputs()[0].name  # type: ignore
            raw_out = sess.run(None, {input_name: blob})[0]  # type: ignore
            raw_arr = np.asarray(raw_out)
            return _postprocess_pose(raw_arr, ratio, pad, orig_w, orig_h, thr, self.iou)
        except Exception:
            return []


def get_pose_detector(
    models_dir: pathlib.Path | None = None,
) -> PoseDetector:
    """Factory lazy — stub si models ausentes."""
    if models_dir is None:
        models_dir = pathlib.Path(__file__).parent.parent / "models"
    candidate = models_dir / "yolo11n-pose.onnx"
    if candidate.exists():
        return PoseDetector(candidate)
    return PoseDetector(None)
