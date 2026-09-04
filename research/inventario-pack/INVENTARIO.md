# Inventario pack portable y seams de adaptación — research #158 (mapa #157)

Rama throwaway: `research/inventario-pack` desde `main@777588a` (local, sin push).
Verificado contra filesystem 2026-09-04. No cierra issue, no postea Answer.
Metodología skill `research`: solo fuentes primarias (archivos del repo), cada cita con ruta:línea verificada por Read/Bash.

## 1. Inventario por archivo (existe / rol / veredicto)

| # | Archivo | Existe | Rol (1 línea) | Veredicto |
|---|---------|--------|---------------|-----------|
| 1 | `.opencode/commands/golden-path.md` (43 lín.) | sí | Pipeline paso a paso Issue→triage→…→merge humano con gates HITL | **Verbatim-estructura / seam-contenido**: orden y DoD copiables; citas `docs/adr/0007:7`, `AGENTS.md:8`, `docs/agents/triage-labels.md:21`, `docs/agents/issue-tracker.md:21` son propias |
| 2 | `.opencode/commands/golden-auto.md` (50 lín.) | sí | Ráfaga autónoma local + panel Hecho/Pendiente tu OK, nunca auto push/PR/close | **Verbatim-estructura / seam-contenido**: doble zona y N=3 copiables; refs `docs/adr/0007:7`, `docs/adr/0009:8`, `golden-path.md:10` propias |
| 3 | `harness/harness.py` (733 lín.) | sí | Loop Plan-Execute-Verify con tiers, sensores y traza append-only | **Seam-mayor**: port de `scraperargenpro/harness/harness.py` (Ticket 06) adaptado; seams en `harness.py:32-64,266-281,343-440` |
| 4 | `harness/check_context.py` (38 lín.) | sí | Linter que bloquea `.py:\d+` efímeros en CONTEXT.md | **Copia-verbatim**: regex `check_context.py:8-9`, `check():14`; solo cambia path si el glosario no se llama CONTEXT.md |
| 5 | `harness/README.md` (140 lín.) | sí | Contrato P-E-V, tiers, sensores, traza e inspección | **Verbatim-estructura / seam-dominio**: origen `README.md:3`, sensores `README.md:10`, tabla `README.md:108-112` con dominios propios |
| 6 | `harness/plan.*.json` (5 files) | sí | Planes como contrato (intent/files/invariants/validation/rollback) | **Verbatim-esquema / seam-valores**: esquema copiable; `plan.example.json:2-8` con `localhost:8000`, `sim_state.json`, `CmdVel/FakeAdapter` propios |
| 7 | `tests/test_golden_path_puro.py` (90 lín.) | sí | Seam único CI+Harness: configs existen + purga + verify low/medium | **Seam**: asserts rutas propias `test_golden_path_puro.py:14-26,46-52,68-90`; copiar forma, reescribir asserts |
| 8 | `.github/workflows/ci.yml` (75 lín.) | sí | Quality + changes + webcam-ci con paridad `uv sync --all-packages` | **Verbatim-estructura / seam-targets**: `ci.yml:21` sync copiable; `ci.yml:27` `mypy fase-0` vs `ci.yml:73` `mypy plataforma/webcam` y `ci.yml:31,33` seam propio |
| 9 | `pyproject.toml` (56 lín.) | sí | Raíz instalable + ruff/pytest/mypy + workspace uv | **Seam**: `pyproject.toml:6` `name="embodied-ai"`, `:15-17` `include=["plataforma*"]`, `:32-41` mypy strict/overrides, `:55-56` members `webcam/backend,sim` |
| 10 | `conftest.py` (3 lín.) | sí | Ancla pytest rootdir + sys.path para `from plataforma...` | **Copia-verbatim** (`conftest.py:1-3`); ver `docs/adr/0002-pytest-rootdir-conftest-pythonpath.md` |
| 11 | `AGENTS.md` (21 lín.) | sí | Aprobación previa por paso + reglas CI local↔GitHub | **Verbatim-regla / seam-valores**: `AGENTS.md:5-8` copiable tal cual; `AGENTS.md:12-14` con `plataforma`, `mypy plataforma/webcam`, lecciones propias |
| 12 | `CONTEXT.md` (172 lín.) | sí | Glosario puro sin specs ni anclas efímeras | **No-verbatim (ejemplo)**: estructura copiable; contenido dominio propio (`CONTEXT.md:157-172` harness/golden path) |
| 13 | `.gitnexusrc` (3 lín.) | sí | Pin PDG para evitar rebuild | **Copia-verbatim** (`.gitnexusrc:2` `{"pdg": true}`) |
| 14 | `.gitignore` (34 lín.) | sí | Higiene: biometría, traza harness, node/dist, `.opencode/` | **Seam**: `:22` `identities.json`, `:30-33` `harness/trajectory|sensor_logs|output`, `:34` `.opencode/` (crítico, ver §3) |
| 15 | `docs/adr/0007-fusion-three-methodologies.md` (25 lín.) | sí | Decisión fusión 3 metodologías + DoD + purga | **No-verbatim (ejemplo)**: `0007:3` cita `harness/harness.py:32`+`AGENTS.md:10`; `0007:9` DoD propio |
| 16 | `docs/adr/0008-golden-path-comando.md` (20 lín.) | sí | Decisión comando `/golden-path` anti-solape + HITL | **No-verbatim (ejemplo)**: `0008:7` crea `.opencode/commands/golden-path.md` |
| 17 | `docs/adr/0009-golden-path-auto.md` (49 lín.) | sí | Decisión `/golden-auto` doble zona + punto de retorno | **No-verbatim (ejemplo)**: `0009:5-6,19-27` + `0009:42-44` retorno `a39e85d` propio |
| 18 | `docs/agents/domain.md` (51 lín.) | sí | Cómo las skills consumen CONTEXT.md + docs/adr/ | **Copia-verbatim** (template Matt; `domain.md:7-9`, sin OWNER/REPO) |
| 19 | `docs/agents/triage-labels.md` (15 lín.) | sí | Mapeo 5 roles canónicos → labels del tracker | **Copia-verbatim** (`triage-labels.md:7-11` tabla 1:1; columna derecha se edita solo si el vocabulario difiere) |
| 20 | `docs/agents/issue-tracker.md` (27 lín.) | sí | GitHub Issues como tracker + ops wayfinding | **Seam-OWNER/REPO**: `issue-tracker.md:3` y `:26` `mauriciosoyastor/embodied-ai`; resto (`:8,:18-21` mapa/frontier/claim/`## Answer`) verbatim-forma |
| 21 | `docs/agents/lessons/0007-golden-path-no-autoejecuta-skills.md` (34 lín.) | sí | `pytest` no dispara skills; usar `/golden-path` | **No-verbatim (ejemplo)**: `0007:7-8,18-20` con rutas propias |

