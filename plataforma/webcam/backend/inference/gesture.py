"""MediaPipe Hand Landmarker Tasks 1.0.1 — gestos por reglas geométricas S2-A.

Tres gestos (+ none) con heurística sin modelo extra:
  open_palm = 4 dedos + pulgar extendidos
  thumbs_up = solo pulgar extendido
  fist      = ningún dedo extendido
Desacoplado de FSM — expone GestoReconocido y classify_gesture puro.
"""

from __future__ import annotations

import math
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    pass

GestureLabel = Literal["open_palm", "fist", "thumbs_up", "none"]
ALLOWED_LABELS: frozenset[str] = frozenset({"open_palm", "fist", "thumbs_up", "none"})

DEDOS: list[tuple[int, int]] = [(8, 6), (12, 10), (16, 14), (20, 18)]


class LandmarkLike(Protocol):
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class GestoReconocido:
    """Evento de dominio desacoplado de MediaPipe — consume handle_gesto."""

    label: GestureLabel
    conf: float
    frame_id: int
    ts: int


# ---------------------------------------------------------------------------
# Reglas geométricas puras — testeables sin MediaPipe
# ---------------------------------------------------------------------------


def _dist(a: LandmarkLike, b: LandmarkLike) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _pulgar_extendido(lm: list[LandmarkLike]) -> bool:
    # tip 4 vs ip 3 respecto a muñeca 0 — distancia
    d_tip = _dist(lm[4], lm[0])
    d_ip = _dist(lm[3], lm[0])
    return d_tip > d_ip * 1.15


def classify_gesture(lm: list[LandmarkLike]) -> GestureLabel:
    """Clasifica 21 landmarks normalizados [0,1] (y hacia abajo)."""
    if len(lm) < 21:
        return "none"
    dedos_ext = [lm[tip].y < lm[pip].y for (tip, pip) in DEDOS]
    pulgar = _pulgar_extendido(lm)
    n = sum(dedos_ext)
    if n == 4 and pulgar:
        return "open_palm"
    if n == 0 and pulgar:
        return "thumbs_up"
    if n == 0 and not pulgar:
        return "fist"
    return "none"


def gesto_confidence(label: GestureLabel) -> float:
    """Confianza heurística para el evento de dominio."""
    if label == "none":
        return 0.0
    return 0.92


# ---------------------------------------------------------------------------
# Reconocedor con MediaPipe Tasks (lazy) + fallback stub
# ---------------------------------------------------------------------------


class GestureRecognizer:
    """Wrapper HandLandmarker Tasks 1.0.1. Stub headless si no hay modelo."""

    def __init__(self, model_path: pathlib.Path | None = None) -> None:
        self.model_path = model_path
        self.is_stub: bool = True
        self._landmarker: object | None = None
        self._ts: int = 0
        if model_path is not None and model_path.exists():
            try:
                import mediapipe as mp  # type: ignore

                base = mp.tasks.BaseOptions(model_asset_path=str(model_path))
                opts = mp.tasks.vision.HandLandmarkerOptions(
                    base_options=base,
                    num_hands=1,
                    min_hand_detection_confidence=0.5,
                    min_hand_presence_confidence=0.5,
                    min_tracking_confidence=0.5,
                    running_mode=mp.tasks.vision.RunningMode.VIDEO,
                )
                self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(
                    opts
                )
                self.is_stub = False
            except Exception:
                self._landmarker = None
                self.is_stub = True

    def recognize(
        self,
        image: object | None = None,
        frame_id: int = 0,
        ts: int = 0,
    ) -> GestoReconocido:
        """Infiere gesto desde frame BGR. Stub → none."""
        if self._landmarker is None or image is None:
            return GestoReconocido(label="none", conf=0.0, frame_id=frame_id, ts=ts)
        try:
            import cv2
            import mediapipe as mp
            import numpy as np

            arr = image
            # Validar ndarray
            if not isinstance(arr, np.ndarray):
                return GestoReconocido(label="none", conf=0.0, frame_id=frame_id, ts=ts)
            if arr.ndim != 3 or arr.size == 0:
                return GestoReconocido(label="none", conf=0.0, frame_id=frame_id, ts=ts)
            rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            self._ts += 33
            ts_video = ts if ts > 0 else self._ts
            res = self._landmarker.detect_for_video(mp_img, int(ts_video))  # type: ignore[attr-defined]
            hand_lms = getattr(res, "hand_landmarks", None)
            if not hand_lms:
                return GestoReconocido(label="none", conf=0.0, frame_id=frame_id, ts=ts)
            lm = hand_lms[0]
            label = classify_gesture(lm)
            conf = gesto_confidence(label)
            return GestoReconocido(label=label, conf=conf, frame_id=frame_id, ts=ts)
        except Exception:
            return GestoReconocido(label="none", conf=0.0, frame_id=frame_id, ts=ts)

    def recognize_landmarks(
        self,
        landmarks: list[LandmarkLike],
        frame_id: int = 0,
        ts: int = 0,
    ) -> GestoReconocido:
        """Atajo headless: clasifica landmarks sintéticos sin MediaPipe."""
        label = classify_gesture(landmarks)
        conf = gesto_confidence(label)
        return GestoReconocido(label=label, conf=conf, frame_id=frame_id, ts=ts)


def get_gesture_recognizer(
    models_dir: pathlib.Path | None = None,
) -> GestureRecognizer:
    """Factory lazy — stub si model ausente."""
    if models_dir is None:
        models_dir = pathlib.Path(__file__).parent.parent / "models"
    candidate = models_dir / "hand_landmarker.task"
    if candidate.exists():
        return GestureRecognizer(candidate)
    return GestureRecognizer(None)
