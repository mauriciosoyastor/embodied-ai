# Ticket 024 — Grilling: Protocolo WS sync y purga dual

> Label: `wayfinder:grilling` · Parent: `004-map-enrollment-hibrido.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por Muse Spark · HITL

## Question

¿Envelope para sync? `type: enroll_sync {id,nombre,embedding[128],ts}` vs reutilizar `type: frame`. ¿Idempotencia por `id`, `ack {type: enroll_ack, payload:{id,status}}`, y `purge {type: purge, payload:{all:true|ids:[]}}` que limpia `localStorage:webcam.identities` + `identities.json` simultaneamente? Definir orden, retry si WS desconectado, y feedback en `percepcion-panel`. HITL con `grilling` + `domain-modeling`. Bloqueado por 023.

## Resolución

**Decisión cerrada (Q1-Q5):**

- **Q1 Bypass Leaky Queue:** `enroll_sync`/`purge` como `type` independientes, no reutilizar `frame`; bypass `AsyncLeakyQueue N=1` por branch paralelo con `asyncio.Lock` + `WS_BUFFERED_LIMIT` bypass (payload ~2KB vs 64KBiros de frame).
- **Q2 Idempotencia:** `nanoid` 8-char en cliente (`enrollment-panel.js`), servidor `identities.json` idempotente por `id` (duplicate → `enroll_ack {status: duplicate}` no error), reintentos automáticos tras `ws.onopen` con backoff.
- **Q3 Purge broadcast:** `purge {all:true}` emitido a `todos los sockets activos` (broadcast) con `purge_ack` por cliente, invalidación inmediata caché `localStorage` + `identities.json`; `purge {ids:[]}` reservado futuro, requiere confirm dialog en UI.
- **Q4 Resiliencia offline:** `webcam.pending_sync` en `localStorage` acumula mutaciones si `ws.readyState !== OPEN`, cero pérdida, vaciado en `ws.onopen` + `GET /identities` fallback.
- **Q5 Hidratación híbrida:** `GET /identities` snapshot al iniciar (`app.py` `lifespan` carga `identities.json`), WS solo deltas `enroll_sync`/`purge` tiempo real; badge `local/server synced` + toast en `percepcion-panel`.

**Glosario:** `CONTEXT.md:89-93` nuevos términos `EnrollSync/EnrollAck`, `Purge/PurgeAck`, `PendingSync`, `Hidratación híbrida`, `Bypass de Leaky Queue`.

**Desbloquea:** 025, 026

Respuestas: Q1 bypass tipos independientes, Q2 nanoid idempotencia, Q3 purge broadcast all:true, Q4 pending_sync offline, Q5 GET snapshot + WS deltas.
