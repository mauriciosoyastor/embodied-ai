# 0008 — Citas a archivos que no existen: hook `citas-existen`

**Status**: active (2026-09-04). Los docs del Golden Path citaban archivos
ausentes en HEAD (caso ADR-0007 citado 4 veces, más `triage-labels.md`,
`test_golden_path_puro.py`, `harness/harness.py`).

## Síntoma

`docs/guides/golden-portable.md` decía "cada archivo citado existe aquí"
pero 6 citas no resolvían en HEAD. El índice GitNexus (otra rama) sí los
tenía, así que el grafo "los veía" y el disco no.

## Causa

Divergencia de ramas + verificación equivocada (`git ls-tree HEAD` mira la
foto vieja, no el índice activo) + ningún gate que valide citas.

## Regla

- Toda cita `docs/adr/*`, `docs/agents/*`, `tests/*.py`, `harness/*.py`
  en `.opencode/commands/*.md` o `docs/guides/golden-portable.md` debe
  existir en el worktree.
- Gate: hook local `citas-existen` en `.pre-commit-config.yaml`
  (script `.github/scripts/check-citas-existen.py`, stdlib, sin red).
- Verificación correcta tras restaurar: `git status` +
  `git diff --cached --stat` + `git ls-files --stage` +
  `git hash-object` vs `git rev-parse <commit>:<path>`. Nunca `ls-tree HEAD`
  para confirmar un stageado.

## Check antes de push

```bash
uv run python .github/scripts/check-citas-existen.py
# OK = 0 citas rotas; si falla, restaura el archivo o corrige la cita
```

## Referencia

Auditoría Golden Path 2026-09-04: 54/100, ticket 01 restauró el ADR-0007
desde el blob `2b5ee6d` (hash `8b5819e...` idéntico).
