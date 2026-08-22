"""Orquestador cognitivo local usando Pydantic AI e inyección de dependencias.

Permite estructurar decisiones de agentes corpóreos y simular (mock)
el hardware mediante contextos inyectados.
"""

from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


@dataclass
class HardwareContext:
    """Contexto de hardware inyectado al orquestador."""

    sensor_activo: bool
    bateria_nivel: float


class DecisionAgentica(BaseModel):
    """Esquema de salida estructurado (Grammar-Constrained Decoding)."""

    accion: str = Field(
        ...,
        description=(
            "Acción a realizar por el robot (ej. 'avanzar', 'detener', 'girar')"
        ),
    )
    razon: str = Field(..., description="Justificación técnica basada en el contexto")
    nivel_confianza: float = Field(
        ..., ge=0.0, le=1.0, description="Confianza en la decisión"
    )


def crear_orquestador(
    modelo: str = "openai:opencode/muse-spark-1.2-contributor-free",
) -> Agent[HardwareContext, DecisionAgentica]:
    """Modelo por defecto: Muse Spark 1.2 free (Cursor) vía OpenAI-compatible API.
    Requiere OPENCODE_API_KEY/CURSOR_API_KEY/OPENAI_API_KEY en .env.
    Legacy: google:gemini-1.5-flash sigue soportado si se pasa explícito.
    """
    """Crea y configura el agente orquestador con Pydantic AI."""
    agent = Agent(
        modelo,
        deps_type=HardwareContext,
        output_type=DecisionAgentica,
        system_prompt=(
            "Eres el orquestador cognitivo central de un sistema de Embodied AI. "
            "Toma decisiones de control basadas en el estado del "
            "hardware proporcionado."
        ),
    )

    @agent.system_prompt
    def incluir_contexto_hardware(ctx: RunContext[HardwareContext]) -> str:
        return (
            f"[Telemetría] Sensor activo: {ctx.deps.sensor_activo}, "
            f"Nivel de batería: {ctx.deps.bateria_nivel}%."
        )

    return agent
