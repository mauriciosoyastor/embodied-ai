# Wayfinder Map — Orquestador Cognitivo + Simulación (Bridge FakeAdapter)

> Label: `wayfinder:map` · Estado: cerrado — way completo · Tracker: local-markdown (hijo de `docs/wayfinder/000-map-voz-camara-registro.md` como base) · Creado: 2026-08-22 · Cerrado: 2026-08-22

## Destination

Prototipo mínimo ejecutable en `plataforma/` donde **StateGraph + Whiteboard + DecisionAgentica (Muse Spark `opencode/muse-spark-1.2-contributor-free` vía `openai:opencode/...`)** consume `GestoReconocido` vía `handle_gesto` histéresis N=5 y comanda `FakeAdapter` (`SimObservation`/`CmdVel` SI/world-frame) headless con `pytest` verde y demo `python -m plataforma.sim` local. `MujocoAdapter` queda desacoplado/bloqueado. `plataforma/webcam` (Voz+Cámara) reusado como módulo base sin cambios. Cierra cuando `uv run pytest plataforma/sim -q` + loop `Gesto→StateGraph→CmdVel→SimObservation` corre sin MuJoCo físico, con `TestModel` y con Muse Spark real (key `fase-1/.env`).

## Notes

- Dominio: Embodied AI platform · `plataforma/webcam` (FastAPI+Vite, ya done) + `plataforma/sim` (Bridge/Adapter) + `fase-1` (Pydantic AI orquestador)
- Skills a consultar por sesión: `grilling`, `domain-modeling`, `prototype`, `research` (y `tdd` para harness)
- Preferencias fijas: TDD baseline primero (Q10 harness verde antes de lógica), `FakeAdapter` primero para no bloquear CI con `mujoco` C++, `Muse Spark 1.2 free` por defecto (`fase-1/.env` `OPENCODE_API_KEY`), `GestoReconocido` como frontera con módulo base, `TestModel` para headless, `uv sync --all-packages` + `pythonpath=["."]`
- Base ya verificada: `fase-1/orchestrator.py` `Agent[HardwareContext, DecisionAgentica]` + `TestModel`, `CONTEXT.md` contratos `SimObservation`/`CmdVel`/`Bridge/Adapter`, `plataforma/webcam` `WS /ws/percepcion` operativo; `OPENCODE_API_KEY` aún placeholder `sk-reemp...` (ver verificación 2026-08-22)

## Decisions so far

<!-- índice — una línea por ticket cerrado: gist + link; el detalle vive en el ticket -->

- [Task harness headless — Ticket 013](tickets/013-task-harness-headless.md) — `plataforma/sim` uv member + `FakeAdapter` 10Hz mock + `pytest 3 passed` con `TestModel`, `ruff`/`mypy` verde sin `mujoco` (2026-08-22) — desbloquea 011
- [Research StateGraph — Ticket 008](tickets/008-research-stategraph-pydantic.md) — `pydantic-graph` 2.32.1 vía `pydantic-ai-slim` (53 KiB, `py.typed`, `TestModel` ok, `openai:opencode` nativo) recomendado sobre LangGraph/transitions/statemachine (2026-08-22) — desbloquea 009, 010
- [Grilling StateGraph estados — Ticket 009](tickets/009-grilling-stategraph-estados.md) — 4 estados `SIM_IDLE/RUNNING/PAUSED/ABORTED(End)` + mapping `thumbs_up/open_palm/fist N=5` idéntico `handle_gesto` + híbrido FSM-gated (LLM solo en RUNNING) + `none`=no-op, `TickNode` 10Hz (2026-08-22) — desbloquea 012 parcial
- [Grilling Whiteboard — Ticket 010](tickets/010-grilling-whiteboard-schema.md) — `WhiteboardState` en `plataforma/sim` (`estado, frame_id, last_gesto/obs/decision/metrics`, sin `transcript`, single-writer memoria, Reducer fog) (2026-08-22) — desbloquea 012 parcial
- [Prototype FakeAdapter — Ticket 011](tickets/011-prototype-fakeadapter.md) — throwaway `prototype_demo.py` `FakeAdapter` 10Hz + `WhiteboardState`/`MissionState`, demo `SIM_IDLE→RUNNING→PAUSED→ABORTED` `frame_id` determinístico, `ruff`/`mypy`/`pytest` verde (2026-08-22) — desbloquea 012
- [Grilling integración — Ticket 012](tickets/012-grilling-integracion-safety.md) — loop 10Hz `TickNode` siempre, mismo `WS /ws/percepcion` `sim_obs/sim_cmd`, safety clamp+Deadman 500ms, `ABORTED` latch ignora LLM hasta `reset()`, streaming fog (2026-08-22) — **mapa sin frontera**

## Not yet specified

<!-- fog hacia el destino — no ticketizable aún con nitidez; gradúa cuando la frontera avance -->

