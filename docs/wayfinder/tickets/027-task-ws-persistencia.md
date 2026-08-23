# Ticket 027 — Task: Implementar WS handlers + persistencia + tests

> Label: `wayfinder:task` · Parent: `004-map-enrollment-hibrido.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por Muse Spark · AFK/HITL

## Question

Trabajo no-decisivo: `plataforma/webcam/backend/ws.py` handlers `enroll_sync`/`purge`/`enroll_ack`, `backend/models/identities.json` con `asyncio.Lock`, `app.py` `GET /identities` y `lifespan` load, `frontend/src/enrollment-panel.js` `localStorage` + `ws.send(enroll_sync)` + `onEnrollAck`, tests headless sin camara (`test_ws` + `test_enrollment`). Bloqueado por 026.

Checklist HITL si no AFK:
- [ ] `ws.py` `enroll_sync` guarda con lock y responde `enroll_ack`
- [ ] `ws.py` `purge` borra file + broadcast
- [ ] `app.py` `lifespan` carga `identities.json` y `GET /identities`
- [ ] `enrollment-panel.js` `localStorage` + `ws.send` + `purge` dual
- [ ] `uv run pytest plataforma/webcam -q` pass

## Resolución

- `plataforma/webcam/backend/identities.py` nuevo: `IdentitiesStore` con `asyncio.Lock` + `tmp→replace` atomico, `l2_normalize`, `enroll` idempotente `nanoid` + promedio `hat_e = normalize(e_old*min(N,5)+e_new)`, `purge`, `load`/`get_all`, singleton `store`
- `plataforma/webcam/backend/ws.py:26` `EnvelopeType` extendido `enroll_sync/enroll_ack/purge/purge_ack/identities`, `connected_clients` set broadcast, `handle_enroll_sync`/`handle_purge` bypass `LeakyQueue N=1`, `perception_ws_handler` branch paralelo + `connected_clients.add/discard`, `ruff`/`mypy` ok
- `plataforma/webcam/backend/app.py:11` `store` import, `lifespan` `await store.load()` log `Identities cargadas`, `GET /identities` snapshot hibrido
- `plataforma/webcam/frontend/src/enrollment-panel.js:8` `STORAGE_PENDING` + `hydrateFromServer()` `GET /identities`, `wsSendEnrollSync`/`flushPending`/`pending_sync` offline queue, `tryEnroll` hibrido `enroll_sync` + pending, `clearBtn` + per-item delete `purge {all:true|ids:[]}` broadcast, `setWsClient`/`handleEnrollAck`/`handlePurgeAck`/`_embedder`
- `plataforma/webcam/frontend/src/main.js:189` `wsClient` `onEnrollAck`/`onPurgeAck` → `enrollment.handle*`, `setWsClient` + `flushPending` en `ws.onopen`, `hydration` al iniciar
- `plataforma/webcam/frontend/ws-client.js:26` `onEnrollAck`/`onPurgeAck` callbacks, `enroll_sync`/`purge_ack` handling
- Verificación: `GET /identities` 0, `ws enroll_sync test1234` → `enroll_ack ok count 1`, `GET 1`, `purge {all:true}` → `purge_ack n=1`, `GET 0` (via `websockets` + `httpx` 2026-08-23), `ruff format`/`check` All checks passed, `mypy` Success, `pytest 64 passed`

**Way completo:** reload verifica `localStorage` + `identities.json` persistencia, `purge` limpia ambas fuentes (broadcast).
