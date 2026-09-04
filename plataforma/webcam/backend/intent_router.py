"""Router de intenciones voz — fast-path determinista sin LLM.

Extraído de `app.py` (VozHandler): clasifica el prompt en
saludo / charla / pregunta visual / meta-modelo con regex precompiladas
(búsqueda lineal en C, escala al crecer el catálogo).

Nota grounding: el keyword pelado "hay" NO es visual — "hay algún modelo
de llm funcionando" es meta-pregunta sobre el modelo, no sobre la escena
(reportaba loop "No veo objetos ahora" sin cámara). Personas ("hay gente",
"hay alguien", "quién hay") siguen siendo visual vía _PERSONA.
"""

from __future__ import annotations

import re

# Saludo/smalltalk que NO afirma nada visual: no requiere percepción fresca.
_SALUDO_KEYWORDS: tuple[str, ...] = (
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
# Sin "hay" pelado: solo cuenta en frases de escena/persona (ver _PERSONA).
_VISION_KEYWORDS: tuple[str, ...] = (
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
    "muest",
    "enseñ",
    "ensen",
)


# Acuse conversacional que NO afirma nada visual (perfecto, genial, dale):
# como el saludo, pasa sin cámara para no repetir "No veo objetos".
_CHARLA_KEYWORDS: tuple[str, ...] = (
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

# Pregunta que SÍ afirma visión (requiere percepción fresca; sin ella G3 calla).
# Incluye personas: "¿quién hay?", "¿ves a alguien?", "¿hay gente?".
_PERSONA_KEYWORDS: tuple[str, ...] = (
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

# Meta-pregunta sobre el modelo mismo (no sobre la escena): responde
# determinista con el estado de proveedores, sin cámara y sin LLM.
_META_KEYWORDS: tuple[str, ...] = (
    "qué modelo",
    "que modelo",
    "qué llm",
    "que llm",
    "qué motor",
    "que motor",
    "qué versión",
    "que version",
    "proveedor",
    "con qué hablo",
    "con que hablo",
    "modelo",
    "modelos",
    "llm",
)


def _compilar(keywords: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile("|".join(re.escape(k) for k in keywords))


_SALUDO_RE = _compilar(_SALUDO_KEYWORDS)
_VISION_RE = _compilar(_VISION_KEYWORDS)
_CHARLA_RE = _compilar(_CHARLA_KEYWORDS)
_PERSONA_RE = _compilar(_PERSONA_KEYWORDS)
_META_RE = _compilar(_META_KEYWORDS)


def _es_saludo(prompt: str) -> bool:
    """True si es smalltalk sin afirmación visual (no necesita cámara)."""
    low = prompt.lower()
    if not _SALUDO_RE.search(low):
        return False
    return _VISION_RE.search(low) is None


def _es_charla(prompt: str) -> bool:
    """True si es acuse sin afirmación visual (no necesita cámara)."""
    low = prompt.lower()
    if not _CHARLA_RE.search(low):
        return False
    return _VISION_RE.search(low) is None


def _es_pregunta_visual(prompt: str) -> bool:
    """True si el prompt pide visión (objetos o personas)."""
    low = prompt.lower()
    if _VISION_RE.search(low):
        return True
    return _PERSONA_RE.search(low) is not None


def _es_meta_modelo(prompt: str) -> bool:
    """True si pregunta por el modelo mismo (qué LLM está vivo)."""
    return _META_RE.search(prompt.lower()) is not None
