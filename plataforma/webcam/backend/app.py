"""FastAPI app webcam — GET /health + WS /ws/percepcion (S2-B).

Lifespan lazy: inicializa YOLO+MediaPipe si models presentes, loguea si stub.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

from plataforma.webcam.backend.identities import store
from plataforma.webcam.backend.inference.gesture import get_gesture_recognizer
from plataforma.webcam.backend.inference.yolo import get_yolo_detector
from plataforma.webcam.backend.metrics import render_prometheus
from plataforma.webcam.backend.ws import perception_ws_handler

logger = logging.getLogger(__name__)


class VozRequest(BaseModel):
    prompt: str
    modelo: str | None = None


# Grounding voz (mapa #130 G1/G3): frescura TTL por campo.
FRESH_ATRIBUTOS_MS = 200
FRESH_Z_MS = 500


def _fresh_snapshot(
    max_age_ms: int = FRESH_ATRIBUTOS_MS,
) -> tuple[list[dict[str, Any]], int, int] | None:
    """Snapshot (atributos, frame_id, age_ms) si la percepción está fresca.

    Lee los globales de `ws` con import diferido (sin ciclo). `None` = stale
    o ausente: la voz no debe afirmar nada (silencio G3).
    """
    try:
        import time as _t

        from plataforma.webcam.backend.ws import last_atributos, last_frame_id, last_ts

        age = int(_t.time() * 1000) - int(last_ts or 0)
        if last_atributos and age <= max_age_ms:
            return list(last_atributos), int(last_frame_id), age
    except Exception:
        pass
    return None


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
        # Warmup ONNX/TensorRT — amortiza cold-start p99 120ms (041) + World-s 048
        try:
            if not yolo.is_stub:
                yolo.warmup(10)
                logger.info("YOLO warmup(10) ok")
        except Exception as exc:  # pragma: no cover
            logger.warning("YOLO warmup falló: %s", exc)
        try:
            from plataforma.webcam.backend.inference.yolo_world import (
                get_yolo_world_detector,
            )

            world = get_yolo_world_detector()
            if not world.is_stub:
                world.warmup(10)
                logger.info(
                    "YOLO-World warmup(10) ok prompts=%d txt_feats=%s",
                    len(world.prompt_list),
                    getattr(world, "_txt_feats_static", None) is not None,
                )
            else:
                logger.info(
                    "YOLO-World stub — model ausente (lazy) prompts=%d",
                    len(world.prompt_list),
                )
        except Exception as exc:  # pragma: no cover
            logger.warning("YOLO-World warmup falló: %s", exc)
        # Hidratar identities.json (hibrido)
        ids = await store.load()
        logger.info("Identities cargadas: %d", len(ids))
    except Exception as exc:  # pragma: no cover
        logger.warning("Lifespan init falló (stub fallback): %s", exc)
    yield
    logger.info("Shutdown webcam backend")


app = FastAPI(title="webcam-backend", version="0.1.0", lifespan=lifespan)

# CORS para fetch 5173→8000 (Ticket 04) — vite dev 5173 y preview
try:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ],
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception:
    pass


@app.get("/health")
async def health() -> dict[str, str]:
    """Healthcheck simple."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Any:
    """OTel Prometheus — S2-D cache_hit_ratio + ttl_expirations + glass_to_glass."""
    from fastapi.responses import PlainTextResponse

    body = render_prometheus()
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4")


@app.get("/identities")
async def list_identities() -> list[dict[str, object]]:
    """Snapshot hibrido para hidratación inicial (Ticket 025)."""
    return await store.get_all()


@app.post("/fsm/reset")
async def fsm_reset() -> dict[str, str]:
    """Libera latch ABORTED → IDLE sin reconectar WS (Ticket 04)."""
    try:
        from plataforma.webcam.backend.ws import _mission_fsm
    except Exception:
        return {"status": "error", "mission": "IDLE"}
    try:
        _mission_fsm.reset()
        # reset last mission cache para forzar próximo envelope
        import plataforma.webcam.backend.ws as ws_mod

        ws_mod._last_mission = None  # type: ignore
        return {"status": "ok", "mission": _mission_fsm.estado.value}
    except Exception as exc:
        return {"status": "error", "mission": str(exc)}


@app.get("/fsm/state")
async def fsm_state() -> dict[str, str]:
    """Estado FSM actual para polling/dashboard."""
    try:
        from plataforma.webcam.backend.ws import _mission_fsm

        return {"mission": _mission_fsm.estado.value}
    except Exception:
        return {"mission": "IDLE"}


