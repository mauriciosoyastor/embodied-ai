"""FastAPI app webcam — GET /health + WS /ws/percepcion (S2-B).

Lifespan lazy: inicializa YOLO+MediaPipe si models presentes, loguea si stub.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

from plataforma.webcam.backend.identities import store
from plataforma.webcam.backend.inference.gesture import get_gesture_recognizer
from plataforma.webcam.backend.inference.yolo import get_yolo_detector
from plataforma.webcam.backend.ws import perception_ws_handler

logger = logging.getLogger(__name__)


class VozRequest(BaseModel):
    prompt: str
    modelo: str | None = None


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
        # Hidratar identities.json (hibrido)
        ids = await store.load()
        logger.info("Identities cargadas: %d", len(ids))
    except Exception as exc:  # pragma: no cover
        logger.warning("Lifespan init falló (stub fallback): %s", exc)
    yield
    logger.info("Shutdown webcam backend")


app = FastAPI(title="webcam-backend", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Healthcheck simple."""
    return {"status": "ok"}


@app.get("/identities")
async def list_identities() -> list[dict[str, object]]:
    """Snapshot hibrido para hidratación inicial (Ticket 025)."""
    return await store.get_all()


@app.post("/voz")
async def VozHandler(req: VozRequest) -> dict[str, str]:
    """Proxy voz: Gemini primero, OpenAI fallback, mock final."""
    prompt = req.prompt.strip()
    if not prompt:
        return {"text": ""}
    import os
    import pathlib
    import sys

    fase1_path = pathlib.Path(__file__).resolve().parents[3] / "fase-1"
    if str(fase1_path) not in sys.path:
        sys.path.insert(0, str(fase1_path))
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(dotenv_path=fase1_path / ".env")
        load_dotenv()
    except Exception:
        pass
    import gemini_client  # type: ignore

    has_groq = bool(os.getenv("GROQ_API_KEY", "").strip())
    has_google = bool(os.getenv("GOOGLE_API_KEY", "").strip())
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    has_hf = bool(os.getenv("HF_TOKEN", "").strip())

    # 1) Groq primario (Ticket 021: Groq→HF→Gemini→mock)
    if has_groq:
        try:
            modelo = os.getenv("GROQ_MODEL", "").strip() or gemini_client.MODELO_DEFECTO
            text = gemini_client.responder(prompt, modelo=modelo)
            if text.strip():
                return {"text": text}
        except Exception as e:
            logger.warning("Groq fallo: %s", e)

    # 2) Secundario HF Router (si GROQ 429/500)
    if has_hf:
        try:
            # HF Router usa mismo cliente OpenAI-compatible pero con base_url HF
            hf_base = (
                os.getenv("OPENAI_BASE_URL_FALLBACK", "").strip()
                or "https://router.huggingface.co/v1"
            )
            # temporal override base_url para este intento
            orig_base = os.getenv("OPENAI_BASE_URL", "")
            os.environ["OPENAI_BASE_URL"] = hf_base
            try:
                text = gemini_client.responder(
                    prompt, modelo="meta-llama/Llama-3.2-3B-Instruct"
                )
                if text.strip():
                    return {"text": text}
            finally:
                if orig_base:
                    os.environ["OPENAI_BASE_URL"] = orig_base
                else:
                    os.environ.pop("OPENAI_BASE_URL", None)
        except Exception as e:
            logger.warning("HF Router fallo: %s", e)

    # 3) Intentar Gemini legacy
    if has_google:
        try:
            modelo = (
                os.getenv("GEMINI_MODEL", "").strip()
                or gemini_client.MODELO_GEMINI_LEGACY
            )
            text = gemini_client.responder(prompt, modelo=modelo)
            return {"text": text}
        except Exception as e:
            logger.warning("Gemini fallo: %s", e)

    # 4) Intentar OpenAI fallback (usa GROQ_MODEL si existe, sino gpt-3.5-turbo)
    if has_openai:
        try:
            from openai import OpenAI

            api_key = (
                os.getenv("GROQ_API_KEY", "").strip()
                or os.getenv("OPENAI_API_KEY", "").strip()
            )
            base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
            client = OpenAI(api_key=api_key, base_url=base_url)
            fallback_model = os.getenv("GROQ_MODEL", "").strip() or "gpt-3.5-turbo"
            resp = client.chat.completions.create(
                model=fallback_model,
                messages=[{"role": "user", "content": prompt}],
            )
            txt = (resp.choices[0].message.content or "").strip()
            if txt:
                return {"text": txt}
        except Exception as e:
            logger.warning("OpenAI fallback fallo: %s", e)

    # 3) Mock final segun patrones
    low = prompt.lower()
    if "hola" in low:
        return {
            "text": (
                "¡Hola! Soy Muse Spark 1.2 free vía OpenAI (fallback). "
                "¿Como te registro por camara? Mirá y hacé pulgar arriba."
            )
        }
    if "registr" in low:
        return {
            "text": (
                "Perfecto, para registrarte mirá a la camara y "
                "hacé pulgar arriba. (fallback OpenAI)"
            )
        }
    if "quien" in low:
        return {
            "text": (
                "Soy Muse Spark 1.2, orquestador cognitivo de Embodied AI. "
                "(fallback OpenAI)"
            )
        }
    return {
        "text": (
            f'Recibio: "{prompt}" (fallback OpenAI — '
            "Gemini y OpenAI no disponibles por el momento)."
        )
    }


@app.websocket("/ws/percepcion")
async def ws_percepcion(websocket: WebSocket) -> None:
    """Único WebSocket percepción — delega a ws.perception_ws_handler."""
    await perception_ws_handler(websocket)
