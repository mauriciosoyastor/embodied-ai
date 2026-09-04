"""FastAPI app webcam — GET /health + WS /ws/percepcion (S2-B).

Lifespan lazy: inicializa YOLO+MediaPipe si models presentes, loguea si stub.
"""

from __future__ import annotations

import logging
import re
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


class TurnoHistorial(BaseModel):
    role: str
    content: str


class VozRequest(BaseModel):
    prompt: str
    modelo: str | None = None
    historial: list[TurnoHistorial] | None = None


# Grounding voz (mapa #130 G1/G3): frescura TTL por campo.
# 2000ms en vez de 200ms: con inferencia CPU ~800ms/frame + envío 2Hz toda
# percepción "fresca" real llega con ~700-1000ms de edad; 200ms solo servía
# con GPU. Para conversar, una foto de hace 1s sigue siendo válida.
FRESH_ATRIBUTOS_MS = 2000
FRESH_Z_MS = 500

# Saludo/smalltalk que NO afirma nada visual: no requiere percepción fresca.
_SALUDO_KEYWORDS = (
    "hola",
    "buenas",
    "cómo estás",
    "como estas",
    "qué tal",
    "que tal",
    "quién sos",
    "quien sos",
    "cómo te llam",
    "como te llam",
    "gracias",
    "chau",
    "adiós",
    "adios",
    "buen día",
    "buenas tardes",
    "buenas noches",
)
# Si el prompt trae alguna de estas, es pregunta visual aunque empiece con hola.
_VISION_KEYWORDS = (
    "color",
    "tamaño",
    "tamano",
    "qué ves",
    "que ves",
    "qué hay",
    "que hay",
    "izquierda",
    "derecha",
    "distancia",
    "cerca",
    "lejos",
    "mira",
    "mirá",
    "busca",
    "buscá",
    "dónde",
    "donde",
    "taza",
    "cup",
    "tv",
    "objeto",
    "objetos",
    "ves",
    "veo",
    "ven",
    "viendo",
    "viend",
    "mirando",
    "miran",
    "observ",
    "vist",
    "hay",
    "muest",
    "enseñ",
    "ensen",
)


def _es_saludo(prompt: str) -> bool:
    """True si es smalltalk sin afirmación visual (no necesita cámara)."""
    low = prompt.lower()
    if not any(k in low for k in _SALUDO_KEYWORDS):
        return False
    return not any(k in low for k in _VISION_KEYWORDS)


# Acuse conversacional que NO afirma nada visual (perfecto, genial, dale):
# como el saludo, pasa sin cámara para no repetir "No veo objetos".
_CHARLA_KEYWORDS = (
    "perfecto",
    "genial",
    "buenísimo",
    "buenisimo",
    "excelente",
    "bárbaro",
    "barbaro",
    "entendido",
    "de nada",
    "dale",
    "jaja",
)


def _es_charla(prompt: str) -> bool:
    """True si es acuse sin afirmación visual (no necesita cámara)."""
    low = prompt.lower()
    if not any(k in low for k in _CHARLA_KEYWORDS):
        return False
    return not any(k in low for k in _VISION_KEYWORDS)


# Pregunta que SÍ afirma visión (requiere percepción fresca; sin ella G3 calla).
# Incluye personas: "¿quién hay?", "¿ves a alguien?", "¿hay gente?".
_PERSONA_KEYWORDS = (
    "persona",
    "personas",
    "alguien",
    "gente",
    "quién hay",
    "quien hay",
    "quién está",
    "quien esta",
    "ves a",
    "se ve",
    "cuánt",
    "cuant",
)


def _es_pregunta_visual(prompt: str) -> bool:
    """True si el prompt pide visión (objetos o personas)."""
    low = prompt.lower()
    if any(k in low for k in _VISION_KEYWORDS):
        return True
    return any(k in low for k in _PERSONA_KEYWORDS)


