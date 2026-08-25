# 04 — Ruta POST /fsm/reset + botón Abortar/Reset

**What to build:** Tablero externo o usuario puede liberar latch `ABORTED→IDLE` sin reconectar WebSocket.

**Blocked by:** 01 — FSM cableada al WebSocket (estado vivo).

**Status:** ready-for-agent

- [ ] `POST /fsm/reset` `app.py` → `fsm.reset()` `fsm.py:125` y emite `estado {mission: IDLE}` broadcast
- [ ] Botón `Reset misión` en `frontend/src/main.js` llama `fetch POST /fsm/reset` y actualiza `p-estado` a `IDLE`
- [ ] `curl -X POST http://localhost:8000/fsm/reset` pasa de `ABORTED` a `IDLE` y siguiente `thumbs_up N=5` → `RUNNING` sin `close` WS
- [ ] Test `test_fsm.py` + manual E2E con `fist` 5s → `ABORTED` → `POST /reset` → `RUNNING`
