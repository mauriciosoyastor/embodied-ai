# Contribuir

Gracias por aportar al roadmap de **Embodied AI / AIoT**.

## Flujo de trabajo

1. Creá un branch con nombre descriptivo (`git checkout -b fix/nombre` o `feature/nombre`).
2. Hacé tus cambios siguiendo el checklist de calidad.
3. Abrí un PR contra `main` usando la plantilla del repo.

## Checklist de calidad

Todo PR debe pasar localmente antes de abrirse:

- `ruff check .`
- `ruff format --check .`
- `mypy fase-0`
- `pytest`
- `pre-commit run --all-files`

El CI (GitHub Actions) corre estos mismos checks y es obligatorio para mergear.

## Convenciones

- **Type hints**: el código Python usa anotaciones de tipos (Python 3.12+).
- **Commits**: mensajes en español, describiendo el qué y el porqué.
- **Documentación**: si cambiás comportamiento, actualizá la guía o README correspondiente.

## Dudas

Usá una issue con la plantilla **Pregunta / aprendizaje**.
