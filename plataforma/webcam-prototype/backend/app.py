"""Backend del prototipo P2: webcam (browser) -> WebSocket -> percepcion -> eventos.

Descartable. Correr: uvicorn app:app --port 8001
"""

import time

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from percepcion import MODELOS, Percepcion

app = FastAPI(title="Prototipo P2 — percepción webcam (descartable)")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

percepcion = Percepcion(MODELOS / "yolo11n.onnx", MODELOS / "hand_landmarker.task")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_bytes()
        frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            continue
        t0 = time.perf_counter()
        res = percepcion.procesar(frame)
        res["total_ms"] = (time.perf_counter() - t0) * 1000
        await ws.send_json(res)
