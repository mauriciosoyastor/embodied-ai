# Ticket 012 — Grilling: Integración Gesto→StateGraph→CmdVel + safety mínimo

> Label: `wayfinder:grilling` · Parent: `001-map-orchestrador-sim.md` · Estado: cerrado · Resolución: 2026-08-22

## Resolución

**Decisión HITL Q1-Q4 (aprobado recomendado 2026-08-22) — cierra mapa 001:**

- **Q1 Rate 10Hz** — `TickNode` siempre `adapter.step(100ms)` + `state.whiteboard.frame_id++` aunque `Gesto==none`, histéresis N=5 → 500ms @10Hz idéntico a `plataforma/webcam/frontend/src/main.js:290` `canSend()` + `Leaky Queue N=1` `CONTEXT.md:20`. No 5Hz.
- **Q2 Endpoint mismo WS** — reusar `WS /ws/percepcion` envelope `{type,seq,ts,payload}` `CONTEXT.md:55` con nuevos `type: sim_obs`/`sim_cmd` (mismo WS, `seq` drop-detection). En tests mock `GestoReconocido`, en demo real consume WS real. `POST /sim/cmd_vel` y `WS /ws/sim` quedan **fog** para backend sim separado futuro.
- **Q3 Safety mínimo** — `FakeAdapter.send_cmd_vel` clamp + `Deadman's Switch` 500ms en `ActNode` (`Gesto`/`Decision` ausente >5 ticks → `CmdVel(0,0)`). `Heartbeat` 1-5Hz, `Geofencing`, `Failsafe`, `Stick Override`, `Safety Envelope` físico quedan **fog/not yet specified** (para `MujocoAdapter`/PX4).
- **Q4 ABORTED + streaming** — `SIM_ABORTED` latch propaga inmediato `CmdVel(0,0)` aunque LLM proponga `avanzar`, ignora todo gesto hasta `reset()` explícito (`state.whiteboard.estado="SIM_IDLE"`). Muse Spark **respuesta completa** por ahora; streaming chunks queda fog heredado mapa 000 (no afecta `Whiteboard.last_decision`).

**Secuencia headless validada (spec para pytest final del mapa):**
`GestoReconocido(thumbs_up N=5)→SIM_RUNNING→DecisionNode(TestModel→CmdVel 0.5)→ActNode→pose x avanza`; `fist N=5→SIM_ABORTED(End)→CmdVel(0,0)` incluso si LLM dice `avanzar` — testeable con `TestModel` sin red.

> Estado previo: abierto · HITL — último ticket del mapa 001

## Question

¿Loop cerrado `GestoReconocido` → `StateGraph` → `DecisionAgentica` (Muse Spark) → `CmdVel` → `FakeAdapter` → `SimObservation` → `Whiteboard`?

Decidir (grilling + domain-modeling):
- ¿Rate del loop: 10Hz como `plataforma/webcam/frontend/src/main.js:290` `canSend()` + `WS_BUFFERED_LIMIT`, o 5Hz para sim headless? ¿Throttling `MAX_FPS` y `Leaky Queue N=1` (`CONTEXT.md:20`)?
- ¿Endpoint: reusa `WS /ws/percepcion` envelope `{type,seq,ts,payload}` (`CONTEXT.md:55`) con nuevo `type: sim_cmd`/`sim_obs`, o nuevo `WS /ws/sim` / `POST /sim/cmd_vel` REST?
- ¿Safety mínimo en prototipo: `Safety Envelope` clamp en `FakeAdapter.send_cmd_vel` + `Deadman's Switch` (ausencia `Gesto`/`Decision` → `CmdVel(0,0)`), o todo a fog? ¿`Heartbeat` 1-5Hz y `Geofencing`/`Failsafe` quedan out?
- ¿Muse Spark streaming (chunks) vs respuesta completa afecta TTS/Whiteboard `transcript` (fog heredado mapa 000)?
- ¿`ABORTED` latch propaga a sim (detiene `CmdVel`) y requiere `reset()` explícito en `Whiteboard`?
- Salida: secuencia headless `pytest` que simula `GestoReconocido(thumbs_up N=5)` → `RUNNING` → `CmdVel(v=0.5)` → pose avanza, y `fist N=5` → `ABORTED` → `CmdVel(0,0)` incluso si LLM dice `avanzar`.

Bloqueado por 009,010,011. Es el ticket que cierra el mapa (define done).
