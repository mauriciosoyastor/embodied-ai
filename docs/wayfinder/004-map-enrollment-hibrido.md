# Wayfinder Map — Enrollment Hibrido localStorage + identities.json

> Label: `wayfinder:map` · Estado: cerrado — way completo · Tracker: local-markdown · Creado: 2026-08-23 · Cerrado: 2026-08-23

## Destination

**Change en lugar** en `plataforma/webcam` donde `Enrollment facial` persiste **hibrido**: `localStorage:webcam.identities` para render inmediato sin latencia + `plataforma/webcam/backend/models/identities.json` en servidor (embedding promediado tras `thumbs_up N=5`) cargado en memoria al iniciar, sincronizado via evento `WebSocket` en cada enroll, y **purga** (`clear`) limpia ambas fuentes simultaneamente. Cierra cuando `POST enroll` local → WS `enroll_sync` → `identities.json` → reload verifica persistencia y `purge` borra ambos.

## Notes

- Dominio: Embodied AI platform · `plataforma/webcam` (`enrollment-panel.js`, `face-embedding.js`, `ws.py`/`app.py`, `localStorage`) + `plataforma/sim` no tocado
- Skills a consultar por sesion: `grilling`, `domain-modeling`, `research`, `prototype`
- Preferencias fijas: aislado localStorage util para render sin latencia pero vulnerable a limpieza; servidor guarda embedding promediado tras `N=5`; hibrido con WS sync y purga dual (usuario definio estrategia)
- Estado actual: `localStorage:webcam.identities` existe (mapa 000 Ticket 005), `identities.json` gitignoreado pero no implementado, WS `/ws/percepcion` operativo en `:8000`, `handle_gesto` histéresis `N=5` verificado

## Decisions so far

- [Research: Enrollment actual + WS sync + file lock — Ticket 023](tickets/023-research-enrollment-hibrido.md) — `enrollment-panel.js` no WS aún, 128-d threshold 0.42, `ws.py` bypass `Leaky Queue N=1`, `asyncio.Lock` + tmp→replace (2026-08-23)
- [Grilling: Protocolo WS sync y purga dual — Ticket 024](tickets/024-grilling-ws-sync-purga.md) — `enroll_sync/enroll_ack/purge/purge_ack` bypass `N=1`, `nanoid` idempotencia, `purge {all:true}` broadcast, `pending_sync` offline, `GET /identities` hidratación (2026-08-23)
- [Grilling: Schema identities.json y embedding promediado — Ticket 025](tickets/025-grilling-identities-schema.md) — `{id,nombre,embedding[128],count,updatedAt}` cap 5 `hat_e = normalize(e_old*min(N,5)+e_new)`, `asyncio.Lock` + tmp→replace, `id` PK (2026-08-23)
- [Prototype: UI hibrido + purga — Ticket 026](tickets/026-prototype-ui-hibrido.md) — `prototype-enrollment-hibrido.html` Tabla vs Chips, `enroll_sync`/`purge` flujos, badge `pending_sync`, veredicto Tabla para prod (2026-08-23)
- [Task: Implementar WS handlers + persistencia + tests — Ticket 027](tickets/027-task-ws-persistencia.md) — `identities.py` + `ws.py` bypass `N=1` + `app.py` `GET /identities` + `enrollment-panel.js` hibrido, WS `enroll_ack`/`purge_ack` verificado (2026-08-23) — **mapa sin frontera**
- [Prototype: UI hibrido + purga — Ticket 026](tickets/026-prototype-ui-hibrido.md) — `prototype-enrollment-hibrido.html` Tabla vs Chips, `enroll_sync`/`purge` flujos, badge `pending_sync`, veredicto Tabla para prod (2026-08-23)

## Not yet specified

- Tamaño limite `identities.json` y expiracion (LRU) — por ahora ilimitado (Ticket 025 Q5)

## Out of scope

- Auth cloud / OAuth / DB centralizada — solo archivo JSON local servidor
- Video grabacion persistente y dataset biometria — privacy ya en mapa 000 (`localStorage` only) ahora hibrido pero sin cloud
- Entrenar modelo facial nuevo — solo ArcFace `mobilefacenet` 128-d existente
- Compartir identidades entre navegadores sin pasar por servidor (P2P) — solo via `identities.json`

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos: `Bloquea:` = este ticket bloquea a otros.

### Ticket 023 — Research: Enrollment actual + WS sync + file lock [wayfinder:research] — CERRADO 2026-08-23
**Question:** ¿Como estan hoy `enrollment-panel.js` (`localStorage:webcam.identities`), `face-embedding.js` (128-d), `ws.py` envelope D5 y `app.py` lifespan para extender a `identities.json`? Evaluar patron file lock (fcntl/asyncio.Lock), carga al iniciar, y evento `enroll_sync`/`purge` sin romper `Leaky Queue N=1`.
**Bloquea:** 024, 025
**Estado:** cerrado — ver [023](tickets/023-research-enrollment-hibrido.md)

### Ticket 024 — Grilling: Protocolo WS sync y purga dual [wayfinder:grilling] — CERRADO 2026-08-23
**Question:** ¿Envelope para sync? `type: enroll_sync {id,nombre,embedding,ts}` vs `type: frame` reutilizado. ¿Idempotencia, ack `enroll_ack`, y `purge {all:true|ids:[]}` que limpia `localStorage` + `identities.json`? HITL con `grilling` + `domain-modeling`.
**Bloquea:** 026, 027
**Estado:** cerrado — ver [024](tickets/024-grilling-ws-sync-purga.md) — `enroll_sync` bypass `N=1`, `nanoid`, `purge broadcast`, `pending_sync`, `GET /identities`

### Ticket 025 — Grilling: Schema identities.json y embedding promediado [wayfinder:grilling] — CERRADO 2026-08-23
**Question:** ¿Schema `identities.json` `{id,nombre,embedding[128],count,updatedAt}` con promedio `new = (old*count + new)/(count+1)` L2-norm? ¿File lock, carga en `lifespan` y `GET /identities` para hidratacion inicial? HITL.
**Bloquea:** 026, 027
**Estado:** cerrado — ver [025](tickets/025-grilling-identities-schema.md) — `count`+`updatedAt`, cap 5, `asyncio.Lock`

### Ticket 026 — Prototype: UI hibrido + purga [wayfinder:prototype] — CERRADO 2026-08-23
**Question:** ¿Como se ve sync? Badge `local/server synced`, lista galeria con origen, boton `Borrar todos` con confirm que emite `purge` y limpia ambos. Throwaway `prototype-enrollment-hibrido.html` linkeado.
**Bloquea:** 027
**Estado:** cerrado — ver [026](tickets/026-prototype-ui-hibrido.md) — Tabla elegida, double-click prototype

### Ticket 027 — Task: Implementar WS handlers + persistencia + tests [wayfinder:task] — CERRADO 2026-08-23
**Question:** Trabajo no-decisivo: `ws.py` handlers `enroll_sync`/`purge`, `backend/models/identities.json` con `asyncio.Lock`, `app.py` `GET /identities` y `lifespan` load, `enrollment-panel.js` `localStorage` + `ws.send(enroll_sync)` + `onEnrollAck`, tests headless sin camara. HITL/AFK.
**Bloquea:** —
**Estado:** cerrado — ver [027](tickets/027-task-ws-persistencia.md) — `enroll_sync`→`enroll_ack` + `purge` broadcast verificado, `GET /identities` 0→1→0
