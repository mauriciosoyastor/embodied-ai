# Ticket 023 — Research: Enrollment actual + WS sync + file lock

> Label: `wayfinder:research` · Parent: `004-map-enrollment-hibrido.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por subagente research · AFK

## Question

¿Como estan hoy `plataforma/webcam/frontend/src/enrollment-panel.js` (`localStorage:webcam.identities`), `face-embedding.js` (128-d ArcFace mobilefacenet), `plataforma/webcam/backend/ws.py` (envelope D5 `frame|detecciones|gesto|estado`, `Leaky Queue N=1`) y `app.py` `lifespan` para extender a `plataforma/webcam/backend/models/identities.json`? Evaluar patron file lock (`asyncio.Lock` vs `fcntl`), carga al iniciar, y evento `enroll_sync`/`purge` sin romper `Leaky Queue N=1` ni `WS_BUFFERED_LIMIT 64KB`. Incluir fuentes primarias (code local + docs `asyncio.Lock`).

Entregable en rama `research/023-enrollment-hibrido` con `docs/agents/research/023-enrollment-hibrido.md`.

## Resolución

- Rama `research/023-enrollment-hibrido` — `docs/agents/research/023-enrollment-hibrido.md` (research subagente)
- `enrollment-panel.js:8` `webcam.identities` no hace `ws.send` aún, `Borrar todos` solo local; `face-embedding.js` 128-d L2 `threshold 0.42`; `ws.py:36` whitelist `frame|detecciones|gesto|estado` + `AsyncLeakyQueue N=1` + `WS_BUFFERED_LIMIT 64KB` solo para `frame`; `app.py:27` `lifespan` punto para `store.load()` + `GET /identities`
- `asyncio.Lock` recomendado (no `fcntl` en `win32`) + write atómico `tmp→replace`; nuevos envelopes `enroll_sync/enroll_ack/purge/purge_ack` bypass queue

**Desbloquea:** 024, 025