# Clases COCO → es-AR para respuestas habladas (el detector habla inglés).
_CLS_ES: dict[str, str] = {
    "person": "persona",
    "chair": "silla",
    "couch": "sillón",
    "bottle": "botella",
    "cup": "taza",
    "cell phone": "celular",
    "laptop": "notebook",
    "keyboard": "teclado",
    "mouse": "mouse",
    "book": "libro",
    "backpack": "mochila",
    "handbag": "cartera",
    "remote": "control remoto",
    "tv": "tele",
    "bed": "cama",
    "dining table": "mesa",
    "toilet": "inodoro",
    "potted plant": "planta",
    "microwave": "microondas",
    "oven": "horno",
    "sink": "pileta",
    "refrigerator": "heladera",
    "clock": "reloj",
    "vase": "florero",
    "toaster": "tostadora",
    "wine glass": "copa",
    "bowl": "bol",
    "scissors": "tijera",
    "teddy bear": "peluche",
    "toothbrush": "cepillo de dientes",
}


def _cls_es(cls: str) -> str:
    """Nombre en es-AR para una clase del detector (fallback: original)."""
    return _CLS_ES.get(str(cls or "").strip().lower(), str(cls))


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


# Veto G2/T1: todo lo que jamás debe llegar a la UI (ni TTS ni panel).
_LEAK_PATTERNS = (
    r"\[Percepci[^\]]*\]",  # eco del prefijo [...] (mock verbatim, paso 2)
    r"Instrucci.n grounding:[^.]*\.",
    r"responde SOLO[^.]*\.",
    r"\(mock grounded[^)]*\)",
    r"mock grounded[^.\n]*",
    r"frame #\d+",
    r"age \d+ms",
    r"#[0-9a-fA-F]{3,8}\b",
    r"\bz:\?",
    r"\bWORLD:[^\s]*",
)
_LEAK_RE = re.compile("|".join(_LEAK_PATTERNS))
_EMPTY_PARENS_RE = re.compile(r"\(\s*\)")
_SPACES_RE = re.compile(r"[ \t]{2,}")


