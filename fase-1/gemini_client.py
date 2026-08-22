"""Cliente LLM — Muse Spark 1.2 (Cursor free) por defecto, fallback Gemini.

Lee la clave desde ``.env`` y expone ``responder`` texto-a-texto.
Soporta dos proveedores:
- Muse Spark 1.2 free (opencode/muse-spark-1.2-contributor-free)
  vía OpenAI-compatible API
- Gemini (google) vía google-genai — compatibilidad legacy
"""

import os
from pathlib import Path

from dotenv import load_dotenv

MODELO_DEFECTO = "opencode/muse-spark-1.2-contributor-free"
# Alias Cursor free — mismo modelo, ID corto para DX
MODELO_CURSOR_FREE = "muse-spark-1.2-free"
MODELO_GEMINI_LEGACY = "gemini-3.6-flash"


def _es_muse_spark(modelo: str) -> bool:
    m = modelo.lower()
    return "muse-spark" in m or "opencode" in m or "cursor" in m


def cargar_clave(modelo: str | None = None) -> str:
    """Devuelve la API key según proveedor."""
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    load_dotenv()
    # Muse Spark / Cursor / OpenCode
    for key in ("OPENCODE_API_KEY", "CURSOR_API_KEY", "OPENAI_API_KEY"):
        val = os.getenv(key, "").strip()
        if val:
            return val
    # Fallback Gemini
    clave = os.getenv("GOOGLE_API_KEY", "").strip()
    if clave:
        return clave
    # Si no hay ninguna, error con hint
    raise ValueError(
        "Falta API key: define OPENCODE_API_KEY/CURSOR_API_KEY/OPENAI_API_KEY "
        "para Muse Spark, o GOOGLE_API_KEY para Gemini en .env"
    )


def crear_cliente():  # type: ignore[no-untyped-def]
    """Crea cliente Google (legacy) — para compatibilidad tests."""
    from google import genai

    return genai.Client(api_key=cargar_clave())


def crear_cliente_openai():  # type: ignore[no-untyped-def]
    """Crea cliente OpenAI-compatible para Muse Spark."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("Falta 'openai' — instala con pip install openai") from exc
    api_key = cargar_clave()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def responder(prompt: str, modelo: str = MODELO_DEFECTO) -> str:
    """Consulta al LLM y devuelve texto. Despacha según prefijo del modelo."""
    if _es_muse_spark(modelo):
        cliente = crear_cliente_openai()
        # Normaliza alias corto al ID completo
        model_id = (
            MODELO_DEFECTO
            if modelo in (MODELO_CURSOR_FREE, "muse-spark-1.2")
            else modelo
        )
        resp = cliente.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()
    # Ruta Gemini legacy
    from google import (
        genai,  # lazy para no exigir google-genai si solo se usa Muse Spark
    )

    _ = genai  # suppress unused
    cliente = crear_cliente()
    respuesta = cliente.models.generate_content(model=modelo, contents=prompt)
    return respuesta.text or ""
