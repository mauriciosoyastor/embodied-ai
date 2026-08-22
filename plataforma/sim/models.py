"""Contrato sim → backend — Pydantic models SI / world-frame."""

from pydantic import BaseModel, Field


class SimObservation(BaseModel):
    """Estado del mundo que todo sim expone (SI, world-frame)."""

    x: float = Field(description="posición x [m] world-frame")
    y: float = Field(description="posición y [m] world-frame")
    yaw: float = Field(description="yaw [rad] world-frame")
    v_x: float = Field(description="vel lineal x [m/s]")
    v_y: float = Field(
        default=0.0, description="vel lineal y [m/s] — 0 para diferencial"
    )
    omega_z: float = Field(description="vel angular z [rad/s]")
    ts: float = Field(description="unix ms simulado")
    frame_id: int = Field(description="contador de frames obs")
    # sensores opcionales podrían añadirse luego


class CmdVel(BaseModel):
    """Comando velocidad (v_x, omega_z) con clamp — conversión a ruedas interna."""

    v_x: float = Field(ge=-1.0, le=1.0, description="vel lineal [m/s] clamp ±1.0")
    omega_z: float = Field(
        ge=-1.5, le=1.5, description="vel angular [rad/s] clamp ±1.5"
    )


class SimMetrics(BaseModel):
    """Métricas motor sim — consume recomendador, no FSM."""

    steps: int = Field(description="steps simulados acumulados")
    wall_time_ms: float = Field(description="wall time acumulado [ms]")
    dt_ms: float = Field(description="dt real vs sim último step [ms]")
    steps_per_s: float = Field(description="steps/s estimado")
