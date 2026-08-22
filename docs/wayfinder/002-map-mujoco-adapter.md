# Wayfinder Map — MujocoAdapter Real (TurtleBot Diferencial)

> Label: `wayfinder:map` · Estado: abierto · Tracker: local-markdown · Creado: 2026-08-22

## Destination

Implementar y validar `MujocoAdapter` real en `plataforma/sim` usando MuJoCo (MJCF TurtleBot diferencial con mapping `(v_x, omega) → (ωL, ωR)`), reemplazando el `FakeAdapter` provisional. Cierra cuando `uv run pytest plataforma/sim -q` corre con física real de MuJoCo (o fallback seguro en CI sin display), con demo `python -m plataforma.sim` operando el modelo físico y `ruff`/`mypy`/`pytest` verde.

## Notes

- Dominio: Embodied AI platform · `plataforma/sim` (Bridge/Adapter físico) + MuJoCo Python (`mujoco`)
- Skills a consultar por sesión: `grilling`, `domain-modeling`, `prototype`, `research`, `tdd`
- Preferencias fijas: Mantener compatibilidad con el `Protocol` definido en `adapter.py` y el `WhiteboardState` del mapa 001; soporte CI headless.

## Decisions so far

<!-- índice — una línea por ticket cerrado: gist + link; el detalle vive en el ticket -->

- [Research MuJoCo Python & headless — Ticket 014](tickets/014-research-mujoco-python.md) — `mujoco>=3.0.0` agregado en `plataforma/sim/pyproject.toml`, mypy override `mujoco.*`, y bucle `mujoco.mj_step` validado como nativo headless en CPU/memoria sin requerir display (2026-08-22) — desbloquea 016 partial
- [Grilling Modelo MJCF & cinemática — Ticket 015](tickets/015-grilling-turtlebot-mjcf.md) — MJCF minimalista inline (base libre + ruedas left/right), cinemática diferencial con $L=0.23, R=0.033$ y clamping de `CmdVel` (2026-08-22) — desbloquea 016

## Not yet specified

<!-- fog hacia el destino — no ticketizable aún con nitidez; gradúa cuando la frontera avance -->

- Control PID de velocidad de rueda individual vs control cinemático directo `CmdVel`
- Sensores avanzados en simulación (lidar/depth camera simulada vs simple odometría/posvis)

## Out of scope

- ROS2 / Nav2 / Gazebo completo — se usa MuJoCo nativo liviano
- Manipuladores robóticos avanzados (brazos) — solo base móvil diferencial

## Tickets (frontera)

### Ticket 014 — Research: MuJoCo Python package y loop headless en uv [wayfinder:research] — CERRADO 2026-08-22 (AFK)
**Question:** ¿Cómo instalar y configurar `mujoco` Python package en el entorno uv del monorepo, y gestionar el step loop headless (sin ventana gráfica) para tests automáticos?
**Bloquea:** 016
**Estado:** cerrado — ver [014](tickets/014-research-mujoco-python.md)

### Ticket 015 — Grilling: Modelo MJCF TurtleBot y cinemática diferencial [wayfinder:grilling] — CERRADO 2026-08-22 (HITL)
**Question:** ¿Qué archivo MJCF usar (incorporado en `mujoco` assets o custom minimalista) y cómo implementar la cinemática inversa diferencial `(v_x, omega) → (omega_l, omega_r)` acorde al `CmdVel` del orquestador?
**Bloquea:** 016
**Estado:** cerrado — ver [015](tickets/015-grilling-turtlebot-mjcf.md)

### Ticket 016 — Prototype: MujocoAdapter cumpliendo adapter.Protocol [wayfinder:prototype] — ABIERTO
**Question:** ¿Cómo estructurar `plataforma/sim/mujoco_adapter.py` instanciando `mujoco.MjModel`/`MjData`, ejecutando step a 10Hz y mapeando `SimObservation` (pose, velocidad) y `CmdVel`?
**Bloquea:** 017

### Ticket 017 — Task: Integración con CI headless y pytest suite [wayfinder:task] — ABIERTO
**Question:** Asegurar que `pytest plataforma/sim -q` ejecute con el `MujocoAdapter` real en máquinas con MuJoCo instalado, y salte gracefully o use FakeAdapter en entornos CI limpios donde MuJoCo C++ no esté disponible.
