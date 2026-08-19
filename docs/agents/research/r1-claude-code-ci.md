# R1 — Cómo ejecutar Claude Code headless/no-interactivo en un runner de GitHub Actions

Fecha: 2026-08-18. Investigación contra fuentes primarias (docs oficiales de Claude Code, repo `anthropics/claude-code-action`, docs de GitHub Actions).

## Pregunta

¿Cómo ejecutar Claude Code de forma headless/no interactiva en un runner de GitHub Actions? Cubre instalación, autenticación, flags headless, modo print vs. agente, límites y costos, push a rama + PR desde CI, modelo recomendado y "gotchas".

## Hallazgos

### 1. Instalación

- La vía documentada como **recomendada** por Anthropic es el instalador nativo (`curl -fsSL https://claude.ai/install.sh | bash`; Windows PowerShell `irm https://claude.ai/install.ps1 | iex`), que auto-actualiza en background. La instalación por `npm install -g @anthropic-ai/claude-code` **también es oficial**: como de v2.1.198 el paquete npm requiere **Node.js 22+**, pero en runtime descarga un binario nativo que no usa Node. No usar `sudo npm install -g` (problemas de permisos/seguridad). Fuente: https://code.claude.com/docs/en/setup
- En un runner NO hace falta instalar nada a mano si se usa la acción oficial: `anthropics/claude-code-action` instala/ejecuta Claude Code automáticamente en el runner (`path_to_claude_code_executable` permite inyectar un ejecutable propio). Fuente: https://github.com/anthropics/claude-code-action y https://github.com/anthropics/claude-code-action/blob/main/docs/faq.md

### 2. Autenticación

