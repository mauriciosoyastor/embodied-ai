# Lección 0006 — Reuse selectivo vs dependencia (hibrido enrollment)

- **Síntoma:** querer `pip install human`/`deepface` para `localStorage`+`purge` trae `dlib` no-win32, `Postgres`/`Redis`, bundles 22-41MB y rompe `uv.lock`/`mypy strict`/`conftest.py`/`LeakyQueue N=1`/`ABORTED N=5`.
- **Causa:** repos 2026-04-25 (`brainwagon/face-recognition` 128-d `0.55`) y 2025 (`CompreFace` 8.1k, `deepface` 23.3k) resuelven trozos (cuaderno **o** fichero **o** WS) pero ninguno `hibrido completo` (`EnrollSync`+`PendingSync`+`Bypass N=1`+`GET /identities`+`IdentitiesStore` cap 5) con `12/12` ingeniería.
- **Solución:** `copy-paste` 2-10 líneas con `// inspirado en human faceid` + MIT atribución: validación `faceid`, `purge` broadcast, `Float32Array→Array` (`brainwagon` 512B/persona), threshold `0.40→0.42` (`face-embedding.js:9`). Mantener `asyncio.Lock`+`tmp→replace` + `PendingSync` propios.
- **Regla:** priorizar `12/12` ingeniería sobre `stars`; si repo <12/12, no dependencia, solo snippet + `docs/adr/0004` y `CONTEXT.md:89`.
