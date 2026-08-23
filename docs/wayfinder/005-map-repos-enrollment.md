# Wayfinder Map — Repos GitHub para Enrollment Hibrido

> Label: `wayfinder:map` · Estado: cerrado — way completo · Tracker: local-markdown · Creado: 2026-08-23 · Cerrado: 2026-08-23

## Destination

**Decisión cerrada** sobre qué **repos GitHub open-source** ya implementan enrollment facial hibrido `localStorage + backend JSON` con `WebSocket sync`, `face embedding 128-d`, `identities store` y gestión de purga, evaluados según **ingeniería de código completa** del repo (`CONTEXT.md` glosario, `docs/adr/`, `pyproject.toml`/`uv` workspace, `conftest.py`/`pythonpath`, `ruff`/`mypy strict`, `pytest` headless, `WS D5`/`LeakyQueue`, `ABORTED latch`, `histéresis N=5`) para reutilizar patrones sin re-inventar.

## Notes

- Dominio: Embodied AI platform · `plataforma/webcam` hibrido recién cerrado (mapa 004) como referencia; evaluar repos según `CONTEXT.md` términos (`EnrollSync`, `IdentitiesStore`, `Bypass LeakyQueue`, `PendingSync`, `Hidratación híbrida`, `Whiteboard`, `Bridge/Adapter`, `Monorepo desacoplado`)
- Skills a consultar: `research`, `grilling`, `domain-modeling`
- Preferencias: priorizar repos con tests reales, mypy/py.typed, CI path-filtered, sin secretos commiteados, licencia permisiva (MIT/Apache-2.0), commit <12 meses, ≥1k stars o referencia directa a `face-api.js`/`onnxruntime`/`mediapipe` + `localStorage`/`IndexedDB` + `WebSocket`
- Estado actual: mapa 004 cerrado (hibrido implementado y verificado `GET /identities` + WS `enroll_ack`/`purge_ack`), pero sin benchmarking externo

## Decisions so far

- [Research: Repos con enrollment hibrido — Ticket 028](tickets/028-research-repos-enrollment.md) — 5+1 repos (face-api.js 17.9k, human 3.3k IndexedDB, CompreFace 8.1k, deepface 23.3k, face_recognition 56k + brainwagon 2026-04-25), ninguno hibrido completo (2026-08-23)
- [Research: Ingeniería completa — Ticket 029](tickets/029-research-ingenieria.md) — 12 criterios: deepface 25% (3/12), resto 8-17% vs nuestro 100% conftest/uv/LeakyQueue/ABORTED (2026-08-23)
- [Grilling: Decisión qué reutilizar — Ticket 030](tickets/030-grilling-reutilizacion.md) — copy-paste 3 patrones (human purge, brainwagon Float32Array, deepface 0.40→0.42), descartar dlib/Postgres, ADR 0004 + lección 0006 (2026-08-23) — **mapa sin frontera**

## Not yet specified

<!-- fog graduado a tickets 028-030 -->

## Out of scope

- Repos que usan cloud facial (AWS Rekognition, Azure Face) — solo local/edge
- Repos que requieren entrenamiento de modelo propio — solo `mobilefacenet`/`ArcFace` 128-d
- Video grabación persistente y dataset biometria — privacy out-of-scope ya en 000/004

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos: `Bloquea:` = este ticket bloquea a otros.

### Ticket 028 — Research: Repos GitHub con enrollment hibrido resuelto [wayfinder:research] — CERRADO 2026-08-23
**Question:** ¿Qué repos GitHub (≥1k stars, MIT/Apache-2.0, <12m) ya resolvieron `localStorage`/`IndexedDB` + `backend JSON` + `WS` sync + `face embedding 128-d` + `purge`? Evaluar 4-6 repos con tabla (`stars`, `licencia`, `stack`, `store`, `WS`, `embedding`, `sync`, `purge`, `ultimo commit`) y lecciones para `enrollment-panel.js`/`identities.py`/`ws.py`.
**Bloquea:** 030
**Estado:** cerrado — ver [028](tickets/028-research-repos-enrollment.md) — 5+1 repos, ninguno hibrido completo

### Ticket 029 — Research: Ingeniería de código completa de esos repos [wayfinder:research] — CERRADO 2026-08-23
**Question:** Para los repos de 028, ¿cumplen ingeniería completa según nuestro repo (`ruff`/`mypy`/`pytest`, `conftest.py`+`pythonpath`, `uv` workspace, `LeakyQueue`/`ABORTED latch`, `ADR`/`CONTEXT`)? Tabla de madurez y gaps.
**Bloquea:** 030
**Estado:** cerrado — ver [029](tickets/029-research-ingenieria.md) — 12/12 vs 25% max

### Ticket 030 — Grilling: Decisión qué reutilizar y qué no [wayfinder:grilling] — CERRADO 2026-08-23
**Question:** Con 028/029, ¿qué patrones adoptar (ej. `asyncio.Lock`+`tmp→replace` vs `filelock`, `GET /identities` hidratación, `pending_sync`, `enroll_ack` broadcast) y qué descartar por no cumplir `win32`/`mypy strict`/`N=5`? Decidir `copy-paste` vs `dependencia` y crear ADR si aplica. HITL con `grilling` + `domain-modeling`. Bloqueado por 028,029.
**Bloquea:** —
**Estado:** cerrado — ver [030](tickets/030-grilling-reutilizacion.md) — copy-paste 3 patrones, ADR 0004, lección 0006
