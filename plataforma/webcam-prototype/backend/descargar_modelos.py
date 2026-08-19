"""Descarga los modelos del prototipo P2 (yolo11n.onnx + hand_landmarker.task)."""

import urllib.request
from pathlib import Path

MODELOS = Path(__file__).resolve().parent / "models"
URLS = {
    "yolo11n.onnx": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx",
    "hand_landmarker.task": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}


def main():
    MODELOS.mkdir(exist_ok=True)
    for nombre, url in URLS.items():
        destino = MODELOS / nombre
        if destino.exists():
            print(f"ya existe: {nombre}")
            continue
        print(f"descargando {nombre} ...")
        urllib.request.urlretrieve(url, destino)
        print(f"  ok: {nombre} ({destino.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
