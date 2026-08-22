"""Tests de gemini_client sin red ni API key real (todo mockeado)."""

from unittest.mock import Mock

import gemini_client
import pytest


def test_cargar_clave_levanta_sin_clave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini_client, "load_dotenv", lambda **kwargs: False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        gemini_client.cargar_clave()


def test_cargar_clave_devuelve_el_valor_del_entorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini_client, "load_dotenv", lambda **kwargs: False)
    monkeypatch.setenv("GOOGLE_API_KEY", "clave-de-prueba")
    assert gemini_client.cargar_clave() == "clave-de-prueba"


def test_responder_usa_cliente_y_devuelve_texto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Muse Spark ruta (default) — mock OpenAI
    mock_choice = Mock()
    mock_choice.message.content = "Hola, mundo"
    mock_resp = Mock()
    mock_resp.choices = [mock_choice]
    cliente = Mock()
    cliente.chat.completions.create.return_value = mock_resp
    monkeypatch.setattr(gemini_client, "crear_cliente_openai", lambda: cliente)

    assert gemini_client.responder("hola") == "Hola, mundo"
    cliente.chat.completions.create.assert_called_once()
    assert (
        cliente.chat.completions.create.call_args.kwargs["model"]
        == gemini_client.MODELO_DEFECTO
    )


def test_responder_devuelve_vacio_si_no_hay_texto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_choice = Mock()
    mock_choice.message.content = None
    mock_resp = Mock()
    mock_resp.choices = [mock_choice]
    cliente = Mock()
    cliente.chat.completions.create.return_value = mock_resp
    monkeypatch.setattr(gemini_client, "crear_cliente_openai", lambda: cliente)

    assert gemini_client.responder("hola") == ""


def test_responder_gemini_legacy_usa_google(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respuesta = Mock()
    respuesta.text = "Hola Gemini"
    cliente = Mock()
    cliente.models.generate_content.return_value = respuesta
    monkeypatch.setattr(gemini_client, "crear_cliente", lambda: cliente)

    assert gemini_client.responder("hola", modelo="gemini-1.5-flash") == "Hola Gemini"
    cliente.models.generate_content.assert_called_once_with(
        model="gemini-1.5-flash",
        contents="hola",
    )
