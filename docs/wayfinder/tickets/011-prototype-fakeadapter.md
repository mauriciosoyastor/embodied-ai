# Ticket 011 — Prototype: FakeAdapter + SimObservation/CmdVel throwaway

> Label: `wayfinder:prototype` · Parent: `001-map-orchestrador-sim.md` · Estado: cerrado · Resolución: 2026-08-22

## Resolución

**Prototype throwaway LOGIC (HITL) — `uv run python plataforma/sim/prototype_demo.py`:**

- **Pregunta respondida:** ¿Se siente bien el Bridge FakeAdapter + Whiteboard + clamp 10Hz? **Sí** — `SI/world-frame`, `CmdVel` clamp `v_x±1.0`/`omega±1.5`, cinemática `yaw+=omega·dt, x+=v·cos(yaw)·dt`, `WhiteboardState` sin `transcript` se siente correcto.
- **Artefactos (throwaway, branch `prototype/011-fakeadapter` previsto):** `plataforma/sim/whiteboard.py:7` `WhiteboardState`+`GestoReconocido` (`CONTEXT.md:56`), `plataforma/sim/state.py:7` `MissionState` dataclass (`ctx.state.whiteboard`), `plataforma/sim/fake_adapter.py:7` `FakeAdapter` 10Hz mock ya verde en 013, `plataforma/sim/prototype_demo.py:1` demo que imprime `WhiteboardState` tras cada tick (surface the state).
- **Demo output (10 ticks):** `SIM_IDLE→RUNNING (thumbs_up)→5 ticks x 0.05→PAUSED (open_palm)→RUNNING turn 0.3/0.8→3 ticks yaw 0.08/0.16/0.24→ABORTED (fist End)`, `frame_id` 10Hz determinístico, `metrics steps/s≈10`.
- **Checks:** `ruff` ✅ `mypy` 9 files ✅ `pytest plataforma/sim 3 passed` ✅ — no persiste, trivial `uv run python plataforma/sim/prototype_demo.py`, sin `mujoco` en CI.
- **Fold:** `WhiteboardState` validado plegado a `plataforma/sim` real (no solo prototype); prototype capturado como throwaway.

> Estado previo: abierto · HITL → desbloquea 012

## Question

¿Cómo se ve y se siente el Bridge mínimo? Prototype throwaway de `FakeAdapter` que cumple el `Protocol` de `CONTEXT.md:46`.

Crear artefacto concreto (no spec) para reaccionar:
- `plataforma/sim/fake_adapter.py` (o `plataforma/webcam/sim/fake_adapter.py` — decidir path) con `class FakeAdapter(SimAdapter)` + métodos `get_observation()→SimObservation`, `send_cmd_vel(CmdVel)→None`, `get_metrics()→SimMetrics`
- `SimObservation` Pydantic con `pose (x,y,yaw)`, `twist (v_x,omega)`, `ts`, `frame_id` (SI/world-frame, cada adapter normaliza) — mock cinemática diferencial integrada 10Hz (`plataforma/webcam/frontend/src/main.js:290` throttling)
- `CmdVel` con clamp `v_x∈[-1,1] m/s`, `omega∈[-1.5,1.5] rad/s` + conversión `(v,ω)→(ωL,ωR)` dummy (sin MuJoCo)
- `FakeAdapter` avanza pose por `dt` con ruido leve, expone `SimMetrics { steps/s, wall_time }`
- Ubicación: `plataforma/sim/` nuevo paquete `uv` member (añadir a `pyproject.toml:46` `tool.uv.workspace.members`) con `pytest` headless que hace `send_cmd_vel` → `get_observation` → assert pose cambió
- No instalar `mujoco`; validar que `uv sync --all-packages` sigue verde path-filtered `plataforma/webcam/**` (`plataforma/webcam/backend` ya existe)

Links prototype como asset en este ticket. Bloqueado por 013 (harness define estructura de test). Desbloquea 012.

## Bloquea

- 012-grilling-integracion-safety