- Para CI/scripts se usa `ANTHROPIC_API_KEY` (header `X-Api-Key`); en modo no-interactivo (`-p`) la key siempre se usa si está presente. La precedencia de credenciales es: cloud provider (Bedrock/Vertex/Foundry) > `ANTHROPIC_AUTH_TOKEN` (bearer, para gateways) > `ANTHROPIC_API_KEY` > `apiKeyHelper` > `CLAUDE_CODE_OAUTH_TOKEN` > login OAuth por `/login`. Fuente: https://code.claude.com/docs/en/authentication
- Alternativa con suscripción (Pro/Max/Team/Enterprise): `claude setup-token` genera un **token OAuth longevo (1 año)** que se setea como `CLAUDE_CODE_OAUTH_TOKEN`. Es para CI donde no hay login por browser. Ojo: **bare mode no lee `CLAUDE_CODE_OAUTH_TOKEN`** — con `--bare` hay que usar `ANTHROPIC_API_KEY` o `apiKeyHelper`. Fuente: https://code.claude.com/docs/en/authentication
- Otras env vars relevantes: `ANTHROPIC_BASE_URL` (ruta de requests, para gateways), `ANTHROPIC_MODEL` (modelo por sesión), `ANTHROPIC_DEFAULT_OPUS/SONNET/HAIKU_MODEL` (pin de alias), `MAX_THINKING_TOKENS`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`. Fuentes: https://code.claude.com/docs/en/model-config y https://code.claude.com/docs/en/env-vars
- En GitHub Actions los secretos se guardan como `ANTHROPIC_API_KEY` o `CLAUDE_CODE_OAUTH_TOKEN` y se pasan a los inputs `anthropic_api_key` / `claude_code_oauth_token` de la acción. Nunca commitear keys. Fuente: https://code.claude.com/docs/en/github-actions

### 3. Flags headless

- `-p` / `--print`: modo no-interactivo; imprime la respuesta y sale. Exit code 0 en éxito, distinto de 0 en fallo. Requerido para scripting/CI (sin `-p` abre la TUI y "cuelga"). Fuente: https://code.claude.com/docs/en/headless y https://code.claude.com/docs/en/cli-reference
- `--dangerously-skip-permissions`: saltea todos los prompts de permiso; **equivale a `--permission-mode bypassPermissions`**. Solo en entornos aislados (CI/container) y con input confiable. Fuente: https://code.claude.com/docs/en/cli-reference
- `--permission-mode`: acepta `default` (alias `manual`), `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`. Para `-p` el modo inicial es `default`/Manual si no se especifica, así que hay que pasarlo explícitamente. `dontAsk` (denegar todo lo que no esté en allow) es útil para CI "locked-down". Fuente: https://code.claude.com/docs/en/cli-reference y https://code.claude.com/docs/en/headless
- `--output-format`: `text` (default), `json`, `stream-json`. Con `json` el payload incluye `total_cost_usd` y breakdown por modelo (estimación client-side). Con `--json-schema` se puede validar salida estructurada (útil para gates de CI). Fuente: https://code.claude.com/docs/en/headless
- `--max-turns`: límite de turns agénticos (solo print mode); **exits con error al alcanzar el límite**. Sin límite por default. Fuente: https://code.claude.com/docs/en/cli-reference
- `--allowedTools`: lista de tools que corren sin prompt (sintaxis de permission rule, ej. `"Bash(git diff *)"` — el `*` con espacio previo habilita prefix matching). `--disallowedTools` y `--tools` restringen. Fuente: https://code.claude.com/docs/en/headless y https://code.claude.com/docs/en/cli-reference
- Complementos recomendados para CI: `--bare` (arranque más rápido y determinista: no lee hooks/skills/plugins/MCP/CLAUDE.md del host; se volverá default de `-p`), `--max-budget-usd` (tope de gasto, solo print mode), `--append-system-prompt`. Fuente: https://code.claude.com/docs/en/headless y https://code.claude.com/docs/en/cli-reference

### 4. Modo print vs. modo agente; ejecución no interactiva

- **Print mode (`-p`)**: un prompt, respuesta a stdout, sale. Lee stdin: `cat build-error.txt | claude -p "explica" > out.txt`. El stdin pipeado está limitado a **10MB** (pasarlo sale con error). Para inputs grandes, escribir a archivo y referenciar la ruta en el prompt. Fuente: https://code.claude.com/docs/en/headless
- `claude -p` igualmente puede ser **agéntico multi-turn**: con `--allowedTools`/`--permission-mode` y `--max-turns` puede editar archivos, correr tests, commitear. Heredoc: se puede pasar el prompt multilínea por argumento o por stdin. Fuente: https://code.claude.com/docs/en/headless y https://code.claude.com/docs/en/cli-reference
- **En la acción `anthropics/claude-code-action@v1`**, el modo lo decide el workflow: **interactive mode** (sin input `prompt`) responde a `@claude` en issues/PRs; **automation mode** (con input `prompt`) corre automático en cualquier evento (incluido cron) y por default escribe resultados al log del run. Fuente: https://code.claude.com/docs/en/github-actions y https://github.com/anthropics/claude-code-action/blob/main/docs/custom-automations.md
- En `-p` no hay diálogo de trust de workspace: igual corren los hooks de `.claude/settings.json` del proyecto y los servers de `.mcp.json` (sin prompt de aprobación). `--bare` evita cargarlos. Fuente: https://code.claude.com/docs/en/headless

### 5. Límites y costos

- Facturación por tokens de API; con OAuth token el uso va contra la suscripción. En el run se consumen además los **GitHub Actions minutes**. Fuente: https://code.claude.com/docs/en/github-actions (sección "Manage costs")
- Controles: `--max-turns` y `--max-budget-usd` (tope en USD, solo print mode; gasto de subagentes cuenta para el cap), `--allowedTools` para acotar superficie, workflow timeouts y concurrency de GitHub para evitar runs runaway. Fuente: https://code.claude.com/docs/en/cli-reference y https://code.claude.com/docs/en/github-actions
- Rate limits de la API: Anthropic recomienda TPM/RPM por usuario según tamaño de equipo (ej. 200k–300k TPM y 5–7 RPM por usuario para equipos de 1–5); los límites son a nivel organización. Existen `system/api_retry` events con categorías como `rate_limit`, `overloaded`, `billing_error` para manejo programático. Fuente: https://code.claude.com/docs/en/costs y https://code.claude.com/docs/en/headless
- El caching de prompts reduce costo de contexto repetido; el costo escala con el contexto (CLAUDE.md, historial de conversación). `total_cost_usd` en `--output-format json` permite trackear por invocación. Fuente: https://code.claude.com/docs/en/costs y https://code.claude.com/docs/en/headless
- Modelos disponibles: aliases `default`, `best`, `fable`, `opus`, `sonnet`, `haiku`, `sonnet[1m]`, `opus[1m]`, `opusplan`. En la API de Anthropic, `opus` → Opus 5, `sonnet` → Sonnet 5; el default por cuenta es Sonnet 5 (Pro/Team Standard) u Opus 5 (Max/API). Fuente: https://code.claude.com/docs/en/model-config

### 6. Push a rama y apertura de PR desde CI

- **Con la acción oficial**: Claude hace commits en una rama y **linkea a una página de creación de PR pre-cargada** — por diseño la acción NO crea el PR directamente (para respetar branch protection y dar control humano). Comportamiento de ramas: issue → crea rama nueva; PR abierto → pushea a la rama del PR; PR cerrado → rama nueva. Usa clones shallow (PR: `--depth=20`, ramas nuevas: `--depth=1`). Fuente: https://github.com/anthropics/claude-code-action/blob/main/docs/capabilities-and-limitations.md y https://github.com/anthropics/claude-code-action/blob/main/docs/faq.md
- La acción autentica como **Claude GitHub App** (claude[bot]) por default: requiere `id-token: write` en el workflow. No se debe pasar `github_token: ${{ secrets.GITHUB_TOKEN }}` porque los commits hechos con `GITHUB_TOKEN` **no disparan workflows subsiguientes** (el actor `github-actions` no puede re-triggerear). Alternativas: token de GitHub App propia (inputs `bot_id`/`bot_name`) o PAT. Fuente: https://code.claude.com/docs/en/github-actions (troubleshooting) y https://github.com/anthropics/claude-code-action/blob/main/docs/faq.md
- Para **CI runs completos disparados por commits de Claude**: el workflow debe escuchar los eventos que generan sus pushes (`push`/`pull_request`). Si la CI no corre, casi siempre es por el tema de `GITHUB_TOKEN` vs. app token. Fuente: https://code.claude.com/docs/en/github-actions (troubleshooting)
- **Con `claude -p` directo en un workflow** (sin la acción): hay que manejar git a mano — `git config user.name`/`user.email`, push con credenciales (PAT almacenado como secret; el `GITHUB_TOKEN` sirve para push pero no re-triggerea workflows) y abrir el PR con `gh pr create` (se autentica con `GH_TOKEN`/`GITHUB_TOKEN`). Fuente: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication y https://code.claude.com/docs/en/headless (ejemplos de `git diff main | claude -p`)
- La acción `github_token` (si se provee) también requiere `id-token: write` para WIF del GitHub App; si se pasa un `github_token` custom, los comentarios aparecen con el user de ese token y los sticky comments dejan de funcionar. Fuente: https://github.com/anthropics/claude-code-action/blob/main/docs/faq.md
- Limitaciones de git de la acción: **no** hace merge, rebase, force push ni operaciones destructivas (enforced en system prompt, incluso con tools permitidas); no puede pushear a otros repos (token sandboxed al repo actual). Fuente: https://github.com/anthropics/claude-code-action/blob/main/docs/capabilities-and-limitations.md y https://github.com/anthropics/claude-code-action/blob/main/docs/faq.md

### 7. Modelo recomendado para implementación de código

- **Sonnet** es el recomendado para tareas de codificación diarias: "Sonnet handles most coding tasks well and costs less than Opus". Opus queda para decisiones de arquitectura o razonamiento multi-paso; Haiku para tareas simples. Fuente: https://code.claude.com/docs/en/costs (sección "Choose the right model")
- En la API de Anthropic, `--model sonnet` resuelve a **Sonnet 5** (alias que apunta al recomendado por provider; pin con `ANTHROPIC_DEFAULT_SONNET_MODEL`). El alias `opusplan` usa Opus para planear y Sonnet para ejecutar. Los ejemplos oficiales de la acción usan `--model claude-sonnet-5` (antes `claude-4-0-sonnet`). Fuente: https://code.claude.com/docs/en/model-config y https://github.com/anthropics/claude-code-action/blob/main/docs/usage.md

### 8. Limitaciones y "gotchas" de Claude Code en CI headless

- **Sin `-p` cuelga**: si falta `-p`, arranca la TUI interactiva esperando input y el job se queda colgado. Fuente: https://usingclaude.com/en/claude-code/examples/claude-code-headless-mode-automation (patrón conocido; ver también https://code.claude.com/docs/en/headless)
- **`--dangerously-skip-permissions` es tan riesgoso como suena**: saltea TODOS los prompts; con input no confiable (texto externo en el prompt) puede editar/borrar archivos inesperadamente. Usar solo en entorno aislado y con `--allowedTools`/`--permission-mode` más acotados si es posible. Fuente: https://code.claude.com/docs/en/cli-reference
- **TTY / permisos**: `-p` no muestra diálogos de trust; los hooks de `.claude/settings.json` y MCP del proyecto corren igual (bare mode para CI determinista). En Windows pre-v2.1.211 un stdin ilegible crasheaba; hoy imprime warning y sigue. Tasks de background (ej. dev server) se terminan ~5s después del resultado final; subagentes quedan cap de 10 min (default). Fuente: https://code.claude.com/docs/en/headless
- **stdin pipeado limitado a 10MB**; excederlo sale con error no-cero. Fuente: https://code.claude.com/docs/en/headless
- **Login/keys en CI**: errores de autenticación en CI casi siempre son por `ANTHROPIC_API_KEY` no seteada en el shell del runner, o por mezclar bare mode con `CLAUDE_CODE_OAUTH_TOKEN`. Fuente: https://code.claude.com/docs/en/authentication y https://code.claude.com/docs/en/headless
- **Gotchas específicos de la acción**: (a) requiere `id-token: write` para la autenticación default por GitHub App; (b) el Bash tool está **deshabilitado por default** (hay que habilitar con `--allowedTools "Bash(...)"`); (c) la GitHub App de Claude **no tiene write sobre workflow files** (no puede modificar CI/CD) ni puede aprobar PRs ni submitear PR reviews; (d) solo responde al trigger phrase como palabra completa (`@claude`, no `@claude-bot`); (e) solo usuarios con write access (o `allowed_non_write_users`) disparan, y los bots están bloqueados salvo `allowed_bots` (evita loops); (f) el app token está sandboxed al repo actual; (g) la acción configura 2 MCP servers (GitHub + file ops) pero sus tools requieren `--allowedTools` explícito; (h) con `actions: read` + `additional_permissions` puede ver resultados de CI. Fuente: https://github.com/anthropics/claude-code-action/blob/main/docs/faq.md, https://github.com/anthropics/claude-code-action/blob/main/docs/capabilities-and-limitations.md, https://code.claude.com/docs/en/github-actions
- **Modelos nuevos pueden tener fallback automático**: Fable 5/Opus 5 tienen classifiers de seguridad (cyberseguridad/biología) que pueden re-rutear o rechazar requests; en no-interactivo un request flaggeado termina el turn con refusal. Fuente: https://code.claude.com/docs/en/model-config
- **Rate limits** a nivel organización: uso alto concurrente (ej. muchos agents en CI) puede chocar contra el TPM/RPM del org; conviene pedir allocation acorde. Fuente: https://code.claude.com/docs/en/costs

## Recomendación

Para este proyecto (Embodied AI):

1. **Usar la acción oficial `anthropics/claude-code-action@v1`** (modo automation con input `prompt`) en vez de invocar `claude -p` a mano: maneja instalación, autenticación GitHub (Claude GitHub App + `id-token: write`), push de commits y link de PR. Es la vía documentada y mantenida por Anthropic.
2. **Autenticación**: secret `ANTHROPIC_API_KEY` (API key) o `CLAUDE_CODE_OAUTH_TOKEN` (suscripción, vía `claude setup-token`) en el repo; pasarlo al input correspondiente. No usar `GITHUB_TOKEN` como `github_token` de la acción.
3. **Modelo**: `--model sonnet` (Sonnet 5 en API de Anthropic) para implementación de código en CI; reservar `opus`/`opusplan` para razonamiento/arquitectura.
4. **Acotar el agente**: en `claude_args` usar `--max-turns N`, `--max-budget-usd M`, `--allowedTools` mínimo (habilitar `Bash(...)` explícitamente, con prefix matching) y evitar `--dangerously-skip-permissions` salvo entorno 100% aislado y controlado.
5. **Si se necesita `claude -p` directo** (scripts/gates): añadir `--bare --output-format json` para determinismo y parsing; setear `ANTHROPIC_API_KEY` en el job; manejar git/push/PR con PAT + `gh pr create` fuera del agente.
6. **PRs**: la acción pushea a rama y deja el PR pre-cargado (control humano); si se quiere PR automático, crear un paso posterior con `gh pr create` (el `GITHUB_TOKEN` alcanza para crear el PR; los commits que disparan CI deben usar app token/PAT, no `GITHUB_TOKEN`).

## Fuentes

- Claude Code — Headless / programmatic: https://code.claude.com/docs/en/headless
- Claude Code — CLI reference: https://code.claude.com/docs/en/cli-reference
- Claude Code — GitHub Actions: https://code.claude.com/docs/en/github-actions
- Claude Code — Authentication: https://code.claude.com/docs/en/authentication
- Claude Code — Setup (instalación, npm): https://code.claude.com/docs/en/setup
- Claude Code — Model configuration: https://code.claude.com/docs/en/model-config
- Claude Code — Costs: https://code.claude.com/docs/en/costs
- Repo `anthropics/claude-code-action` (README): https://github.com/anthropics/claude-code-action
- Acción — Usage guide (inputs): https://github.com/anthropics/claude-code-action/blob/main/docs/usage.md
- Acción — Custom automations: https://github.com/anthropics/claude-code-action/blob/main/docs/custom-automations.md
- Acción — Capabilities & limitations: https://github.com/anthropics/claude-code-action/blob/main/docs/capabilities-and-limitations.md
- Acción — FAQ (gotchas): https://github.com/anthropics/claude-code-action/blob/main/docs/faq.md
- Acción — Setup guide: https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md
- GitHub Docs — Automatic token authentication (GITHUB_TOKEN): https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
