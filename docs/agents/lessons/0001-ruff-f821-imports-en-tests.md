# 0001 — Imports explícitos en tests que llaman otro módulo (ruff F821)

**Status**: active (2026-08-21, PRs #58/#59 bloqueados por CI `quality` + `webcam-ci`).

## Síntoma

CI falla en el primer paso de lint:

- `quality` → `ruff check .` exit 1
- `webcam-ci` → `uv run ruff check plataforma/webcam` exit 1

Mensaje típico: `F821 Undefined name 'run_inference'` / `F821 Undefined name 'ws_mod'`.
Format, mypy y pytest no llegan a correr (skipped).

## Causa

Un test **usa** un símbolo de otro módulo (p. ej. `run_inference` de `plataforma.webcam.backend.ws`) pero **no lo importa** en ese scope. Un comentario del estilo `# ws.run_inference usa…` no define el nombre para ruff.

Ocurrió en `test_gesture.py` / `test_yolo.py` (tests S2-A que ejercitan la seam de S2-B).

## Regla

Todo nombre que el test **llame** debe estar definido en ese archivo: import de módulo o `from … import …` (top-level o al inicio de la función del test).

## Check antes de push

```bash
uv run ruff check .
uv run ruff check plataforma/webcam
```

Ambos deben pasar en verde. Compleción: cero `F821` en el output.

## Incorrecto / correcto

```python
# incorrecto — F821: run_inference no está definido
def test_ws_run_inference_gesto_allowed_via_stub() -> None:
    """ws.run_inference debe retornar gesto…"""
    _boxes, gesto = run_inference(dummy_jpeg, frame_id=42, ts=1)
```

```python
# correcto — import en el mismo scope que usa el símbolo
def test_ws_run_inference_gesto_allowed_via_stub() -> None:
    """ws.run_inference debe retornar gesto…"""
    from plataforma.webcam.backend.ws import run_inference

    _boxes, gesto = run_inference(dummy_jpeg, frame_id=42, ts=1)
```

```python
# correcto — alias de módulo si el test monkeypatchea
import plataforma.webcam.backend.ws as ws_mod

boxes, gesto = ws_mod.run_inference(...)
```

## Referencia

Fix aplicado en ramas `agent/51-s2-b-websocket-envelope` y `agent/53-s2-d-frontend-overlay` (2026-08-21).