def strip_grounding_leak(text: str) -> str:
    """Defensa en profundidad: quita ecos de grounding/debug de una salida.

    Se aplica a TODA respuesta `text` (incluido texto LLM, que puede repetir
    el prefijo). Idempotente; el contenido legítimo pasa intacto.
    """
    cleaned = _LEAK_RE.sub("", text)
    cleaned = _EMPTY_PARENS_RE.sub("", cleaned)
    return _SPACES_RE.sub(" ", cleaned).strip()


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
    """Proxy voz: Ollama local primero, Groq/HF/Gemini backup, mock final.
    S3 anclaje AtributoVista.

    Grounded harness (mapa #130): todo prompt se encierra con
    Percepción viva fresca (TTL G1); sin frescura la voz calla (G3).
    """  # noqa: E501
    prompt = req.prompt.strip()
    if not prompt:
        return {"text": ""}

    # Gate G1/G3 (mapa #130): sin percepción fresca no se afirma NADA visual.
    # Solo las preguntas visuales (objetos o personas) callan sin cámara.
    # Charla genérica ("contame algo", "¿y entonces?") pasa pelada al LLM
    # para conversar fluido sin afirmar visión (no inventa por system prompt).
    es_saludo = _es_saludo(prompt)
    es_charla = _es_charla(prompt)
    es_visual = _es_pregunta_visual(prompt)
    snapshot = _fresh_snapshot()
    if snapshot is None and es_visual and not es_charla:
        return {"text": ""}
    if snapshot is None:
        last_atributos: list[dict[str, Any]] = []
        last_frame_id, _age = 0, 0
    else:
        last_atributos, last_frame_id, _age = snapshot

    # Acuse conversacional: respuesta determinista SIN pasar por el LLM.
    # qwen1.5b alucina "No veo objetos ahora" ante acuses pelados (con o
    # sin historial), y ese eco realimenta el historial ("repite lo mismo").
    # El saludo tampoco afirma visión: responde determinista sin LLM.
    # Con cámara activa (snapshot fresco) saluda describiendo lo que ve en
    # vez de invitar a iniciarla (captura: saludo con age 313ms fresco).
    if es_saludo and not es_visual:
        if last_atributos:
            _n_sal = len(last_atributos)
            _descs_sal = ", ".join(
                f"{_cls_es(str(a.get('cls')))} {a.get('color')} {a.get('tamano')}"
                for a in last_atributos[:4]
            )
            return {
                "text": strip_grounding_leak(
                    f"¡Hola! Te escucho. Veo {_n_sal} objeto{'s' if _n_sal != 1 else ''}: {_descs_sal}."  # noqa: E501
                )
            }
        return {
            "text": "¡Hola! Te escucho. Si iniciás la cámara, te describo lo que ve."
        }
    if es_charla:
        return {"text": "Entendido, te sigo escuchando."}

    # Grounding previo backend-only: inyectar Percepción viva a TODO prompt
    # CON visión fresca. Sin snapshot (solo saludo) el prompt va pelado para
    # que el LLM no invente objetos: un saludo no necesita grounding.
    if snapshot is None:
        prompt_grounded = prompt
    else:
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
        prompt_grounded = f"{grounded_prefix}Usuario dice: {prompt}"
    # S3 — anclaje voz a AtributoVista: si pregunta por color/tamaño/qué ves/
    # personas, responder desde last_atributos (determinista, sin LLM).
    try:
        low_q = prompt.lower()
        is_persona_q = any(
            k in low_q
            for k in [
                "persona",
                "personas",
                "alguien",
                "gente",
                "quién hay",
                "quien hay",
                "quién está",
                "quien esta",
                "hay gente",
            ]
        )
        is_color_q = (
            any(
                k in low_q
                for k in [
                    "color",
                    "tamaño",
                    "tamano",
                    "qué ves",
                    "que ves",
                    "qué hay",
                    "que hay",
                    "izquierda",
                    "derecha",
                    "distancia",
                    "cuánt",
                    "cuant",
                    "objeto",
                    "objetos",
                    "viendo",
                    "viend",
                    "mirando",
                    "miran",
                    "observ",
                    "vist",
                ]
            )
            or is_persona_q
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
                elif "tv" in low_q or "tele" in low_q:
                    target = next(
                        (a for a in last_atributos if a.get("cls") == "tv"), None
                    )
                elif is_persona_q:
                    target = next(
                        (a for a in last_atributos if a.get("cls") == "person"),
                        None,
                    )
                    if target is None:
                        return {"text": strip_grounding_leak("No veo personas ahora.")}
                    persons = [a for a in last_atributos if a.get("cls") == "person"]
                    if "cuánt" in low_q or "cuant" in low_q:
                        n_p = len(persons)
                        return {
                            "text": strip_grounding_leak(
                                f"Veo {n_p} persona{'s' if n_p != 1 else ''}."
                            )
                        }
                    n_persons = len(persons)
                    plural_p = "s" if n_persons != 1 else ""
                    return {
                        "text": strip_grounding_leak(
                            f"Sí, hay {n_persons} persona{plural_p} en cámara."
                        )
                    }
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
                                "text": strip_grounding_leak(
                                    f"A la izquierda de la taza está {_cls_es(str(a.get('cls')))} {a.get('color')} {a.get('tamano')}."  # noqa: E501
                                )
                            }
                        if "derecha" in low_q and right:
                            a = right[0]
                            return {
                                "text": strip_grounding_leak(
                                    f"A la derecha de la taza está {_cls_es(str(a.get('cls')))} {a.get('color')} {a.get('tamano')}."  # noqa: E501
                                )
                            }
                if target and "color" in low_q:
                    return {
                        "text": strip_grounding_leak(
                            f"La {_cls_es(str(target.get('cls')))} es {target.get('color')} tamaño {target.get('tamano')}."  # noqa: E501
                        )
                    }
                if (
                    "qué ves" in low_q
                    or "que ves" in low_q
                    or "qué hay" in low_q
                    or "que hay" in low_q
                    or "objeto" in low_q
                    or "objetos" in low_q
                    or "viendo" in low_q
                    or "viend" in low_q
                    or "mirando" in low_q
                    or "observ" in low_q
                    or "qué estás" in low_q
                    or "que estas" in low_q
                ):
                    descs = ", ".join(
                        [
                            f"{_cls_es(str(a.get('cls')))} {a.get('color')} {a.get('tamano')}"  # noqa: E501
                            for a in last_atributos[:4]
                        ]
                    )
                    n = len(last_atributos)
                    return {
                        "text": strip_grounding_leak(
                            f"Veo {n} objeto{'s' if n != 1 else ''}: {descs}."  # noqa: E501
                        )
                    }
                if target:
                    return {
                        "text": strip_grounding_leak(
                            f"Veo {_cls_es(str(target.get('cls')))} {target.get('color')} {target.get('tamano')}."  # noqa: E501
                        )
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
                    return {
                        "text": strip_grounding_leak(f"Buscando {', '.join(prompts)}.")
                    }
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

    # 0) Ollama local PRIMARIO (gratis/offline; docs 020-ollama-fallback).
    #    Env: OLLAMA_BASE_URL (default 127.0.0.1:11434/v1),
    #    OLLAMA_MODEL (default qwen2.5:1.5b). Default IPv4 explícita:
    #    `localhost` puede resolver a ::1 donde Docker Desktop hace relay
    #    a OTRO Ollama sin nuestros modelos. Si el daemon no está,
    #    falla rápido (connect) y sigue la cadena hospedada.
    ollama_base = (
        os.getenv("OLLAMA_BASE_URL", "").strip() or "http://127.0.0.1:11434/v1"
    )
    ollama_model = os.getenv("OLLAMA_MODEL", "").strip() or "qwen2.5:1.5b"
    # Conversación fluida: memoria multi-turno + system conciso es-AR.
    # Sin historial el contrato viejo (solo prompt) sigue idéntico.
    _system = (
        "Sos un asistente de voz en español rioplatense. "
        "Respondé corto (1-2 frases, máximo 60 palabras), "
        "conversacional, sin listas ni tecnicismos. "
        "Si hay percepción viva entre corchetes, usala; si no, no inventes objetos."
    )
    _hist: list[dict[str, str]] = []
    try:
        for t in req.historial or []:
            r = (t.role or "").strip().lower()
            c = (t.content or "").strip()
            if r not in ("user", "assistant") or not c:
                continue
            _hist.append({"role": r, "content": c[:500]})
        _hist = _hist[-6:]
    except Exception:
        _hist = []
    _messages: list[dict[str, str]] = [{"role": "system", "content": _system}]
    _messages.extend(_hist)
    _messages.append({"role": "user", "content": prompt_grounded})
    try:
        from openai import OpenAI

        _ollama = OpenAI(api_key="ollama", base_url=ollama_base)
        _resp = _ollama.chat.completions.create(
            model=ollama_model,
            messages=_messages,  # type: ignore[arg-type]
            timeout=10,
            temperature=0.6,
            max_tokens=150,
            extra_body={
                "options": {
                    "temperature": 0.6,
                    "num_predict": 120,
                    "num_ctx": 2048,
                },
                "keep_alive": "5m",
            },
        )
        _txt = (_resp.choices[0].message.content or "").strip()
        if _txt:
            return {"text": strip_grounding_leak(_txt)}
    except Exception as e:
        logger.warning("Ollama fallo: %s", e)

    # 1) Groq secundario (antes primario Ticket 021) — grounded
    if has_groq:
        try:
            modelo = os.getenv("GROQ_MODEL", "").strip() or gemini_client.MODELO_DEFECTO
            text = gemini_client.responder(prompt_grounded, modelo=modelo)
            if text.strip():
                return {"text": strip_grounding_leak(text)}
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
                    return {"text": strip_grounding_leak(text)}
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
            return {"text": strip_grounding_leak(text)}
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
                return {"text": strip_grounding_leak(txt)}
        except Exception as e:
            logger.warning("OpenAI fallback fallo: %s", e)

    # Mock final (mapa #130 G3): silencio total — el mock nunca afirma visión
    # ni devuelve el prefijo (era el leak de la captura). Las respuestas
    # deterministas con visión fresca ya salieron por atajos S3 arriba.
    # Excepción: saludo — no afirma visión, así que responde determinista
    # en vez de callar (conversación fluida sin cámara ni keys).
    if es_saludo:
        return {
            "text": "¡Hola! Te escucho. Si iniciás la cámara, te describo lo que ve."
        }
    # Fragmento/pregunta no clasificada CON visión fresca: describir lo que
    # se ve en vez de callar (el STT continuo suele entregar fragmentos como
    # "qué" de "qué ves"). G3 intacto: solo afirma datos frescos reales.
    if snapshot is not None and last_atributos:
        _n = len(last_atributos)
        _descs = ", ".join(
            f"{_cls_es(str(a.get('cls')))} {a.get('color')} {a.get('tamano')}"
            for a in last_atributos[:4]
        )
        return {
            "text": strip_grounding_leak(
                f"Veo {_n} objeto{'s' if _n != 1 else ''}: {_descs}."
            )
        }
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
