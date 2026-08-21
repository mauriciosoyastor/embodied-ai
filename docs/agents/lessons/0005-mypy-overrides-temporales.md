# 0005 — Overrides temporales de mypy: retirar al aterrizar el módulo

**Status**: active (2026-08-21). `pyproject.toml` aún tiene override de `plataforma.webcam.backend.ws` aunque `ws.py` ya está en `main` (#58).

## Síntoma

```toml
[[tool.mypy.overrides]]
module = ["plataforma.webcam.backend.ws"]
ignore_missing_imports = true
```

queda en el árbol después de que el módulo real existe. Mypy deja de chequear ese archivo (o enmascara imports rotos). Comentarios tipo “temporal hasta S2-B” se vuelven sediment.

## Causa

Un agente añadió el override para desbloquear CI **antes** de que existiera `ws.py`, y el cleanup no se hizo en el PR que introdujo el módulo.

## Regla

Si agregás un override / skip / `# type: ignore` **temporal**:

1. Nombralo en el PR o ADR con condición de retiro (“quitar cuando exista `ws.py`”).
2. En el PR que aterriza el módulo: **borrá el override** en el mismo commit (o el inmediato).
3. Compleción: `uv run mypy plataforma/webcam` verde **sin** ese override.

## Check

```bash
rg "plataforma.webcam.backend.ws" pyproject.toml
# Si ws.py existe bajo plataforma/webcam/backend/, el override ignore_missing_imports de ese módulo no debe quedar.
```

## Referencia

ADR 0002 mencionaba override temporal de `ws`; post-merge #58 el archivo ya vive en main (`358713f`).
