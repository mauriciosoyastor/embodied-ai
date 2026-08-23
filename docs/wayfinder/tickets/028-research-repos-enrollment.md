# Ticket 028 — Research: Repos GitHub con enrollment hibrido resuelto

> Label: `wayfinder:research` · Parent: `005-map-repos-enrollment.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por subagente research · AFK

## Question

¿Qué repos GitHub (≥1k stars, MIT/Apache-2.0, <12m) ya resolvieron `localStorage`/`IndexedDB` + `backend JSON` + `WS` sync + `face embedding 128-d` + `purge`? Evaluar 4-6 repos con tabla (`stars`, `licencia`, `stack`, `store`, `WS`, `embedding`, `sync`, `purge`, `ultimo commit`) y lecciones para `enrollment-panel.js`/`identities.py`/`ws.py` según `CONTEXT.md` (`EnrollSync`, `IdentitiesStore`, `PendingSync`).

Entregable en rama `research/028-repos-enrollment` con `docs/agents/research/028-repos-enrollment.md`.

## Resolución

- Rama `research/028-repos-enrollment` — `docs/agents/research/028-repos-enrollment.md` (310 líneas, 5 repos)
- `face-api.js` 17.9k MIT archivado 2020, `human` 3.3k MIT IndexedDB 2024, `CompreFace` 8.1k Apache-2.0 Postgres 2026-02, `deepface` 23.3k MIT file+pgvector 2026-05, `face_recognition` 56k MIT pickle 2024 + brainwagon 2026-04-25 0 stars 128-d localStorage (actualizado 2026-08-23)
- Ninguno cubre exacto hibrido `localStorage+backend JSON+WS enroll_sync/purge+PendingSync+GET /identities+Bypass N=1`; recomendación copy-paste selectivo human/CompreFace/deepface + brainwagon 0.55→0.42, descartar bundles/dlib/Postgres

**Desbloquea:** 030