Resultado: 21/21 existen en filesystem. En git: 19/21 tracked; 2/21 ignorados (los 2 `.opencode/commands/*.md`).

## 2. Tabla verbatim-vs-seam (resumen portable)

| Copia-verbatim (sin cambios) | Seam-de-adaptación (cambiar al portar) |
|---|---|
| `conftest.py`, `.gitnexusrc`, `harness/check_context.py` | `OWNER/REPO`: `issue-tracker.md:3,26` `mauriciosoyastor/embodied-ai` → nuevo owner/repo; más `harness.py:34-44` allowlist dominios |
| `docs/agents/domain.md`, `docs/agents/triage-labels.md` (tabla 1:1) | `nombre paquete`: `pyproject.toml:6` `embodied-ai` + `:15-17` `plataforma*` + `:55-56` members → nuevo paquete |
| Esquema `plan.*.json` + estructura `ci.yml`/`README.md`/comandos | `target mypy`: `ci.yml:27` vs `:73`, `harness.py:272` `plataforma/webcam`, `pyproject.toml:32-41`, `AGENTS.md:14` → nuevo target |
| — | `hook domain_assertions()`: `harness.py:343-440` (`CmdVel±1.0/±1.5:360-370`, `FakeAdapter:379-393`, `identities 128-d:410-428`) → reescribir por dominio; `SANDBOX_WRITABLE:53-64` + `README.md:13,111,126` |

## 3. Seams con líneas exactas

- **OWNER/REPO**: `docs/agents/issue-tracker.md:3` (`mauriciosoyastor/embodied-ai`), `:26` (`gh api repos/mauriciosoyastor/embodied-ai/...`).
- **Paquete**: `pyproject.toml:6,15-17,55-56`.
- **Mypy**: `pyproject.toml:32-41`; `ci.yml:27,73`; `harness/harness.py:266-281`; `AGENTS.md:14`.
- **domain_assertions()**: `harness/harness.py:343-352` docstring + `:354-396` sim models + `:399-430` identities + `:443-508` `build_evidence()` que lo consume y fija `risk`.
- **Crítico portable**: `.gitignore:34` ignora `.opencode/` → `git check-ignore -v` confirma que `golden-path.md` y `golden-auto.md` están ignorados y `git ls-files .opencode/commands/` vacío. Al portar: o `git add -f` o recortar `.gitignore:34` a subpaths (p.ej. `.opencode/node_modules/`), si no el pack "portable" pierde los 2 comandos. `harness/trajectory.jsonl:30` y `harness/output/:32` también ignorados por diseño (traza volátil).

## 4. Citas NO verificadas

Ninguna. Todas las rutas/líneas arriba fueron leídas del filesystem en esta sesión. Única salvedad: `harness/plan.overlay-world-ux.json`, `plan.voz-grounded.json`, `plan.webcam-percepcion.json` listados por `git ls-files harness/plan.*.json` pero solo se leyó contenido de `plan.example.json` y `plan.sim-headless.json`; su interior no se cita aquí.