@app.post("/voz")
async def VozHandler(req: VozRequest) -> dict[str, str]:
    """Proxy voz: Gemini primero, OpenAI fallback, mock final. S3 anclaje AtributoVista.

    Grounded harness (mapa #130): todo prompt se encierra con
    Percepción viva fresca (TTL G1); sin frescura la voz calla (G3).
    """  # noqa: E501
    prompt = req.prompt.strip()
    if not prompt:
        return {"text": ""}

    # Gate G1/G3 (mapa #130): sin percepción fresca no se afirma nada.
    snapshot = _fresh_snapshot()
    if snapshot is None:
        return {"text": ""}
    last_atributos, last_frame_id, _age = snapshot

    # Grounding previo backend-only: inyectar Percepción viva a TODO prompt.
    # Este prefijo alimenta LLMs pero NUNCA sale en `text` (ver T1 checklist).
    _descs = ", ".join(
        [
            f"{a.get('cls')} {a.get('color')} {a.get('tamano')} "
            f"{a.get('color_hsv_hex', '')} z:{a.get('z_rel') or '?'}"
            f"{' WORLD:' + str(a.get('prompt_origen')) if a.get('is_world') else ''}"  # noqa: E501
            for a in last_atributos[:4]
        ]
    )
    grounded_prefix = (
        f"[Percepción viva frame #{last_frame_id} age {_age}ms: {_descs}] "
        f"Instrucción grounding: responde SOLO sobre lo que ves. "  # noqa: E501
        f"Si no ves, di 'No veo objetos ahora'. Prohibido inventar precios/Walmart. "  # noqa: E501
    )
    # prompt efectivo para LLM
    prompt_grounded = (
        f"{grounded_prefix}Usuario dice: {prompt}" if grounded_prefix else prompt
    )
    # S3 — anclaje voz a AtributoVista: si pregunta por color/tamaño/qué ves, responder desde last_atributos si fresh <500ms  # noqa: E501
    try:
        low_q = prompt.lower()
        is_color_q = any(
            k in low_q
            for k in [
                "color",
                "tamaño",
                "tamano",
                "qué ves",
                "que ves",
                "izquierda",
                "derecha",
                "distancia",
            ]
        )
        if is_color_q:
            # Gate G1/G3: la frescura ya quedó validada arriba (snapshot).
            if last_atributos:
                # buscar taza/cup si pregunta específica, sino listar todos
                target = None
                if "taza" in low_q or "cup" in low_q:
                    target = next(
                        (a for a in last_atributos if a.get("cls") == "cup"), None
                    )
                elif "tv" in low_q:
                    target = next(
                        (a for a in last_atributos if a.get("cls") == "tv"), None
                    )
                # relaciones espaciales: izquierda/derecha por centroide
                if "izquierda" in low_q or "derecha" in low_q and "taza" in low_q:
                    sorted_at = sorted(
                        last_atributos,
                        key=lambda a: float(a.get("centroide", {}).get("x_c", 0.5)),
                    )
                    cup = next(
                        (a for a in last_atributos if a.get("cls") == "cup"), None
                    )
                    if cup and sorted_at:
                        cup_x = float(cup.get("centroide", {}).get("x_c", 0.5))
                        left = [
                            a
                            for a in sorted_at
                            if float(a.get("centroide", {}).get("x_c", 0)) < cup_x
                        ]
                        right = [
                            a
                            for a in sorted_at
                            if float(a.get("centroide", {}).get("x_c", 0)) > cup_x
                        ]
                        if "izquierda" in low_q and left:
                            a = left[-1]
                            return {
                                "text": f"A la izquierda de la taza está {a.get('cls')} {a.get('color')} {a.get('tamano')}."  # noqa: E501
                            }
                        if "derecha" in low_q and right:
                            a = right[0]
                            return {
                                "text": f"A la derecha de la taza está {a.get('cls')} {a.get('color')} {a.get('tamano')}."  # noqa: E501
                            }
                if target and "color" in low_q:
                    return {
                        "text": f"La {target.get('cls')} es {target.get('color')} tamaño {target.get('tamano')}."  # noqa: E501
                    }
                if "qué ves" in low_q or "que ves" in low_q:
                    descs = ", ".join(
                        [
                            f"{a.get('cls')} {a.get('color')} {a.get('tamano')}"  # noqa: E501
                            for a in last_atributos[:4]
                        ]
                    )
                    n = len(last_atributos)
                    return {
                        "text": f"Veo {n} objeto{'s' if n != 1 else ''}: {descs}."  # noqa: E501
                    }
                if target:
                    return {
                        "text": f"Veo {target.get('cls')} {target.get('color')} {target.get('tamano')}."  # noqa: E501
                    }
    except Exception:
        pass
    # S3 dynamic PromptList: FIX — fuera de is_color_q para que "mira/busca/dónde está" dispare siempre si DYNAMIC=True  # noqa: E501
    try:
        from plataforma.webcam.backend.config import YOLO_WORLD_DYNAMIC_BY_VOZ

        if YOLO_WORLD_DYNAMIC_BY_VOZ:
            from plataforma.webcam.backend.inference.yolo_world import (
                extract_prompts_from_transcript,
                get_yolo_world_detector,
            )

            prompts = extract_prompts_from_transcript(prompt)
            if prompts:
                get_yolo_world_detector(prompt_list=prompts)
                # ack corto si es comando percepción puro — evita LLM fallback "incompleto"  # noqa: E501
                low2 = prompt.lower()
                if any(
                    k in low2
                    for k in ["mira", "mirá", "busca", "buscá", "dónde", "donde"]
                ):  # noqa: E501
                    return {"text": f"Buscando {', '.join(prompts)}."}
    except Exception:
        pass
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

    # 1) Groq primario (Ticket 021: Groq→HF→Gemini→mock) — grounded
    if has_groq:
        try:
            modelo = os.getenv("GROQ_MODEL", "").strip() or gemini_client.MODELO_DEFECTO
            text = gemini_client.responder(prompt_grounded, modelo=modelo)
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
                    prompt_grounded, modelo="meta-llama/Llama-3.2-3B-Instruct"
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

    # 3) Intentar Gemini legacy — grounded
    if has_google:
        try:
            modelo = (
                os.getenv("GEMINI_MODEL", "").strip()
                or gemini_client.MODELO_GEMINI_LEGACY
            )
            text = gemini_client.responder(prompt_grounded, modelo=modelo)
            return {"text": text}
        except Exception as e:
            logger.warning("Gemini fallo: %s", e)

    # 4) Intentar OpenAI fallback (usa GROQ_MODEL si existe, sino gpt-3.5-turbo) — grounded  # noqa: E501
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
                messages=[{"role": "user", "content": prompt_grounded}],
            )
            txt = (resp.choices[0].message.content or "").strip()
            if txt:
                return {"text": txt}
        except Exception as e:
            logger.warning("OpenAI fallback fallo: %s", e)

    # Mock final (mapa #130 G3): silencio total — el mock nunca afirma visión
    # ni devuelve el prefijo (era el leak de la captura). Las respuestas
    # deterministas con visión fresca ya salieron por atajos S3 arriba.
    return {"text": ""}


