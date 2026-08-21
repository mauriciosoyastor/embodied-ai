# 0004 — Artefactos locales: no commitear; ampliar `.gitignore`

**Status**: active (2026-08-21). Working tree local contaminado frente a GitHub limpio.

## Síntoma

`git status` muestra untracked que **no existen en `origin/main`**:

- `node_modules/` (Vite/npm)
- `dist/` (build frontend)
- `trajectory.jsonl` (orquestador OpenCode)
- `.opencode/node_modules/` (plugins locales)
- `README.init.md` (scaffold Opencode Free Agents, no es doc del producto)

Si se stagean, el PR explota en tamaño y CI puede lint/format basura.

## Causa

`.gitignore` del repo cubría Python/venv/secrets pero **no** artefactos Node ni traces de agentes.

## Regla

Antes de `git add` / commit:

1. Solo stageá fuente del producto y docs del repo.
2. Compleción: `git status` sin `node_modules`, `dist`, `trajectory.jsonl`, ni caches de herramientas.

Entradas mínimas en `.gitignore` (mantenerlas):

```gitignore
node_modules/
dist/
trajectory.jsonl
.opencode/node_modules/
```

## Check antes de push

```bash
git status -u --short | findstr /i "node_modules dist trajectory .opencode"
# Compleción: sin líneas (o solo paths que el humano pidió trackear a propósito)
```

## Referencia

Drift local 2026-08-21 tras S2 merges: GitHub limpio; disco local con prototype dist + opencode deps.
