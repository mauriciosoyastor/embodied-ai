# Prototipo P2 — percepción webcam (DESCARTABLE)

Pipeline: webcam del navegador → JPEG → WebSocket → backend Python (YOLO11n ONNX + MediaPipe HandLandmarker) → eventos (objetos + gesto) → overlay en el visor.

Valida: latencia percibida del loop completo, streaming por WebSocket y la separación percepción (backend) vs renderización (navegador). NO conecta la FSM.

## Cómo correr

1. **Backend** (terminal 1):
   ```
   py -3.12 -m venv .venv
   .venv\Scripts\activate
   pip install -r backend\requirements.txt
   python backend\descargar_modelos.py   # una sola vez
   python backend\selftest.py           # verifica sin cámara
   uvicorn app:app --port 8001          # desde backend/
   ```
2. **Frontend** (terminal 2):
   ```
   npm install
   npm run dev
   ```
3. Abrir **http://localhost:5173** y dar permiso de cámara.

## Stack (research R2)

Python 3.12 · `onnxruntime==1.29.0` CPU · `opencv-python==4.14.0.94` · `mediapipe==1.0.1` (Tasks API) · `yolo11n.onnx` (assets oficiales Ultralytics) · `hand_landmarker.task` (Google AI Edge).

## Modelos

No se commitean (exceden el límite de pre-commit). Se descargan con `backend\descargar_modelos.py`:

- `yolo11n.onnx` ← `https://github.com/ultralytics/assets/releases` (tag v8.3.0)
- `hand_landmarker.task` ← `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`

## Contrato de eventos (provisional, alimenta D5)

- Cliente → servidor: `blob` JPEG binario.
- Servidor → cliente: JSON `{gesto, objetos:[{x1,y1,x2,y2,conf,clase,etiqueta}], yolo_ms, mano_ms, total_ms}`.

## Gestos

`open_palm` · `fist` · `thumbs_up` por reglas geométricas sobre los 21 landmarks (sin modelo extra). Mapeo informativo a la FSM de misión: thumbs_up → RUNNING, open_palm → PAUSED, fist → ABORTED.
