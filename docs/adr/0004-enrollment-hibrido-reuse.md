# ADR 0004 — Enrollment hibrido: reuse selectivo vs dependencia

- **Estado:** aceptado 2026-08-23
- **Contexto:** wayfinder 004 (hibrido `localStorage:webcam.identities` + `backend/models/identities.json` via `WS enroll_sync/purge`) y 005 (repos GitHub 2026-04-25 `brainwagon/face-recognition` + `CompreFace`/`deepface`/`human`/`face-api.js` + `Frigate`/`yakhyo`). Ninguno cubre exacto `EnrollSync`+`PendingSync`+`Bypass LeakyQueue N=1`+`GET /identities`+`IdentitiesStore` cap 5 con `12/12` ingeniería (`ruff`/`mypy`/`conftest.py`/`uv.lock`/`ABORTED N=5`/`COSINE 0.42`).
- **Decisión:** `copy-paste` selectivo con atribución MIT (validación `human` faceid, `purge` broadcast `CompreFace`, threshold `0.40→0.42` `deepface`, `Float32Array→Array` `brainwagon` 2026-04-25), descartar `dlib`/`Postgres`/`bundles 22-41MB`/`512-d`/`IndexedDB` migración. Mantener `asyncio.Lock`+`tmp→replace` + `Bypass N=1` + `PendingSync` propios.
- **Consecuencias:** preserva `win32`/`mypy strict`/`uv` + `12/12` ingeniería, evita dependencias pesadas y licencias non-commercial, requiere mantener `docs/agents/research/028|029` como evidencia y el glosario híbrido (término `EnrollSync`, detalle en ADR-0010).
