"""Cliente para Gemini (Google AI Studio) vía API key.

Lee la clave desde ``.env`` (``GOOGLE_API_KEY``) y expone una función
simple de texto a texto. Es el primer ladrillo del orquestador cognitivo
de la Fase 1.
"""

import os

from dotenv import load_dotenv
from google import genai

MODELO_DEFECTO = "gemini-3.6-flash"


def cargar_clave() -> str:
    """Devuelve la API key desde el entorno o ``.env``."""
    load_dotenv()
    clave = os.getenv("GOOGLE_API_KEY", "").strip()
    if not clave:
        raise ValueError("Falta GOOGLE_API_KEY en .env o en el entorno")
    return clave


def crear_cliente() -> genai.Client:
    return genai.Client(api_key=cargar_clave())


def responder(prompt: str, modelo: str = MODELO_DEFECTO) -> str:
    """Consulta a Gemini y devuelve el texto generado."""
    cliente = crear_cliente()
    respuesta = cliente.models.generate_content(model=modelo, contents=prompt)
    return respuesta.text or ""
