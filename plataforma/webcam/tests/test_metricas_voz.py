"""Observabilidad de enrutamiento voz — Fast-Path vs Slow-Path (Prometheus)."""

from __future__ import annotations

from plataforma.webcam.backend.metrics import (
    record_voz_fast,
    record_voz_slow,
    render_prometheus,
    reset,
)


def test_contadores_fast_slow_y_render() -> None:
    reset()
    record_voz_fast("saludo")
    record_voz_fast("saludo")
    record_voz_fast("meta")
    record_voz_slow("groq")
    record_voz_slow("ollama")
    body = render_prometheus()
    assert 'voz_fast_path_total{intent="saludo"} 2' in body
    assert 'voz_fast_path_total{intent="meta"} 1' in body
    assert 'voz_slow_path_total{proveedor="groq"} 1' in body
    assert 'voz_slow_path_total{proveedor="ollama"} 1' in body
    assert "voz_offline_mode" in body
    reset()
    body2 = render_prometheus()
    assert 'voz_fast_path_total{intent="saludo"} 0' in body2


def test_saludo_cuenta_fast_path(monkeypatch: object) -> None:
    # El fast-path determinista deja huella (ahorro tokens/latencia).
    import pytest

    assert isinstance(monkeypatch, pytest.MonkeyPatch)
    reset()
    import asyncio

    from plataforma.webcam.backend import ws as ws_mod
    from plataforma.webcam.backend.app import VozHandler, VozRequest

    async def _inner() -> dict[str, str]:
        return await VozHandler(VozRequest(prompt="hola, ¿cómo estás?"))

    monkeypatch.setattr(ws_mod, "last_atributos", [])
    monkeypatch.setattr(ws_mod, "last_frame_id", 0)
    monkeypatch.setattr(ws_mod, "last_ts", 0)
    assert asyncio.run(_inner())["text"].startswith("¡Hola!")
    assert 'voz_fast_path_total{intent="saludo"} 1' in render_prometheus()
    reset()
