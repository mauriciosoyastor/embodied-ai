# Embodied AI / AIoT — Roadmap de Aprendizaje

Roadmap de aprendizaje en **Inteligencia Artificial Corpórea (Embodied AI)** e **AIoT**: un plan ejecutable de qué construir y en qué orden, donde cada fase cierra con un **hito** (proyecto mínimo que corre y se entiende).

## Contenido

- **Guía Maestra**: documento principal con el roadmap completo de aprendizaje.
- **CONTEXT.md**: glosario de dominio del proyecto.
- **Fase 0 — Fundamentos**: prerrequisitos — Python, git/GitHub, Linux y Docker.

## Estructura del repo

```
├── fase-0/               # Fase 0: fundamentos (Python, git, Linux, Docker)
├── docs/agents/          # Convenciones del issue tracker (GitHub Issues)
├── .github/              # CI, plantillas de issues/PR y Dependabot
├── CONTEXT.md            # Glosario de dominio
├── CONTRIBUTING.md       # Cómo contribuir
└── pyproject.toml        # Configuración de Python (ruff, mypy, pytest)
```

## Cómo correr la Fase 0

```bash
pip install -e ".[dev]"
python fase-0/main.py fase-0/ejemplo.txt   # conteo de palabras
pytest                                     # tests
```

## Calidad

Cada PR pasa por CI (GitHub Actions) con: **ruff** (lint + format), **mypy** (typecheck estricto) y **pytest**. Localmente, pre-commit aplica los checks de ruff y de higiene.

## Licencia

MIT — ver [LICENSE](LICENSE).
