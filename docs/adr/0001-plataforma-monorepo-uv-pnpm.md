# 0001 — Plataforma como monorepo modular desacoplado con uv y pnpm

La plataforma virtual de entrenamiento vive en `plataforma/` como un monorepo modular desacoplado: `backend/` (FastAPI), `frontend/` (Vite 6 + TypeScript 5 + Three.js, Node 22 LTS) y `sim/` (MuJoCo/Gymnasium), cada subsistema autocontenido y sin dependencias cruzadas. Se eligió `uv` (workspace) para todo el Python y `pnpm` para el frontend, con locks (`uv.lock`, `pnpm-lock.yaml`) commiteados para builds reproducibles.

**Status**: accepted (2026-08-19, ticket D4 — estructura del repo plataforma/ + CI con path filtering).

**Considered Options**:
- **Raíz con setuptools+pip** (convención actual del repo): descartada — no aísla los runtimes y mezcla los bindings C++ de MuJoCo con el entorno de la API web.
- **Múltiples archivos de workflow**: descartado — un solo `ci.yml` con `dorny/paths-filter` consolida el pipeline en la UI de PRs y centraliza los disparadores.

**Consequences**:
- El CI raíz se acota a `fase-0 fase-1` (ruff/mypy); los jobs de plataforma corren con sus propios toolchains.
- La interacción `sim → backend` exige contratos de datos explícitos (Pydantic/OpenAPI) para no reintroducir acoplamiento.
- `Dockerfile` solo en `plataforma/backend/`; el dev local usa procesos nativos (`uv run uvicorn`, `pnpm dev`).