- Reducer + Grammar-Constrained Decoding completo (más allá de `DecisionAgentica` actual) — fog hasta cerrar StateGraph+Whiteboard
- MujocoAdapter real (MJCF TurtleBot diferencial `(v_x,omega)→(ωL,ωR)`) — bloqueado por harness verde; gradúa tras FakeAdapter validado
- ROS2 / Gazebo / PX4 Offboard como adapters futuros — fuera de este prototipo
- Safety Envelope físico completo (`Deadman's Switch`, `Heartbeat` 1-5Hz, `Geofencing`, `Failsafe`, `Stick Override`) — decidir alcance mínimo en Ticket 012
- Streaming TTS por chunks vs respuesta completa (fog heredado de mapa 000) — evaluar si afecta Whiteboard `transcript`
- Persistencia Whiteboard más allá de memoria (¿`plataforma/sim/whiteboard.json`?) — por ahora memoria

## Out of scope

- Modificar `plataforma/webcam` (Voz+Cámara) más allá de consumir `GestoReconocido` — es módulo base congelado (ver mapa 000)
- Auth cloud / DB centralizada para sim — solo local/headless
- Video grabación persistente y dataset biometría — privacy ya resuelto en mapa 000 (`localStorage` only)
- Instalación MuJoCo/Gazebo en CI principal — path-filtered `plataforma/sim` solo con `FakeAdapter` en este mapa

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos nativos en tracker real; aquí se listan con `Bloquea:` y estado `abierto/cerrado`.

### Ticket 008 — Research: StateGraph con pydantic-ai vs alternativas [wayfinder:research] — CERRADO 2026-08-22 (AFK)
**Question:** ¿`pydantic-graph`/`pydantic-ai` StateGraph nativo vs `LangGraph` vs `transitions` para modelar estados, con compat `openai:opencode/muse-spark-1.2-contributor-free` y `TestModel` headless?
**Bloquea:** 009, 010
**Estado:** cerrado — ver [008](tickets/008-research-stategraph-pydantic.md)

### Ticket 009 — Grilling: Estados y transiciones del StateGraph [wayfinder:grilling] — CERRADO 2026-08-22 (HITL)
**Question:** ¿Tabla de estados (¿reusar `ABORTED` latch + `PAUSED`/`RUNNING` + `SIM_IDLE`/`SIM_MOVING` o `IDLE→EXECUTING→DONE`?) y transiciones `handle_gesto`→`DecisionAgentica`→`CmdVel`?
**Bloquea:** 012
**Estado:** cerrado — ver [009](tickets/009-grilling-stategraph-estados.md)

### Ticket 010 — Grilling: Schema del Whiteboard [wayfinder:grilling] — CERRADO 2026-08-22 (HITL)
**Question:** ¿Pydantic schema del Whiteboard: `SimObservation + GestoReconocido + DecisionAgentica + SimMetrics` (+ ¿`transcript`?) en `plataforma/sim/whiteboard.py`? ¿Memoria vs persistencia?
**Bloquea:** 012
**Estado:** cerrado — ver [010](tickets/010-grilling-whiteboard-schema.md)

### Ticket 011 — Prototype: FakeAdapter + SimObservation/CmdVel throwaway [wayfinder:prototype] — CERRADO 2026-08-22 (HITL)
**Question:** ¿Cómo se ve el Bridge mínimo? Prototype throwaway `plataforma/sim/fake_adapter.py` que cumple `Protocol` (`SimObservation` SI/world-frame, `CmdVel` clamp, `SimMetrics` 10Hz mock) para validar contrato sin MuJoCo.
**Bloquea:** 012
**Estado:** cerrado — ver [011](tickets/011-prototype-fakeadapter.md)

### Ticket 012 — Grilling: Integración Gesto→StateGraph→CmdVel + safety mínimo [wayfinder:grilling] — CERRADO 2026-08-22 (HITL)
**Question:** ¿Loop cerrado `GestoReconocido`→StateGraph→`DecisionAgentica` (Muse Spark)→`CmdVel`→`SimObservation`? ¿Rate 10Hz como `webcam/frontend/src/main.js:290`, throttling, y qué safety mínimo (`Deadman's Switch`/`Heartbeat`/`Safety Envelope`) entra en este prototipo vs fog?
**Estado:** cerrado — ver [012](tickets/012-grilling-integracion-safety.md)

### Ticket 013 — Task: Harnés headless TDD con TestModel [wayfinder:task] — CERRADO 2026-08-22 (AFK)
**Question:** Trabajo previo no-decisivo: `pytest plataforma/sim -q` verde con `FakeAdapter` stub + `TestModel` + `HardwareContext`, `uv` workspace `plataforma/sim`, `pythonpath=["."]`, sin `mujoco` en CI. Establece baseline para Q8/Q9.
**Estado:** cerrado — ver [013](tickets/013-task-harness-headless.md)
