"""Tests de gemini_client sin red ni API key real (todo mockeado)."""

from unittest.mock import Mock

import gemini_client
import pytest


def test_cargar_clave_levanta_sin_clave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini_client, "load_dotenv", lambda: False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        gemini_client.cargar_clave()


def test_cargar_clave_devuelve_el_valor_del_entorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini_client, "load_dotenv", lambda: False)
    monkeypatch.setenv("GOOGLE_API_KEY", "clave-de-prueba")
    assert gemini_client.cargar_clave() == "clave-de-prueba"


def test_responder_usa_cliente_y_devuelve_texto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respuesta = Mock()
    respuesta.text = "Hola, mundo"
    cliente = Mock()
    cliente.models.generate_content.return_value = respuesta
    monkeypatch.setattr(gemini_client, "crear_cliente", lambda: cliente)

    assert gemini_client.responder("hola") == "Hola, mundo"
    cliente.models.generate_content.assert_called_once_with(
        model=gemini_client.MODELO_DEFECTO,
        contents="hola",
    )


def test_responder_devuelve_vacio_si_no_hay_texto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respuesta = Mock()
    respuesta.text = None
    cliente = Mock()
    cliente.models.generate_content.return_value = respuesta
    monkeypatch.setattr(gemini_client, "crear_cliente", lambda: cliente)

    assert gemini_client.responder("hola") == ""
