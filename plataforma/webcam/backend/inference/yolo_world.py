"""YOLO-World s wrapper S3 — open-vocab PromptList.

Headless sin modelo (is_stub True) hasta que `models/yolo-world-s.onnx` exista.
API compatible con YoloDetector: predict + set_classes + save stub.
S3: lazy bajo flag YOLO_WORLD_ENABLED, slow_queue 2Hz, PromptList 20+8.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from plataforma.webcam.backend.config import (
    YOLO_WORLD_PROMPTLIST_STATIC,
)

try:
    from plataforma.webcam.backend.config import YOLO_IMGSZ as _IMGSZ_CFG
except Exception:
    _IMGSZ_CFG = 640
IMGSZ: int = int(_IMGSZ_CFG)
STRIDE: int = 32
PAD_VALUE: int = 114


@dataclass(frozen=True, slots=True)
class BoxWorld:
    """Detección World con coords normalizadas + flag is_world."""

    x: float
    y: float
    w: float
    h: float
    cls: str
    conf: float
    is_world: bool = True
    prompt_origen: str | None = None


def _letterbox_world(
    img: NDArray[np.uint8],
    size: int = IMGSZ,
) -> tuple[NDArray[np.uint8], float, tuple[int, int]]:
    """Letterbox idéntico a YoloDetector — sin dependencia circular."""
    import cv2

    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nw = round(w * r)
    nh = round(h * r)
    dw = size - nw
    dh = size - nh
    top = dh // 2
    bottom = dh - dh // 2
    left = dw // 2
    right = dw - dw // 2
    scaled = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    padded = cv2.copyMakeBorder(
        scaled,
        top,
        bottom,
        left,
        right,
        cv2.BORDER_CONSTANT,
        value=(PAD_VALUE, PAD_VALUE, PAD_VALUE),
    )
    return padded, r, (left, top)  # type: ignore[return-value]


def _nms_world(dets: NDArray[np.floating], iou_thr: float = 0.7) -> list[int]:
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


def _postprocess_world(
    raw: NDArray[np.floating],
    ratio: float,
    pad: tuple[int, int],
    orig_w: int,
    orig_h: int,
    conf_thr: float,
    iou_thr: float,
    prompt_list: list[str],
) -> list[BoxWorld]:
    """Decodifica salida World (num_classes+4, N) → List[BoxWorld] normalizado."""
    if raw.ndim == 3:
        raw = raw[0]
    # Esperado (C+4, N) donde C=len(prompt_list). Transponer a (N, C+4) si hace falta
    if raw.shape[0] == len(prompt_list) + 4 and raw.shape[1] != len(prompt_list) + 4:
        # ya es (C+4, N)
        raw = raw.T
    elif raw.shape[0] == 4 + len(prompt_list):
        raw = raw.T
    # Si sigue siendo (84,8400) con N en dim 1, transponer
    if raw.shape[1] == len(prompt_list) + 4 and raw.shape[0] > raw.shape[1]:
        # heuristic: N > C+4
        pass
    elif raw.shape[0] == len(prompt_list) + 4:
        raw = raw.T
    if raw.ndim != 2 or raw.shape[1] < 5:
        return []
    # raw (N, 4+C)
    boxes = raw[:, :4]
    scores = raw[:, 4:]
    # scores shape N x C
    if scores.shape[1] != len(prompt_list):
        # truncar o pad con ceros si mismatch (modelo exportado con C fijo distinto)
        if scores.shape[1] > len(prompt_list):
            scores = scores[:, : len(prompt_list)]
        else:
            pad_c = len(prompt_list) - scores.shape[1]
            scores = np.concatenate(
                [scores, np.zeros((scores.shape[0], pad_c), dtype=scores.dtype)], axis=1
            )
    cls_ids = np.argmax(scores, axis=1)
    cls_confs = np.max(scores, axis=1)
    keep_mask = cls_confs >= conf_thr
    if not np.any(keep_mask):
        return []
    boxes = boxes[keep_mask]
    cls_ids = cls_ids[keep_mask]
    cls_confs = cls_confs[keep_mask]
    cx, cy, w, h = boxes.T
    px, py = pad
    x1 = (cx - w / 2 - px) / ratio
    y1 = (cy - h / 2 - py) / ratio
    x2 = (cx + w / 2 - px) / ratio
    y2 = (cy + h / 2 - py) / ratio
    x1 = np.clip(x1, 0, orig_w)
    y1 = np.clip(y1, 0, orig_h)
    x2 = np.clip(x2, 0, orig_w)
    y2 = np.clip(y2, 0, orig_h)
    dets = np.stack([x1, y1, x2, y2, cls_confs, cls_ids.astype(float)], axis=1)
    keep_idx = _nms_world(dets, iou_thr)
    out: list[BoxWorld] = []
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
        label = prompt_list[cid] if 0 <= cid < len(prompt_list) else str(cid)
        conf = float(d[4])
        out.append(
            BoxWorld(
                x=max(0.0, min(1.0, nx)),
                y=max(0.0, min(1.0, ny)),
                w=max(0.0, min(1.0, nw)),
                h=max(0.0, min(1.0, nh)),
                cls=label,
                conf=max(0.0, min(1.0, conf)),
                is_world=True,
                prompt_origen=label,
            )
        )
    return out


class YoloWorldDetector:
    """Detector YOLO-World s — S3.

    Sin modelo: is_stub True, predict → [].
    Con modelo: onnxruntime con txt_feats dinámico.
    048: cache _txt_feats_static 20x512 offline + warmup(10) piggyback slow 2Hz.
    """

    def __init__(
        self,
        model_path: pathlib.Path | None = None,
        prompt_list: list[str] | None = None,
    ) -> None:
        self.model_path = model_path
        self.prompt_list: list[str] = list(prompt_list or YOLO_WORLD_PROMPTLIST_STATIC)
        self.is_stub: bool = True
        self._session: Any | None = None
        self._txt_feats_static: Any | None = None
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
                try:
                    self._txt_feats_static = np.zeros(
                        (1, len(self.prompt_list), 512), dtype=np.float32
                    )
                except Exception:
                    self._txt_feats_static = None
            except Exception:
                self._session = None
                self._txt_feats_static = None
                self.is_stub = True

    def set_classes(self, prompts: list[str]) -> None:
        """Actualiza PromptList — debounce y max 8 lo maneja ws.py S3."""
        cleaned = [str(p).strip() for p in prompts if str(p).strip()]
        if len(cleaned) > 8:
            cleaned = cleaned[:8]
        if cleaned:
            self.prompt_list = cleaned
            try:
                self._txt_feats_static = np.zeros(
                    (1, len(self.prompt_list), 512), dtype=np.float32
                )
            except Exception:
                self._txt_feats_static = None

    def warmup(self, n: int = 10) -> None:
        """Precalienta ORT graph + cache txt_feats — amortiza cold-start igual que YoloDetector."""  # noqa: E501
        if self._session is None or self.is_stub:
            return
        try:
            sess: Any = self._session
            input_name: str = sess.get_inputs()[0].name  # type: ignore
            dummy_img = np.random.randn(1, 3, 640, 640).astype(np.float32)
            dummy_txt = np.zeros(
                (1, min(8, len(self.prompt_list)), 512), dtype=np.float32
            )
            for _ in range(max(0, n)):
                try:
                    inputs = {input_name: dummy_img}
                    if len(sess.get_inputs()) > 1:  # type: ignore
                        txt_name: str = sess.get_inputs()[1].name  # type: ignore
                        inputs[txt_name] = dummy_txt
                    sess.run(None, inputs)  # type: ignore
                except Exception:
                    sess.run(None, {input_name: dummy_img})  # type: ignore
        except Exception:
            return

    def predict(
        self, image: Any | None = None, conf_thr: float | None = None
    ) -> list[BoxWorld]:
        """Infiere boxes World normalizadas. Sin imagen o sin sesión → [] stub."""
        if image is None or self._session is None or self.is_stub:
            return []
        thr = conf_thr if conf_thr is not None else 0.35
        try:
            import cv2  # type: ignore
        except Exception:
            return []
        arr: NDArray[np.uint8] = image  # type: ignore
        if arr.ndim != 3 or arr.shape[2] != 3:
            return []
        orig_h, orig_w = arr.shape[:2]
        if orig_h == 0 or orig_w == 0:
            return []
        try:
            padded, ratio, pad = _letterbox_world(arr, size=IMGSZ)
            _ = cv2
            rgb = padded[:, :, ::-1].astype(np.float32) / 255.0
            blob = np.transpose(rgb, (2, 0, 1))[None]
            blob = np.ascontiguousarray(blob, dtype=np.float32)
            # txt_feats — zeros stub 512-d (real CLIP requeriría encoder); shape 1xNx512
            if self._txt_feats_static is not None:
                try:
                    txt = self._txt_feats_static
                    # ajustar N si prompt_list cambió sin regenerar
                    if txt.shape[1] != len(self.prompt_list):  # type: ignore
                        txt = np.zeros(
                            (1, len(self.prompt_list), 512), dtype=np.float32
                        )
                except Exception:
                    txt = np.zeros((1, len(self.prompt_list), 512), dtype=np.float32)
            else:
                txt = np.zeros((1, len(self.prompt_list), 512), dtype=np.float32)
            sess: Any = self._session
            inputs: dict[str, Any] = {}
            in_names = [i.name for i in sess.get_inputs()]  # type: ignore
            # mapear por orden: 0=images, 1=txt_feats
            inputs[in_names[0]] = blob
            if len(in_names) > 1:
                # asegurar dtype float32 y shape correcto
                inputs[in_names[1]] = txt.astype(np.float32)
            raw_out = sess.run(None, inputs)[0]  # type: ignore
            raw_arr = np.asarray(raw_out)
            return _postprocess_world(
                raw_arr, ratio, pad, orig_w, orig_h, thr, 0.7, self.prompt_list
            )
        except Exception:
            return []

    def save(self, path: pathlib.Path) -> None:
        """Re-parametrizado stub — no-op S3."""
        _ = path


_world_singleton: YoloWorldDetector | None = None


def get_yolo_world_detector(
    models_dir: pathlib.Path | None = None,
    prompt_list: list[str] | None = None,
) -> YoloWorldDetector:
    global _world_singleton
    if _world_singleton is None:
        if models_dir is None:
            models_dir = pathlib.Path(__file__).parent.parent / "models"
        candidate = models_dir / "yolo-world-s.onnx"
        pl = prompt_list or YOLO_WORLD_PROMPTLIST_STATIC
        if candidate.exists():
            _world_singleton = YoloWorldDetector(candidate, pl)
        else:
            _world_singleton = YoloWorldDetector(None, pl)
    elif prompt_list is not None:
        _world_singleton.set_classes(prompt_list)
    return _world_singleton


# helper S3: extracción PromptList desde transcript voz
def extract_prompts_from_transcript(text: str) -> list[str]:
    """Regex S3: detecta 'mirá/buscá/dónde está/qué color' + noun fuera W30."""
    import re

    low = text.lower()
    triggers = [
        "mira",
        "mirá",
        "busca",
        "buscá",
        "donde esta",
        "dónde está",
        "que color",
        "qué color",
        "hay",
        "ves",
    ]
    if not any(t in low for t in triggers):
        return []
    # FIX acentos: incluir mirá/buscá/dónde en regex (antes solo sin tilde)
    m = re.search(
        r"(?:mirá|mira|buscá|busca|dónde está|donde esta|qué color es|que color es|hay|ves)\s+([^.?]+)",  # noqa: E501
        low,
    )
    if not m:
        return []
    phrase = m.group(1).strip()
    parts = re.split(r"\s+y\s+|\s*,\s*|\s+con\s+", phrase)
    prompts = [p.strip() for p in parts if len(p.strip()) >= 3 and len(p.strip()) <= 40]
    from plataforma.webcam.backend.config import YOLO_WHITELIST

    out: list[str] = []
    for p in prompts:
        if any(cls in p for cls in YOLO_WHITELIST):
            if (
                "roja" in p
                or "rojo" in p
                or "amarillo" in p
                or "negro" in p
                or "azul" in p
            ):
                out.append(p)
            continue
        out.append(p)
    return out[:8]
