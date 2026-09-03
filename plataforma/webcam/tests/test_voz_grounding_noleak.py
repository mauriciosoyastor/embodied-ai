"""Tests grounding voz — gate de frescura + silencio G1/G3 (mapa #130 paso 1).

Sin cámara ni LLM: se llama a `VozHandler` directo (sin lifespan) con los
globales `ws.last_atributos/last_frame_id/last_ts` falsificados.
Criterio: pytest plataforma/webcam/tests/test_voz_grounding_noleak.py verde.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from plataforma.webcam.backend import ws as ws_mod
from plataforma.webcam.backend.app import VozHandler, VozRequest


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


def _preguntar(prompt: str) -> dict[str, str]:
    async def _inner() -> dict[str, str]:
        return await VozHandler(VozRequest(prompt=prompt))

    return asyncio.run(_inner())


def test_prompt_vacio_silencio(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    assert _preguntar("   ") == {"text": ""}


def test_sin_atributos_silencio(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, [], 100)
    assert _preguntar("¿qué ves?") == {"text": ""}


def test_stale_silencio_g1(monkeypatch: pytest.MonkeyPatch) -> None:
    # age 1699ms (captura) supera TTL 200ms → la voz calla aunque haya datos.
    _fijar_percepcion(monkeypatch, _atributos(), 1699)
    assert _preguntar("¿qué ves?") == {"text": ""}
    assert _preguntar("hola") == {"text": ""}


def test_fresco_color_q_responde_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    _fijar_percepcion(monkeypatch, _atributos(), 100)
    resp = _preguntar("¿qué ves?")
    assert resp["text"].startswith("Veo")
