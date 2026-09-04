"""Tests grounding voz — gate de frescura + silencio G1/G3 (mapa #130 paso 1).

Sin cámara ni LLM: se llama a `VozHandler` directo (sin lifespan) con los
globales `ws.last_atributos/last_frame_id/last_ts` falsificados.
Criterio: pytest plataforma/webcam/tests/test_voz_grounding_noleak.py verde.
"""

from __future__ import annotations

import asyncio
import sys
import time
import types
from typing import Any

import pytest

from plataforma.webcam.backend import ws as ws_mod
from plataforma.webcam.backend.app import (
    VozHandler,
    VozRequest,
    strip_grounding_leak,
)


def _atributos() -> list[dict[str, Any]]:
    return [
        {
            "cls": "person",
            "color": "naranja",
            "tamano": "grande",
            "color_hsv_hex": "#67e22",
            "z_rel": None,
            "area": 0.2,
            "centroide": {"x_c": 0.5, "y_c": 0.5},
        }
    ]


def _fijar_percepcion(
    monkeypatch: pytest.MonkeyPatch, attrs: list[dict[str, Any]], age_ms: int
) -> None:
    now_ms = int(time.time() * 1000)
    monkeypatch.setattr(ws_mod, "last_atributos", attrs)
    monkeypatch.setattr(ws_mod, "last_frame_id", 72)
    monkeypatch.setattr(ws_mod, "last_ts", now_ms - age_ms)


