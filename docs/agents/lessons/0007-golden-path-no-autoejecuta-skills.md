# 0007 — Golden Path no auto-ejecuta skills: usar `/golden-path`

**Status**: active (2026-09-03). Llamar a `golden path` vía `pytest` no dispara skills.

## Síntoma

Corrés `pytest tests/test_golden_path_puro.py` (o `harness verify`) y ninguna
skill Matt (`triage`/`wayfinder`/`to-tickets`/`tdd`/`code-review`) se ejecuta.

## Causa

El test es seam `CI+Harness` (configs + purga + `verify`), no orquestador.
Las skills viven a nivel agente (tool `skill`), no como funciones Python
importables desde el test.

## Regla

- Para verificar el seam: `pytest tests/test_golden_path_puro.py`.
- Para ejecutar el pipeline: `/golden-path <issue|texto>` en el TUI
  (`.opencode/commands/golden-path.md`, secuencia ADR-0007/ADR-0008).
- Anti-solape: `wayfinder` solo con niebla, `to-tickets` trocea una vez,
  `gitnexus-plan` detalla por ticket, reviews en una sola pasada.

## Check antes de push

```bash
uv run pytest tests/test_golden_path_puro.py -q
# Compleción: 5/5 en verde; si falla, ver seam CI+Harness, no las skills
```

## Referencia

Pregunta 2026-09-03: "xq al llamar a golden path no se ejecutan las skills".
Resolución: comando `/golden-path` + ADR-0008 + ajuste de glosario.
