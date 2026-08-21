# 0003 — Una sola carpeta viva del frontend webcam (sin siblings)

**Status**: active (2026-08-21). Local tenía `plataforma/frontend-prototype/` (dist + node_modules) mientras GitHub solo conoce `plataforma/webcam/frontend/`.

## Síntoma

- `git status` muestra untracked enorme bajo `plataforma/frontend-prototype/` (`node_modules/`, `dist/`).
- En GitHub, `plataforma/` solo lista `webcam` (+ `__init__.py`).
- Riesgo: un agente commitea el sibling o trabaja en el path viejo y el PR no coincide con el árbol canónico.

## Causa

Prototipos/spikes locales se dejaron al lado del path oficial en vez de reemplazarlo o borrarse. Viola la regla del repo: **un proyecto = una carpeta con git**; no crear siblings permanentes (`*-prototype`, `*-workshop`, clones extra).

## Regla

Fuente de verdad del visor webcam:

- Frontend: `plataforma/webcam/frontend/`
- Backend: `plataforma/webcam/backend/`

Si un spike termina absorbido por S2-D (o similar): borrá o ignorá el sibling local; no lo agregues al commit. No crees `plataforma/frontend-prototype/` “por las dudas”.

## Check antes de push

```bash
git status -u
# Compleción: no hay paths untracked bajo plataforma/*-prototype ni hermanos de webcam/
gh api repos/mauriciosoyastor/embodied-ai/contents/plataforma --jq '.[].name'
# Compleción: lista alineada con lo que vas a pushear (hoy: __init__.py, webcam)
```

## Incorrecto / correcto

| Incorrecto | Correcto |
|---|---|
| Editar `plataforma/frontend-prototype/` | Editar `plataforma/webcam/frontend/` |
| `git add plataforma/frontend-prototype` | Dejar el sibling fuera del stage / borrarlo |
| Segundo clone “para probar” | Worktree solo si el humano lo pide |

## Referencia

Comparación local vs `origin/main` 2026-08-21: sibling solo local; oficial ya merged vía #59.
