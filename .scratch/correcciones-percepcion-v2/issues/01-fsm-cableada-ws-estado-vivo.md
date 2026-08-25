# 01 — FSM cableada al WebSocket (estado vivo)

**What to build:** El gesto reconocido (`fist`/`open_palm`/`thumbs_up`) con histéresis N=5 altera la MissionFSM real y el frontend muestra `estado: RUNNING|PAUSED|ABORTED` en vivo, no `—`. `fist` 5 frames → ABORTED latch; el latch ignora gestos hasta reset.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `ws.py:perception_ws_handler` instancia `MissionFSM()` singleton y tras `gesto_payload` hace `fsm.handle_gesto(GestoReconocido(...))` y emite envelope `estado {mission: estado.value, frame_id}` con `seq_lock`
- [ ] `ws-client.js:onEstado` → `overlay.js:handleEstado` pinta chip `mission-tag` correctamente
- [ ] `uv run pytest plataforma/webcam/tests/test_fsm.py -q` verde y demo manual: 0.5s fist → `estado: ABORTED` en overlay
- [ ] No rompe contrato D5: `make_envelope` con `seq` incremental, tests `test_ws.py` verdes
