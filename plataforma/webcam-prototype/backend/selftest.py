"""Selftest headless del prototipo P2 (sin camara).

Corre el pipeline completo con un frame sintetico y valida el clasificador
de gestos con landmarks fabricados. Salida: PASS/FAIL por chequeo.
"""

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))


class Punto:
    def __init__(self, x, y):
        self.x, self.y = x, y


def _base():
    lm = [Punto(0.5, 0.9)] * 21
    lm[3] = Punto(0.58, 0.82)  # pulgar ip (distinto de la muñeca)
    return lm


def _palm():
    lm = _base()
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        lm[tip] = Punto(lm[pip].x, lm[pip].y - 0.25)
    lm[4] = Punto(0.78, 0.70)
    return lm


def _fist():
    lm = _base()
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        lm[tip] = Punto(lm[pip].x, lm[pip].y + 0.02)
    lm[4] = Punto(0.59, 0.83)
    return lm


def _thumbs_up():
    lm = _base()
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        lm[tip] = Punto(lm[pip].x, lm[pip].y + 0.02)
    lm[4] = Punto(0.60, 0.35)
    return lm


def _check(nombre, cond):
    print(f"{'PASS' if cond else 'FAIL'}  {nombre}")
    return cond


def main():
    from gestos import clasificar_gesto
    from percepcion import MODELOS, YoloDetector

    ok = True
    ok &= _check(
        "modelos presentes",
        (MODELOS / "yolo11n.onnx").exists()
        and (MODELOS / "hand_landmarker.task").exists(),
    )

    yolo = YoloDetector(MODELOS / "yolo11n.onnx")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    t0 = time.perf_counter()
    dets = yolo.detectar(frame)
    ms = (time.perf_counter() - t0) * 1000
    ok &= _check(f"YOLO corre sin camara (vacio, {ms:.1f} ms)", isinstance(dets, list))

    ok &= _check("gesto open_palm", clasificar_gesto(_palm()) == "open_palm")
    ok &= _check("gesto fist", clasificar_gesto(_fist()) == "fist")
    ok &= _check("gesto thumbs_up", clasificar_gesto(_thumbs_up()) == "thumbs_up")

    print("SELFTEST", "OK" if ok else "FALLO")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
