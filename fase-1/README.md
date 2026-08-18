# Fase 1 — Cerebro Central Local y Orquestación Cognitiva

Primer ladrillo de la Fase 1 de la Guía Maestra: conectar un LLM (Gemini de
Google AI Studio) desde Python. Acá se aprende a guardar secretos fuera del
repo (`.env`), a consumir una API con SDK y a testear sin red.

## Hito

`python main.py "tu prompt"` responde con texto generado por Gemini usando tu
clave de API.

## Setup

```bash
pip install -e ".[fase1]"
```

## Configuración

1. Creá tu API key en [Google AI Studio](https://aistudio.google.com/apikey).
2. Copiá `.env.example` a `.env` y pegá tu clave:

```bash
copy .env.example .env   # Windows
```

3. Editá `.env`:

```
GOOGLE_API_KEY=tu-clave-aqui
```

> `.env` está en `.gitignore`: la clave nunca se sube al repo.

## Uso

```bash
python main.py "Explicame que es un StateGraph en una frase"
```

## Test

```bash
pytest fase-1        # sin red: todo mockeado
```

## Arquitectura

- `gemini_client.py` — carga la clave, crea el cliente y expone `responder`.
- `main.py` — CLI de una línea.
- `test_gemini_client.py` — tests con `unittest.mock` (sin API key ni red).

Siguiente paso del hito de Fase 1: un orquestador local con Pydantic AI que
inyecte dependencias (ver Guía Maestra).