def _sin_proveedores(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "GROQ_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "HF_TOKEN",
        "GROQ_MODEL",
        "GEMINI_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)


def _sin_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cadena LLM que falla rápido: sin sondas de red (hermético + veloz).

    `VozHandler` recarga `fase-1/.env` con `load_dotenv`, así que borrar env
    no alcanza: las keys reales vuelven y cada intento 403 quema segundos,
    envejeciendo el snapshot más allá del TTL entre asserts.
    """

    def _raise(*a: Any, **k: Any) -> Any:
        raise RuntimeError("sin red en tests")

    stub = types.SimpleNamespace(responder=_raise, MODELO_DEFECTO="stub")
    monkeypatch.setitem(sys.modules, "gemini_client", stub)

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            raise RuntimeError("sin red en tests")

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))


def _sin_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    """Solo la rama Ollama falla rápido (el resto de la cadena sigue real/stub).

    Para tests que verifican ramas hospedadas con el daemon Ollama vivo.
    """

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            raise RuntimeError("sin ollama en tests")

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))


def _taza() -> dict[str, Any]:
    return {
        "cls": "cup",
        "color": "roja",
        "tamano": "pequeño",
        "color_hsv_hex": "#aa2222",
        "z_rel": None,
        "area": 0.02,
        "centroide": {"x_c": 0.7, "y_c": 0.6},
    }


def _preguntar(
    prompt: str, historial: list[dict[str, str]] | None = None
) -> dict[str, str]:
    async def _inner() -> dict[str, str]:
        from plataforma.webcam.backend.app import TurnoHistorial

        turns = (
            [TurnoHistorial(role=t["role"], content=t["content"]) for t in historial]
            if historial
            else None
        )
        return await VozHandler(VozRequest(prompt=prompt, historial=turns))

    return asyncio.run(_inner())


def test_prompt_vacio_silencio(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    assert _preguntar("   ") == {"text": ""}


def test_sin_atributos_silencio(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_ollama(monkeypatch)
    _fijar_percepcion(monkeypatch, [], 100)
    assert _preguntar("¿qué ves?") == {"text": ""}


def test_stale_silencio_g1(monkeypatch: pytest.MonkeyPatch) -> None:
    # age 5000ms supera TTL 2000ms → la voz calla en preguntas visuales.
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 5000)
    assert _preguntar("¿qué ves?") == {"text": ""}


def test_stale_saludo_responde_sin_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    # El saludo no afirma visión: responde aunque la percepción esté vieja.
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 5000)
    text = _preguntar("hola, ¿cómo estás?")["text"]
    assert text.startswith("¡Hola!")
    _sin_veto(text)


def test_saludo_con_llm_no_niega_objetos(monkeypatch: pytest.MonkeyPatch) -> None:
    # Regresión captura: "cómo estás" con LLM disponible (Ollama vivo) no debe
    # negar visión. El saludo responde determinista sin pasar por el LLM.
    _fijar_percepcion(monkeypatch, _atributos(), 5000)

    class _Msg:
        content = "No veo objetos ahora."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, *a: Any, **k: Any) -> Any:
            return _Resp()

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        @property
        def chat(self) -> Any:
            return _Chat()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))
    text = _preguntar("cómo estás")["text"]
    assert "No veo objetos" not in text
    assert text.startswith("¡Hola!")
    _sin_veto(text)


def test_edad_captura_ahora_responde(monkeypatch: pytest.MonkeyPatch) -> None:
    # age 684ms (captura real CPU ~800ms/infer): con TTL 2000ms es fresca.
    _fijar_percepcion(monkeypatch, _atributos(), 684)
    text = _preguntar("¿qué ves?")["text"]
    assert text == "Veo 1 objeto: persona naranja grande."


def test_saludo_con_visual_pide_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    # "hola, ¿qué ves?" trae keyword visual → no es saludo puro: sin
    # percepción fresca calla igual que cualquier pregunta visual.
    _sin_proveedores(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 5000)
    assert _preguntar("hola, ¿qué ves?") == {"text": ""}


def test_fresco_color_q_responde_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    resp = _preguntar("¿qué ves?")
    assert resp["text"].startswith("Veo")


VETO_TOKENS = (
    "responde SOLO",
    "Instrucción grounding",
    "mock grounded",
    "Percepción viva",
    "frame #",
    "age ",
    "z:",
    "WORLD:",
)


def _sin_veto(text: str) -> None:
    for token in VETO_TOKENS:
        assert token not in text
    assert not any(f"#{h}" in text for h in ("67e22", "aa2222"))


def test_que_ves_natural_sin_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    text = _preguntar("¿qué ves?")["text"]
    assert text == "Veo 1 objeto: persona naranja grande."
    _sin_veto(text)


def test_que_ves_plural(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos() + [_taza()], 100)
    text = _preguntar("¿qué ves?")["text"]
    assert text == "Veo 2 objetos: persona naranja grande, taza roja pequeño."
    _sin_veto(text)


def test_color_taza_natural(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos() + [_taza()], 100)
    text = _preguntar("¿qué color tiene la taza?")["text"]
    assert text == "La taza es roja tamaño pequeño."
    _sin_veto(text)


def test_izquierda_taza_natural(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos() + [_taza()], 100)
    text = _preguntar("¿qué hay a la izquierda de la taza?")["text"]
    assert text == "A la izquierda de la taza está persona naranja grande."
    _sin_veto(text)


def test_quien_hay_persona(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    text = _preguntar("¿quién hay en cámara?")["text"]
    assert "persona" in text.lower()
    assert "hay 1 persona" in text.lower()
    _sin_veto(text)


def test_hay_alguien_sin_personas(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, [_taza()], 100)
    text = _preguntar("¿hay alguien ahí?")["text"]
    assert text == "No veo personas ahora."
    _sin_veto(text)


def test_que_hay_objetos_es(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos() + [_taza()], 100)
    text = _preguntar("¿qué hay?")["text"]
    assert text.startswith("Veo 2 objetos:")
    assert "persona" in text and "taza" in text
    _sin_veto(text)


def test_mock_silencio_total_g3(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sin proveedores el handler cae al mock: G3 manda silencio en lo visual,
    # jamás eco; el saludo responde determinista (no afirma visión).
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    assert _preguntar("hola")["text"].startswith("¡Hola!")
    assert _preguntar("¿quién sos?")["text"].startswith("¡Hola!")
    # Sin clasificar pero CON visión fresca: describe, no calla (G3 intacto).
    assert _preguntar("contame algo")["text"] == "Veo 1 objeto: persona naranja grande."


def test_fragmento_stt_describe_escena(monkeypatch: pytest.MonkeyPatch) -> None:
    # El STT continuo entrega fragmentos ("qué" de "qué ves"): con visión
    # fresca se describe la escena en vez de mandar "iniciá la cámara".
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 681)
    text = _preguntar("qué")["text"]
    assert text == "Veo 1 objeto: persona naranja grande."
    _sin_veto(text)


def test_sin_vision_y_sin_clasificar_calla(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sin visión fresca y sin saludo: silencio total aunque haya mock.
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 5000)
    assert _preguntar("contame algo") == {"text": ""}


def test_fragmento_ahora_stale_calla(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fragmento STT de 1 palabra ("ahora." de la captura) sin visión fresca:
    # silencio backend; el frontend pide cámara vía __SIN_CAMARA__.
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 5000)
    assert _preguntar("ahora.") == {"text": ""}


def test_ollama_primario_responde(monkeypatch: pytest.MonkeyPatch) -> None:
    # Rama 0 Ollama con cliente stub exitoso: responde LLM real-like con
    # grounding (prefijo inyectado pero sanitizado en salida).
    _fijar_percepcion(monkeypatch, _atributos(), 100)

    class _Msg:
        content = "Hola, veo que hay una persona."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, *a: Any, **k: Any) -> Any:
            return _Resp()

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        @property
        def chat(self) -> Any:
            return _Chat()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))
    text = _preguntar("contame algo interesante")["text"]
    assert "persona" in text
    _sin_veto(text)


def test_historial_multiturno_llega_a_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    # Conversación fluida: system + historial + user van en messages.
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    capturado: dict[str, Any] = {}

    class _Msg:
        content = "Claro, era roja."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, *a: Any, **k: Any) -> Any:
            capturado.update(k)
            return _Resp()

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        @property
        def chat(self) -> Any:
            return _Chat()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))
    text = _preguntar(
        "¿y su color?",
        historial=[
            {"role": "user", "content": "¿qué ves?"},
            {"role": "assistant", "content": "Veo una taza."},
        ],
    )["text"]
    assert "roja" in text.lower() or "claro" in text.lower()
    msgs = capturado.get("messages", [])
    assert msgs[0]["role"] == "system"
    assert any(m["content"] == "Veo una taza." for m in msgs)
    assert msgs[-1]["role"] == "user"
    assert capturado.get("timeout") == 10
    _sin_veto(text)


def test_sin_historial_compat_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    # Contrato viejo prompt-only: system + user, sin turnos intermedios.
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    capturado: dict[str, Any] = {}

    class _Msg:
        content = "Hola."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, *a: Any, **k: Any) -> Any:
            capturado.update(k)
            return _Resp()

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        @property
        def chat(self) -> Any:
            return _Chat()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))
    assert _preguntar("contame algo")["text"] == "Hola."
    msgs = capturado.get("messages", [])
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"


def test_strip_legitimo_intacto() -> None:
    text = "Veo 1 objeto: person naranja grande."
    assert strip_grounding_leak(text) == text
    # Idempotente.
    assert strip_grounding_leak(strip_grounding_leak(text)) == text


def test_strip_quita_eco_prefijo() -> None:
    eco = (
        "[Percepción viva frame #72 age 100ms: person naranja grande #67e22 z:?] "
        "Instrucción grounding: responde SOLO sobre lo que ves. "
        "Útil frame #72 (mock grounded)."
    )
    limpio = strip_grounding_leak(eco)
    _sin_veto(limpio)
    assert "Útil" in limpio


def _stub_gemini_eco(monkeypatch: pytest.MonkeyPatch, eco: str) -> None:
    def _responder(prompt: str, modelo: str = "") -> str:
        _ = (prompt, modelo)
        return eco

    stub = types.SimpleNamespace(responder=_responder, MODELO_DEFECTO="stub")
    monkeypatch.setitem(sys.modules, "gemini_client", stub)


def test_eco_llm_sanitizado(monkeypatch: pytest.MonkeyPatch) -> None:
    # Un proveedor que repite el prefijo no debe filtrarlo a la UI.
    _sin_ollama(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    _stub_gemini_eco(
        monkeypatch,
        "[Percepción viva frame #72 age 100ms: person naranja] "
        "Instrucción grounding: responde SOLO sobre lo que ves. "
        "Veo una persona frame #72 #67e22 z:? WORLD:cup (mock grounded).",
    )
    monkeypatch.setenv("GROQ_API_KEY", "test")
    for var in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "HF_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    # Prompt no-color para saltear atajos S3 y llegar a la cadena LLM.
    text = _preguntar("contame algo interesante")["text"]
    _sin_veto(text)
    assert "Veo una persona" in text


def test_saludo_con_objetos_pide_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    # "hola + objetos" es visual aunque empiece con saludo: sin frescura calla.
    from plataforma.webcam.backend.app import _es_saludo

    assert _es_saludo("hola, ¿qué objetos ves?") is False
    assert _es_saludo("hola, ¿qué ves?") is False
    assert _es_saludo("hola, ¿cómo estás?") is True
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 5000)
    assert _preguntar("hola, ¿qué objetos ves?") == {"text": ""}
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    assert _preguntar("objetos")["text"].startswith("Veo")


def test_ack_charla_no_repite_no_veo(monkeypatch: pytest.MonkeyPatch) -> None:
    # "perfecto" es charla (no afirma visión): jamás silencio G3,
    # con o sin percepción fresca. Fija el "repite lo mismo".
    from plataforma.webcam.backend.app import _es_charla

    assert _es_charla("perfecto") is True
    assert _es_charla("perfecto, ¿qué ves?") is False
    assert _es_charla("hola, ¿cómo estás?") is False
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    fresco = _preguntar("perfecto")["text"]
    assert fresco == "Entendido, te sigo escuchando."
    _sin_veto(fresco)
    _fijar_percepcion(monkeypatch, _atributos(), 5000)
    stale = _preguntar("perfecto")["text"]
    assert stale == "Entendido, te sigo escuchando."
    _sin_veto(stale)


def test_ack_charla_no_pasa_por_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    # qwen1.5b alucina "No veo objetos ahora" ante acuses pelados: el acuse
    # se cortocircuita determinista ANTES de la cadena LLM aunque haya
    # proveedor vivo (Docker ollama con modelo pulleado).
    _fijar_percepcion(monkeypatch, _atributos(), 5000)

    class _Msg:
        content = "No veo objetos ahora."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, *a: Any, **k: Any) -> Any:
            return _Resp()

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        @property
        def chat(self) -> Any:
            return _Chat()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))
    assert _preguntar("perfecto")["text"] == "Entendido, te sigo escuchando."
    assert _preguntar("dale")["text"] == "Entendido, te sigo escuchando."


def test_pregunta_visual_incluye_personas() -> None:
    from plataforma.webcam.backend.app import _es_pregunta_visual

    assert _es_pregunta_visual("¿quién hay en cámara?") is True
    assert _es_pregunta_visual("¿hay alguien ahí?") is True
    assert _es_pregunta_visual("¿ves a alguien?") is True
    assert _es_pregunta_visual("¿qué ves?") is True
    assert _es_pregunta_visual("contame algo") is False
    assert _es_pregunta_visual("¿y entonces qué hacemos?") is False


def test_charla_generica_stale_va_a_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fluidez: charla genérica sin cámara NO calla si hay LLM vivo —
    # va pelada al LLM sin afirmar visión (no repite "iniciá la cámara").
    _fijar_percepcion(monkeypatch, _atributos(), 5000)

    class _Msg:
        content = "Seguimos charlando, te escucho."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, *a: Any, **k: Any) -> Any:
            return _Resp()

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        @property
        def chat(self) -> Any:
            return _Chat()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))
    text = _preguntar("¿y entonces qué hacemos?")["text"]
    assert text == "Seguimos charlando, te escucho."


def test_visual_stale_silencia_aunque_haya_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # G3 intacto: pregunta visual sin frescura calla aunque haya LLM.
    _fijar_percepcion(monkeypatch, _atributos(), 5000)

    class _Msg:
        content = "Invento objetos."

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, *a: Any, **k: Any) -> Any:
            return _Resp()

    class _Chat:
        def __init__(self) -> None:
            self.completions = _Completions()

    class _OpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        @property
        def chat(self) -> Any:
            return _Chat()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=_OpenAI))
    assert _preguntar("¿qué ves?") == {"text": ""}
    assert _preguntar("¿hay alguien ahí?") == {"text": ""}


def test_viendo_ahora_es_visual() -> None:
    from plataforma.webcam.backend.app import _es_pregunta_visual

    assert _es_pregunta_visual("qué estás viendo ahora") is True
    assert _es_pregunta_visual("¿qué estás mirando?") is True
    assert _es_pregunta_visual("¿qué observás?") is True


def test_viendo_ahora_fresco_describe(monkeypatch: pytest.MonkeyPatch) -> None:
    # Captura: "qué estás viendo ahora" con visión fresca describe
    # determinista S3 en vez de caer al LLM ("No veo objetos ahora").
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    text = _preguntar("qué estás viendo ahora")["text"]
    assert text == "Veo 1 objeto: persona naranja grande."
    _sin_veto(text)


def test_viendo_ahora_stale_calla(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sin frescura: silencio G3 (el frontend pide cámara vía __SIN_CAMARA__).
    _sin_proveedores(monkeypatch)
    _sin_red(monkeypatch)
    _fijar_percepcion(monkeypatch, _atributos(), 5000)
    assert _preguntar("qué estás viendo ahora") == {"text": ""}