class VisionCaptionRequest(BaseModel):
    frame_id: int = 0
    jpeg_b64: str | None = None
    objects: list[str] | None = None


@app.post("/vision/caption")
async def vision_caption(req: VisionCaptionRequest) -> dict[str, object]:
    """VLM 1Hz Groq→HF→Gemini→mock. No rompe /voz; TODO overlay #82."""
    try:
        from plataforma.webcam.backend.inference.vlm import get_vlm_client

        client = get_vlm_client()
        leyenda = client.caption(
            image_b64=req.jpeg_b64, frame_id=req.frame_id, objects=req.objects
        )
        return {
            "frame_id": leyenda.frame_id,
            "caption": leyenda.caption,
            "objects": list(leyenda.objects),
            "conf": leyenda.conf,
            "ts": leyenda.ts,
            "provider": leyenda.provider,
        }
    except Exception as exc:  # pragma: no cover
        logger.warning("vision/caption fallback mock: %s", exc)
        return {
            "frame_id": req.frame_id,
            "caption": "Escena vacia (mock)",
            "objects": req.objects or [],
            "conf": 0.5,
            "ts": 0,
            "provider": "mock",
        }


@app.websocket("/ws/percepcion")
async def ws_percepcion(websocket: WebSocket) -> None:
    """Único WebSocket percepción — delega a ws.perception_ws_handler."""
    await perception_ws_handler(websocket)
