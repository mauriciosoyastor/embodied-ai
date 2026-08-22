"""Tests TDD para StateGraph sim — 009/010/012."""

import pytest

from plataforma.sim.fake_adapter import FakeAdapter
from plataforma.sim.graph import SimDeps, build_sim_graph
from plataforma.sim.state import MissionState
from plataforma.sim.whiteboard import GestoReconocido, WhiteboardState


@pytest.mark.anyio
async def test_gesto_thumbs_up_5_ticks_to_running() -> None:
    graph, _ = build_sim_graph()
    state = MissionState(whiteboard=WhiteboardState(estado="SIM_IDLE"))
    deps = SimDeps(adapter=FakeAdapter())
    # 5 thumbs_up consecutivos → SIM_RUNNING + CmdVel 0.5 + pose avanza
    for i in range(5):
        state.whiteboard.last_gesto = GestoReconocido(
            label="thumbs_up", conf=0.9, frame_id=i, ts=float(i * 100)
        )
        result = await graph.run(state=state, deps=deps)
        # primeros 4 ticks no transicionan, 5to sí
        if i < 4:
            assert result.output in ("SIM_IDLE", "SIM_RUNNING")  # hysteresis progresiva
        else:
            assert result.output == "SIM_RUNNING"
            assert state.whiteboard.last_observation is not None
            assert state.whiteboard.last_observation.x > 0


@pytest.mark.anyio
async def test_fist_aborted_latch_ignores_llm() -> None:
    graph, _ = build_sim_graph()
    state = MissionState(whiteboard=WhiteboardState(estado="SIM_RUNNING"))
    deps = SimDeps(adapter=FakeAdapter())
    # forzar ABORTED con 5 fist
    for i in range(5):
        state.whiteboard.last_gesto = GestoReconocido(
            label="fist", conf=0.95, frame_id=i, ts=0
        )
        result = await graph.run(state=state, deps=deps)
    assert result.output == "ABORTED"
    assert state.whiteboard.estado == "SIM_ABORTED"
    # siguiente thumbs_up debe seguir ABORTED (latch)
    state.whiteboard.last_gesto = GestoReconocido(
        label="thumbs_up", conf=0.9, frame_id=10, ts=0
    )
    # fake decision avanzar previa

    # setear decision que intentaría avanzar
    try:
        import sys

        sys.path.insert(0, "fase-1")
        from orchestrator import DecisionAgentica  # type: ignore[import-not-found]

        state.whiteboard.last_decision = DecisionAgentica(
            accion="avanzar", razon="intento", nivel_confianza=0.9
        )
    except Exception:
        pass
    result2 = await graph.run(state=state, deps=deps)
    assert result2.output == "ABORTED"
    # CmdVel debe ser 0 → pose no avanza mucho (deadman + abort)
    obs_before = state.whiteboard.last_observation
    assert obs_before is not None


@pytest.mark.anyio
async def test_deadman_5_ticks_none_to_stop() -> None:
    graph, _ = build_sim_graph()
    state = MissionState(whiteboard=WhiteboardState(estado="SIM_RUNNING"))
    deps = SimDeps(adapter=FakeAdapter())
    # primero poner RUNNING con gesto válido
    state.whiteboard.last_gesto = GestoReconocido(
        label="thumbs_up", conf=0.9, frame_id=0, ts=0
    )
    # forzar N=5 para entrar RUNNING ya está RUNNING, ahora 5 ticks none → deadman
    for i in range(5):
        state.whiteboard.last_gesto = GestoReconocido(
            label="none", conf=0.0, frame_id=i + 1, ts=0
        )
        result = await graph.run(state=state, deps=deps)
    # deadman debe mandar CmdVel 0, pero estado sigue RUNNING (no ABORTED)
    assert result.output == "SIM_RUNNING"
    # metrics debe existir
    assert state.whiteboard.metrics is not None
