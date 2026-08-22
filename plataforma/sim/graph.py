"""StateGraph sim — Tick→HandleGesto→Decision→Act (012).

Implementa 009 (4 estados SIM_*) + 010 (WhiteboardState) + 012 (10Hz, WS same, Deadman).
Usa pydantic_graph BaseNode para tipado pero orquestación manual simple (evita builder).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_graph import BaseNode, End, GraphRunContext

from plataforma.sim.fake_adapter import FakeAdapter
from plataforma.sim.models import CmdVel
from plataforma.sim.state import MissionState
from plataforma.sim.whiteboard import WhiteboardState

# ---- DecisionAgentica import (fase-1) con fallback stub ----
try:
    sys.path.insert(0, "fase-1")
    from orchestrator import DecisionAgentica  # type: ignore[import-not-found]
except ImportError:

    class DecisionAgentica(BaseModel):  # type: ignore[no-redef]
        accion: str
        razon: str
        nivel_confianza: float


# ---- Deps inyectadas al graph ----
@dataclass
class SimDeps:
    adapter: FakeAdapter
    hyst_last: str | None = None
    hyst_count: int = 0
    deadman_ticks: int = 0


# ---- Helpers histéresis (espejo fsm.py:68) ----
HYSTERESIS_N = 5
CONF_THRESHOLD = 0.7


def _apply_gesto(state: MissionState, deps: SimDeps) -> None:
    wb: WhiteboardState = state.whiteboard
    gesto = wb.last_gesto
    if gesto is None:
        deps.hyst_last = None
        deps.hyst_count = 0
        return
    if gesto.label == "none" or gesto.conf < CONF_THRESHOLD:
        deps.hyst_last = None
        deps.hyst_count = 0
        return
    if wb.estado == "SIM_ABORTED":
        if gesto.label == deps.hyst_last:
            deps.hyst_count += 1
        else:
            deps.hyst_last = gesto.label
            deps.hyst_count = 1
        return
    if gesto.label == deps.hyst_last:
        deps.hyst_count += 1
    else:
        deps.hyst_last = gesto.label
        deps.hyst_count = 1
    if deps.hyst_count < HYSTERESIS_N:
        return
    if gesto.label == "fist":
        wb.estado = "SIM_ABORTED"
    elif gesto.label == "open_palm":
        wb.estado = "SIM_PAUSED"
    elif gesto.label == "thumbs_up":
        wb.estado = "SIM_RUNNING"
    deps.hyst_last = None
    deps.hyst_count = 0


def _decide_to_cmd(decision: DecisionAgentica | None) -> CmdVel:
    if decision is None:
        return CmdVel(v_x=0.0, omega_z=0.0)
    a = decision.accion.lower()
    if a in ("avanzar", "adelante", "forward"):
        return CmdVel(v_x=0.5, omega_z=0.0)
    if a in ("girar", "rotar", "turn"):
        return CmdVel(v_x=0.2, omega_z=0.8)
    if a in ("detener", "stop", "pausa"):
        return CmdVel(v_x=0.0, omega_z=0.0)
    if decision.nivel_confianza >= 0.6:
        return CmdVel(v_x=0.3, omega_z=0.0)
    return CmdVel(v_x=0.0, omega_z=0.0)


# ---- Nodos ----
class TickNode(BaseNode[MissionState, SimDeps, str]):
    """Avanza frame_id siempre (012 Q1 10Hz)."""

    async def run(self, ctx: GraphRunContext[MissionState, SimDeps]) -> HandleGestoNode:
        ctx.state.whiteboard.frame_id += 1
        return HandleGestoNode()


class HandleGestoNode(BaseNode[MissionState, SimDeps, str]):
    async def run(
        self, ctx: GraphRunContext[MissionState, SimDeps]
    ) -> DecisionNode | ActNode | End[str]:
        _apply_gesto(ctx.state, ctx.deps)
        wb = ctx.state.whiteboard
        if wb.estado == "SIM_ABORTED":
            return End(data="ABORTED")
        if wb.estado == "SIM_RUNNING":
            return DecisionNode()
        return ActNode()


class DecisionNode(BaseNode[MissionState, SimDeps, str]):
    """Solo si SIM_RUNNING — híbrido FSM-gated (009 Q3)."""

    async def run(
        self, ctx: GraphRunContext[MissionState, SimDeps]
    ) -> ActNode | End[str]:
        wb = ctx.state.whiteboard
        if wb.estado != "SIM_RUNNING":
            return ActNode()
        if wb.last_decision is None:
            wb.last_decision = DecisionAgentica(
                accion="avanzar", razon="fallback headless", nivel_confianza=0.8
            )
        return ActNode()


class ActNode(BaseNode[MissionState, SimDeps, str]):
    """Envía CmdVel a FakeAdapter, step 100ms, actualiza Whiteboard (012 Q3)."""

    async def run(self, ctx: GraphRunContext[MissionState, SimDeps]) -> End[str]:
        wb = ctx.state.whiteboard
        deps = ctx.deps
        if wb.last_gesto is None or wb.last_gesto.label == "none":
            deps.deadman_ticks += 1
        else:
            deps.deadman_ticks = 0
        if deps.deadman_ticks >= 5:
            cmd = CmdVel(v_x=0.0, omega_z=0.0)
        elif wb.estado == "SIM_ABORTED":
            cmd = CmdVel(v_x=0.0, omega_z=0.0)
        elif wb.estado in ("SIM_IDLE", "SIM_PAUSED"):
            cmd = CmdVel(v_x=0.0, omega_z=0.0)
        else:
            cmd = _decide_to_cmd(wb.last_decision)
        deps.adapter.send_cmd_vel(cmd)
        obs = deps.adapter.step(dt_ms=100.0)
        wb.last_observation = obs
        wb.metrics = deps.adapter.get_metrics()
        return End(data=wb.estado)


# ---- Graph manual (sin GraphBuilder) ----
@dataclass
class GraphRunResult:
    output: str
    state: MissionState


class SimGraph:
    """Orquestador manual que ejecuta Tick→Handle→Decision→Act."""

    def render(self, direction: str = "LR") -> str:  # noqa: ARG002
        return (
            "stateDiagram-v2\n"
            "  [*] --> TickNode\n"
            "  TickNode --> HandleGestoNode\n"
            "  HandleGestoNode --> DecisionNode: SIM_RUNNING\n"
            "  HandleGestoNode --> ActNode: IDLE/PAUSED\n"
            "  HandleGestoNode --> [*]: ABORTED\n"
            "  DecisionNode --> ActNode\n"
            "  ActNode --> [*]\n"
        )

    async def run(self, state: MissionState, deps: SimDeps) -> GraphRunResult:
        # Tick
        tick = TickNode()
        ctx_tick = GraphRunContext(state=state, deps=deps)
        nxt = await tick.run(ctx_tick)
        # HandleGesto
        ctx_h = GraphRunContext(state=state, deps=deps)
        nxt2 = await nxt.run(ctx_h)  # type: ignore[union-attr]
        if isinstance(nxt2, End):
            return GraphRunResult(output=nxt2.data, state=state)
        # Decision or Act
        ctx_d = GraphRunContext(state=state, deps=deps)
        nxt3 = await nxt2.run(ctx_d)  # type: ignore[union-attr]
        if isinstance(nxt3, End):
            return GraphRunResult(output=nxt3.data, state=state)
        ctx_a = GraphRunContext(state=state, deps=deps)
        end = await nxt3.run(ctx_a)  # type: ignore[union-attr]
        assert isinstance(end, End)
        return GraphRunResult(output=end.data, state=state)


def build_sim_graph() -> tuple[SimGraph, type[MissionState]]:
    """Construye Graph para tests/demos. Retorna (graph, StateType)."""
    return SimGraph(), MissionState
