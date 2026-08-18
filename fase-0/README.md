# Fase 0 — Fundamentos

Primera fase del roadmap de aprendizaje en **Embodied AI / AIoT**.

Objetivo: construir los cimientos — Python, git/GitHub, Linux y Docker — antes de tocar orquestación cognitiva, percepción y robótica.

## Orden de aprendizaje

1. Python (mini-hito 1) → `GUIA-python.md`
2. git y GitHub (mini-hito 3, parte 1) → `GUIA-git.md`
3. Linux con WSL2 (parte 3) → `GUIA-linux.md`
4. Docker (mini-hito 2) → `GUIA-docker.md`

## Mini-hitos

- [ ] **Mini-hito 1**: script Python propio que corre (`contar_palabras.py` + `main.py` es el ejemplo).
- [ ] **Mini-hito 2**: contenedor Docker que levanta tu script (el `Dockerfile` es el ejemplo).
- [ ] **Mini-hito 3**: repo en GitHub con tus archivos versionados.

## Cómo correr el ejemplo

Con Python:
```
python main.py ejemplo.txt
```

Con tests:
```
python -m pytest test_contar_palabras.py
```

Con Docker:
```
docker build -t fase-0-ejemplo .
docker run --rm fase-0-ejemplo
```

## Contexto

Decisiones y roadmap en los issues del repo de GitHub (mapa wayfinder con label `wayfinder:map` y tickets). Ver `docs/agents/issue-tracker.md` para las convenciones del tracker.
