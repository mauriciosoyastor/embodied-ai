"""Tests unitarios para el orquestador cognitivo de la Fase 1 usando Pydantic AI.

Verifica la inyección de dependencias y el decodificador restringido (TestModel).
"""

import pytest
from orchestrator import DecisionAgentica, HardwareContext, crear_orquestador
from pydantic_ai.models.test import TestModel


def test_orquestador_decision_exitosa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica que el agente devuelva un esquema DecisionAgentica

    válido usando TestModel.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-key")
    agent = crear_orquestador()

    # Usamos TestModel para simular la respuesta estructurada sin llamadas de red
    custom_output = DecisionAgentica(
        accion="avanzar",
        razon="Sensor activo y batería óptima.",
        nivel_confianza=0.95,
    )

    with agent.override(model=TestModel(custom_output_args=custom_output)):
        deps = HardwareContext(sensor_activo=True, bateria_nivel=90.0)
        resultado = agent.run_sync("Evaluar entorno operativo", deps=deps)

        assert isinstance(resultado.output, DecisionAgentica)
        assert resultado.output.accion == "avanzar"
        assert resultado.output.nivel_confianza == 0.95
        assert resultado.output.razon == "Sensor activo y batería óptima."
