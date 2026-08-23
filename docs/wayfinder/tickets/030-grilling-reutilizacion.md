# Ticket 030 — Grilling: Decisión qué reutilizar y qué no

> Label: `wayfinder:grilling` · Parent: `005-map-repos-enrollment.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por Muse Spark · HITL

## Question

Con 028/029, ¿qué patrones adoptar (ej. `asyncio.Lock`+`tmp→replace` vs `filelock`/`fcntl`, `GET /identities` hidratación, `pending_sync`, `enroll_ack` broadcast, `l2_normalize` cap 5) y qué descartar por no cumplir `win32`/`mypy strict`/`N=5`/`COSINE_THRESHOLD`? Decidir `copy-paste` vs `dependencia` y crear ADR si hard-to-reverse. HITL con `grilling` + `domain-modeling`. Bloqueado por 028,029.

## Resolución

**Decisión cerrada (Q1-Q5, actualizado 2026-08-23 con repos 2026-04-25):**

- **Q1 Adoptar (copy-paste 2-10 líneas):** validación multi-check `human` `faceid` → `evaluate()` `person>0.6` + `face inset` + `consent`, `purge` broadcast `CompreFace`/`deepface` (`DELETE` → `purge {all:true}` + `purge_ack`), threshold `0.40` `deepface` valida `COSINE_THRESHOLD 0.42` (`face-embedding.js:9`), y `Float32Array→Array` `brainwagon 2026-04-25` (`localStorage:face-recognition-enrollments-full` 512B/persona).
- **Q2 Descartar:** `dlib` (`ageitgey` no-win32), `Postgres/Redis` (`CompreFace`), bundles 22-41MB (`human`), `IndexedDB` migración (mantener `localStorage` + `pending_sync`), `512-d` (mantener `128-d` `mobilefacenet`), licencias non-commercial.
- **Q3 Forma:** `copy-paste` con atribución MIT `// inspirado en human faceid` sin dependencia — preserva `uv.lock` + `12/12` ingeniería (`conftest.py`/`pythonpath`, `LeakyQueue N=1`, `ABORTED N=5`, `WS D5`, `COSINE 0.42`/`CAP 5`).
- **Q4 ADR:** sí — `docs/adr/0004-enrollment-hibrido-reuse.md` (hard-to-reverse: `identities.json` + WS, surprising: por qué no `human` entero, trade-off 5+3 repos 2026).
- **Q5 Lección:** sí — `docs/agents/lessons/0006-reuse-selectivo.md` + índice `README.md` (no copiar bundles, validar threshold, `brainwagon` 0.55→0.42).

Respuestas: Q1 adoptar 3 patrones + brainwagon, Q2 descartar dlib/Postgres/bundles, Q3 copy-paste, Q4 ADR sí, Q5 lección sí.

**Desbloquea:** mapa 005 sin frontera (way completo).
