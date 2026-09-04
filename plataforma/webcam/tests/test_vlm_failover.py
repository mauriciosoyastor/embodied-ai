"""VLM failover — scout primario, qwen Groq ante 429/503, luego HF/Gemini/mock."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from plataforma.webcam.backend.inference.vlm import VLMClient


def _fake_openai(
    monkeypatch: pytest.MonkeyPatch, comportamiento: dict[str, str]
) -> None:
    """Fake OpenAI: por modelo devuelve texto o levanta RuntimeError."""

    class _Msg:
        def __init__(self, content: str) -> None:
            self.content = content

    class _Choice:
        def __init__(self, content: str) -> None:
            self.message = _Msg(content)

    class _Resp:
        def __init__(self, content: str) -> None:
            self.choices = [_Choice(content)]

    class _Completions:
        def create(self, *a: Any, **k: Any) -> Any:
            model = str(k.get("model", ""))
            for prefijo, salida in comportamiento.items():
                if prefijo in model:
                    if salida == "RAISE_429":
                        raise RuntimeError("429 Too Many Requests")
                    return _Resp(salida)
            raise RuntimeError(f"modelo no stubbeado: {model}")

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


def test_vlm_scout_primario_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test")
    for var in ("HF_TOKEN", "GOOGLE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    _fake_openai(monkeypatch, {"scout": "Una taza roja sobre la mesa."})
    leyenda = VLMClient().caption(objects=["taza"])
    assert leyenda.provider == "groq"
    assert "taza" in leyenda.caption


def test_vlm_fallback_qwen_ante_429(monkeypatch: pytest.MonkeyPatch) -> None:
    # scout 429 → qwen Groq (mismo base_url/key) antes de HF.
    monkeypatch.setenv("GROQ_API_KEY", "test")
    for var in ("HF_TOKEN", "GOOGLE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    _fake_openai(monkeypatch, {"scout": "RAISE_429", "qwen": "Taza roja en mesa."})
    leyenda = VLMClient().caption(objects=["taza"])
    assert leyenda.provider == "groq-fallback"
    assert "Taza" in leyenda.caption


def test_vlm_mock_sin_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("GROQ_API_KEY", "HF_TOKEN", "GOOGLE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    leyenda = VLMClient().caption(objects=["taza"])
    assert leyenda.provider == "mock"
