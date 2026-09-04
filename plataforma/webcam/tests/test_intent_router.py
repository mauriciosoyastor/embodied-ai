"""Router de intenciones voz — paridad con app.py + fix 'hay' pelado.

El bug: "hay algún modelo de llm funcionando" caía como pregunta
visual (keyword "hay") y sin cámara terminaba en "No veo objetos".
"""

from plataforma.webcam.backend.intent_router import (
    _es_charla,
    _es_meta_modelo,
    _es_pregunta_visual,
    _es_saludo,
)


def test_saludo_paridad() -> None:
    assert _es_saludo("hola, ¿qué objetos ves?") is False
    assert _es_saludo("hola, ¿qué ves?") is False
    assert _es_saludo("hola, ¿cómo estás?") is True


def test_charla_paridad() -> None:
    assert _es_charla("perfecto") is True
    assert _es_charla("perfecto, ¿qué ves?") is False
    assert _es_charla("hola, ¿cómo estás?") is False


def test_visual_paridad_personas() -> None:
    assert _es_pregunta_visual("¿quién hay en cámara?") is True
    assert _es_pregunta_visual("¿hay alguien ahí?") is True
    assert _es_pregunta_visual("¿ves a alguien?") is True
    assert _es_pregunta_visual("¿qué ves?") is True
    assert _es_pregunta_visual("contame algo") is False
    assert _es_pregunta_visual("¿y entonces qué hacemos?") is False


def test_hay_pelado_no_es_visual() -> None:
    # Reporte captura: pregunta meta sobre el modelo, no sobre la escena.
    assert _es_pregunta_visual("hay algún modelo de llm que esté funcionando") is False
    assert _es_pregunta_visual("¿hay wifi acá?") is False
    # ...pero personas siguen siendo visual:
    assert _es_pregunta_visual("¿hay gente?") is True
    assert _es_pregunta_visual("¿hay alguien ahí?") is True


def test_meta_modelo() -> None:
    assert _es_meta_modelo("hay algún modelo de llm que esté funcionando") is True
    assert _es_meta_modelo("¿qué modelo sos?") is True
    assert _es_meta_modelo("con qué llm hablo") is True
    assert _es_meta_modelo("¿qué ves?") is False
    assert _es_meta_modelo("hola, ¿cómo estás?") is False
    assert _es_meta_modelo("perfecto") is False
