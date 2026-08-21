# 0002 — Expresiones GitHub Actions: sin `| int` estilo jq

**Status**: active (2026-08-21). Cada push a `main` falla el workflow `.github/workflows/agent-review.yml`.

## Síntoma

En Actions aparece un run fallido distinto de `CI`, p. ej. `.github/workflows/agent-review.yml`, con anotación:

`Invalid workflow file: Unexpected symbol: '|'. ... (steps.review.outputs.iteration | int) < 3`

El job `CI` puede estar verde; el fallo es de **parseo del YAML de workflow**, no del código de la app.

## Causa

Las expresiones de GitHub Actions **no** soportan el pipe de jq (`| int`). Eso es sintaxis de `jq`/filtros, no de `${{ }}`.

## Regla

Para comparar un output numérico en `if:` usá `fromJSON(...)` (o comparación directa si el valor ya es número JSON):

```yaml
# correcto
if: steps.review.outputs.verdict == 'request_changes' && fromJSON(steps.review.outputs.iteration) < 3

# correcto (límite superior)
if: steps.review.outputs.verdict == 'request_changes' && fromJSON(steps.review.outputs.iteration) >= 3
```

```yaml
# incorrecto — rompe el workflow al cargar
if: steps.review.outputs.verdict == 'request_changes' && (steps.review.outputs.iteration | int) < 3
```

## Check antes de push

Si tocás `.github/workflows/*.yml`:

1. Abrí el archivo en el editor de GitHub o corré un push a una rama de prueba.
2. Compleción: el workflow aparece en Actions sin anotación `Invalid workflow file`.

## Referencia

Fallos en main tras merge #58/#59: runs `32451950582`, `32452020032`.
