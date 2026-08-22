"""PROTOTYPE THROWAWAY — logic demo para Ticket 011. No es producción.

Pregunta: ¿Se siente bien el Bridge FakeAdapter + Whiteboard + clamp CmdVel a 10Hz?

Ejecuta: uv run python plataforma/sim/prototype_demo.py
- Avanza 5 ticks con CmdVel(0.5, 0) y 3 ticks girando, luego abort.
- Imprime WhiteboardState tras cada acción (surface the state).
"""

from plataforma.sim.fake_adapter import FakeAdapter
from plataforma.sim.models import CmdVel
from plataforma.sim.state import MissionState
from plataforma.sim.whiteboard import GestoReconocido, WhiteboardState


def _print_state(label: str, state: MissionState) -> None:
    wb = state.whiteboard
    obs = wb.last_observation
    pos = f"x={obs.x:.2f} y={obs.y:.2f} yaw={obs.yaw:.2f}" if obs else "no obs"
    gesto = wb.last_gesto.label if wb.last_gesto else "—"
    print(f"[{label}] estado={wb.estado} frame={wb.frame_id} {pos} gesto={gesto}")


def main() -> None:
    print("=== PROTOTYPE 011 — FakeAdapter + Whiteboard (throwaway) ===")
    adapter = FakeAdapter()
    state = MissionState(whiteboard=WhiteboardState(estado="SIM_IDLE"))

    _print_state("init", state)

    # SIM_IDLE -> SIM_RUNNING via thumbs_up N=5 (mock 1 evento)
    state.whiteboard.last_gesto = GestoReconocido(
        label="thumbs_up", conf=0.9, frame_id=1, ts=0
    )
    state.estado = "SIM_RUNNING"
    adapter.send_cmd_vel(CmdVel(v_x=0.5, omega_z=0.0))
    for i in range(5):
        obs = adapter.step(dt_ms=100.0)
        state.whiteboard.last_observation = obs
        state.whiteboard.frame_id = obs.frame_id
        state.whiteboard.metrics = adapter.get_metrics()
        _print_state(f"tick RUN {i + 1}", state)

    # SIM_RUNNING -> SIM_PAUSED via open_palm
    state.whiteboard.last_gesto = GestoReconocido(
        label="open_palm", conf=0.85, frame_id=6, ts=0
    )
    state.estado = "SIM_PAUSED"
    adapter.send_cmd_vel(CmdVel(v_x=0.0, omega_z=0.0))
    obs = adapter.step()
    state.whiteboard.last_observation = obs
    state.whiteboard.frame_id = obs.frame_id
    _print_state("paused", state)

    # SIM_PAUSED -> SIM_RUNNING girando
    state.whiteboard.last_gesto = GestoReconocido(
        label="thumbs_up", conf=0.9, frame_id=7, ts=0
    )
    state.estado = "SIM_RUNNING"
    adapter.send_cmd_vel(CmdVel(v_x=0.3, omega_z=0.8))
    for i in range(3):
        obs = adapter.step()
        state.whiteboard.last_observation = obs
        state.whiteboard.frame_id = obs.frame_id
        _print_state(f"tick TURN {i + 1}", state)

    # SIM_RUNNING -> SIM_ABORTED
    state.whiteboard.last_gesto = GestoReconocido(
        label="fist", conf=0.92, frame_id=10, ts=0
    )
    state.estado = "SIM_ABORTED"
    adapter.send_cmd_vel(CmdVel(v_x=0.0, omega_z=0.0))
    obs = adapter.step()
    state.whiteboard.last_observation = obs
    _print_state("ABORTED (End)", state)
    msg = "Bridge SI/world-frame + clamp + 10Hz se siente correcto"
    print(f"=== END — prototype responde: {msg} ===")


if __name__ == "__main__":
    main()
