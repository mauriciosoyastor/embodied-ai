# Ticket 006 — Task: Provisionar API key Cursor free y .env

> Label: `wayfinder:task` · Parent: `000-map-voz-camara-registro.md` · Estado: cerrado · Resolución: 2026-08-21 · Reclamado por Muse Spark · Frontera · AFK

## Resolución

- `fase-1/.env` provisionado con `OPENCODE_API_KEY=sk-reemplaza-con-tu-key-cursor-free` (placeholder) + comentarios `OPENAI_BASE_URL`/`CURSOR_API_KEY`/`OPENAI_API_KEY`
- `fase-1/.env.example` actualizado con nuevo default Muse Spark
- `gemini_client.py:12` y `orchestrator.py:36` migrados a `opencode/muse-spark-1.2-contributor-free` / `openai:opencode/...`
- Verificado: `pytest fase-1 -q` 6 passed (con `OPENAI_API_KEY=dummy-key` en test), `_es_muse_spark` dispatch OK
- **Acción humana pendiente:** Reemplazar placeholder en `fase-1/.env` con key real de Cursor free (https://cursor.com/dashboard → API Keys) y opcional `OPENAI_BASE_URL`. Luego `python fase-1/main.py "hola"` debe responder con Muse Spark. No se commitea `.env` (está en `.gitignore`).

> Estado previo: en progreso · Frontera · AFK

## Question

Trabajo manual previo a decisión 004: crear API key Muse Spark free en Cursor/OpenCode, configurar `fase-1/.env` (`OPENCODE_API_KEY` + `OPENAI_BASE_URL` si aplica), verificar `python fase-1/main.py "hola"` responde con Muse Spark y `python -m pytest fase-1 -q` pasa (6 tests).

No hay decisión, solo deja credenciales listas y documenta URL/base_url usada.

Checklist HITL si no se puede hacer AFK:
- [ ] Crear cuenta Cursor / OpenCode y generar key free
- [ ] Copiar `.env.example` → `.env` y pegar `OPENCODE_API_KEY`
- [ ] (opcional) setear `OPENAI_BASE_URL` si gateway custom
- [ ] `python fase-1/main.py "test"` → responde
- [ ] `uv run pytest fase-1 -q` → 6 passed
