# Ticket 025 — Grilling: Schema identities.json y embedding promediado

> Label: `wayfinder:grilling` · Parent: `004-map-enrollment-hibrido.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por Muse Spark · HITL

## Question

¿Schema `plataforma/webcam/backend/models/identities.json` `{id,nombre,embedding[128],count,updatedAt,source}` con promedio `new = (old*count + new)/(count+1)` L2-norm y threshold coseno 0.4? ¿File lock (`asyncio.Lock` en `ws.py`), carga en `app.py` `lifespan` al iniciar, y `GET /identities` para hidratacion inicial del frontend? Definir concurrencia (dos clientes mismo nombre) y limite tamaño. HITL. Bloqueado por 023.

## Resolución

**Decisión cerrada (Q1-Q5):**

- **Q1 Esquema:** `{id: nanoid, nombre, embedding: float[128], count, updatedAt: ISO, source}` — `count` para promedio móvil, `updatedAt` para ordenar `GET /identities` eficientemente.
- **Q2 Promedio L2 Cap 5:** `hat_e = normalize(e_old * min(N,5) + e_new)` / `min(N+1,6)` — balance adaptabilidad/robustez, no diluye infinito tras 5 enrolls.
- **Q3 Concurrencia atómica:** `asyncio.Lock` + `tmp→os.replace` en `win32` (sin `fcntl`), evita JSON corrupto por interrupción; `app.py` `lifespan` carga `identities.json` en `app.state.store` + `GET /identities`.
- **Q4 Identidad por ID:** clave primaria `id` (nanoid), nombre no único — soporta duplicados UI `Mauri #a1b2`, `purge` por `ids:[]` futuro.
- **Q5 LRU:** sin límite/expiración en fase 0, base pequeña; LRU queda en `Not yet specified` para futuro.

**Desbloquea:** 026

Respuestas: Q1 schema con count/updatedAt, Q2 L2 cap 5, Q3 Lock+tmp→replace, Q4 id distinto, Q5 sin límite.
