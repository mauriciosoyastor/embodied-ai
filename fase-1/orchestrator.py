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
    percepcion: list[dict] | None = None,
) -> Agent[HardwareContext, DecisionAgentica]:
    """Modelo por defecto: Muse Spark 1.2 free (Cursor) vía OpenAI-compatible API.
    Requiere OPENCODE_API_KEY/CURSOR_API_KEY/OPENAI_API_KEY en .env.
    Legacy: google:gemini-1.5-flash sigue soportado si se pasa explícito.
    percepcion: lista de AtributoVista (track_id, cls, color_hsv_hex, z_rel, is_world)
    para grounding Grammar-Constrained (harness plan.voz-grounded).
    """
    """Crea y configura el agente orquestador con Pydantic AI."""
    percepcion_txt = ""
    if percepcion:
        descs = []
        for a in percepcion[:4]:
            descs.append(
                f"{a.get('cls')} {a.get('color', '?')} {a.get('tamano', '?')} "
                f"hex:{a.get('color_hsv_hex', '?')} z:{a.get('z_rel') or '?'} "
                f"{'WORLD:' + str(a.get('prompt_origen')) if a.get('is_world') else ''}"
            )
        percepcion_txt = f" | Percepción viva frame:[{', '.join(descs)}]"
    agent = Agent(
        modelo,
        deps_type=HardwareContext,
        output_type=DecisionAgentica,
        system_prompt=(
            "Eres el orquestador cognitivo central de un sistema de Embodied AI. "
            "Toma decisiones de control basadas en el estado del "
            "hardware proporcionado. "
            "REGLA GROUNDING: Responde SOLO sobre la Percepción viva provista. "
            "Si no hay percepción fresh, di 'No veo objetos ahora'. "
            "Prohibido hallucinar productos, precios o sitios Walmart/Best Buy."
            + percepcion_txt
        ),
    )

    @agent.system_prompt
    def incluir_contexto_hardware(ctx: RunContext[HardwareContext]) -> str:
        return (
            f"[Telemetría] Sensor activo: {ctx.deps.sensor_activo}, "
            f"Nivel de batería: {ctx.deps.bateria_nivel}%." + percepcion_txt
        )

    return agent
