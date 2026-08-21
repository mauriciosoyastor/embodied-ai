"""FastAPI app webcam — GET /health + WS /ws/percepcion (S2-B).

Lifespan lazy: inicializa YOLO+MediaPipe si models presentes, loguea si stub.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket

from plataforma.webcam.backend.inference.gesture import get_gesture_recognizer
from plataforma.webcam.backend.inference.yolo import get_yolo_detector
from plataforma.webcam.backend.ws import perception_ws_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicializa detectores lazy — no falla si models ausentes."""
    _ = app
    try:
        yolo = get_yolo_detector()
        gesture = get_gesture_recognizer()
        if yolo.is_stub:
            logger.info("YOLO stub activo — model ausente (lazy)")
        else:
            logger.info("YOLO cargado: %s", yolo.model_path)
        if gesture.is_stub:
            logger.info("Gesture stub activo — model ausente (lazy)")
        else:
            logger.info("Gesture cargado: %s", gesture.model_path)
    except Exception as exc:  # pragma: no cover
        logger.warning("Lifespan init falló (stub fallback): %s", exc)
    yield
    logger.info("Shutdown webcam backend")


app = FastAPI(title="webcam-backend", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Healthcheck simple."""
    return {"status": "ok"}


@app.websocket("/ws/percepcion")
async def ws_percepcion(websocket: WebSocket) -> None:
    """Único WebSocket percepción — delega a ws.perception_ws_handler."""
    await perception_ws_handler(websocket)
