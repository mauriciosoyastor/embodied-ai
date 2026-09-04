# Golden portable — guía para replicar Golden Path Fusión en otro proyecto u OpenCode global

Origen verificado en este repo (2026-09-04). No especula: cada archivo citado existe aquí.

## 1. Qué es (30s)

Pipeline único obligatorio (ADR-0007 `docs/adr/0007-fusion-three-methodologies.md`):

`Issue → triage → wayfinder? → to-tickets (1 vez) → gitnexus-plan (por ticket) → gitnexus-work (+harness verify) → gitnexus-review + code-review (1 fix-cycle) → merge humano`

- `/golden-path` (`.opencode/commands/golden-path.md`): paso a paso con gates HITL (respeta `AGENTS.md` aprobación previa). Sin flags no cambia.
- `/golden-auto` (`.opencode/commands/golden-auto.md`, ADR-0009 `docs/adr/0009-golden-path-auto.md`): misma secuencia pero invocar equivale a "aprueba por adelantado pasos locales y defaults; push/PR/close/merge siempre con OK". Regla de oro: lo que `git` puede deshacer lo decide la máquina; lo que deja huella afuera lo decide el humano.
- `pytest` jamás ejecuta skills (lesson 0007 `docs/agents/lessons/0007-golden-path-no-autoejecuta-skills.md`): `tests/test_golden_path_puro.py` es solo seam `CI+Harness`. Las skills viven a nivel agente (tool `skill`).

Tres metodologías fusionadas:
1. Matt Pocock: `triage / wayfinder / to-tickets / tdd / code-review` (42 skills instaladas, mapa en `docs/agents/domain.md`).
2. GitNexus: `query → context → impact → trace → pdg_query + explain`, `detect_changes`, `.gitnexusrc` con `{"pdg": true}`.
3. Repo: `AGENTS.md` aprobación + `harness P-E-V` (`harness/harness.py`) + paridad CI (`uv sync --all-packages`).

## 2. Inventario real (qué copiar)

| Pieza | Ruta aquí | Rol |
|---|---|---|
| Comando paso a paso | `.opencode/commands/golden-path.md` | template orden canónico + anti-solape + DoD |
| Comando auto | `.opencode/commands/golden-auto.md` | ráfaga local + panel Hecho / Pendiente tu OK |
| Decisión fusión | `docs/adr/0007-fusion-three-methodologies.md` | por qué este orden, DoD, reversibilidad |
| Decisión comando | `docs/adr/0008-golden-path-comando.md` | anti-solape, por qué no auto-orquestador Python |
| Decisión auto | `docs/adr/0009-golden-path-auto.md` | doble zona, 3 reintentos, nunca auto remoto |
| Lesson anti-confusión | `docs/agents/lessons/0007-golden-path-no-autoejecuta-skills.md` | pytest ≠ skills |
| Glosario agente | `docs/agents/domain.md`, `triage-labels.md`, `issue-tracker.md` | lo que `triage/wayfinder` leen antes de explorar |
| Harness P-E-V | `harness/harness.py`, `harness/README.md`, `harness/check_context.py`, `harness/plan.*.json` | loop Plan→Execute→Verify, tiers, sensores, traza |
| Seam CI+Harness | `tests/test_golden_path_puro.py` | 5 asserts: configs + purga + workflows + trajectory + verify low/medium |
| Paridad CI | `.github/workflows/ci.yml`, `pyproject.toml`, `conftest.py`, `AGENTS.md` regla CI | `uv sync --all-packages`, `pythonpath=["."]`, mypy/ruff/pytest |
| Índice grafo | `.gitnexusrc` | `{"pdg": true}` evita rebuild 18.5s |
| Glosario dominio | `CONTEXT.md` + linter `\.py:\d+` | glosario puro, sin anclas efímeras (anti-pattern `ws.py:197`) |
| Ignorados | `.gitignore` | nunca `node_modules/ dist/ trajectory.jsonl .opencode/node_modules/` |

## 3. Opción A — futuro proyecto (recomendado, ~15 min)

Mínimo viable (= lo que `test_golden_path_puro.py` exige):

```powershell
# 1. Estructura
New-Item -ItemType Directory -Path docs/adr, docs/agents/lessons, docs/guides, .opencode/commands, harness, tests -Force
'{"pdg": true}' | Set-Content .gitnexusrc -Encoding utf8

# 2. Copiar desde este repo (ajusta OWNER/REPO en issue-tracker.md)
Copy-Item .opencode/commands/golden-path.md, .opencode/commands/golden-auto.md .opencode/commands/  # origen: este repo
Copy-Item docs/adr/0007-fusion-three-methodologies.md, docs/adr/0008-golden-path-comando.md, docs/adr/0009-golden-path-auto.md docs/adr/
Copy-Item docs/agents/domain.md, docs/agents/triage-labels.md, docs/agents/issue-tracker.md docs/agents/
Copy-Item docs/agents/lessons/0007-golden-path-no-autoejecuta-skills.md docs/agents/lessons/
Copy-Item harness/harness.py, harness/check_context.py, harness/README.md harness/
Copy-Item harness/plan.example.json harness/  # + los plan.* que uses
Copy-Item tests/test_golden_path_puro.py tests/
Copy-Item AGENTS.md, CONTEXT.md, conftest.py, .gitnexusrc .
# Fusiona a mano: pyproject.toml ([tool.setuptools.packages.find], pytest pythonpath, mypy, ruff), .github/workflows/ci.yml, .gitignore
```

`pyproject.toml` mínimo (ver el real aquí, `pyproject.toml:15-56`):

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["plataforma*"]  # ajusta a tu paquete o elimina si no hay paquete
[tool.pytest.ini_options]
pythonpath = ["."]
[tool.mypy]
strict = true
explicit_package_bases = true
disallow_untyped_decorators = false
warn_unused_ignores = false
[[tool.mypy.overrides]]
module = ["numpy.*","cv2.*","fastapi.*","onnxruntime.*","mediapipe.*","PIL.*"]
ignore_missing_imports = true
[dependency-groups]
dev = ["ruff","mypy","pytest","pre-commit>=4.6.2"]
```

`ci.yml` mínimo (ver real `.github/workflows/ci.yml:9-33`): `uv sync --all-packages` → `ruff check` → `ruff format --check` → `mypy <tu-paquete>` → `pytest` → `python harness/check_context.py` → `pre-commit run --all-files`.

Adapta el harness a tu dominio: cambia `domain_assertions()` en `harness/harness.py:343` (aquí valida `CmdVel/FakeAdapter/SimObservation`); conserva `EvidenceBundle`, `check_permission` (tiers), `run_detect_changes`, `append_trajectory`. Si tu proyecto no usa GitNexus, el sensor hace fallback a `low` (no bloquea).

Verifica:

```powershell
uv sync --all-packages
uv run ruff check .; uv run ruff format --check .
uv run mypy <tu-paquete>
uv run pytest tests/test_golden_path_puro.py -q  # 5/5 verde = seam OK
uv run python harness/check_context.py
node .gitnexus/run.cjs analyze --index-only --pdg  # luego status debe dar pdg:true status:current
```

## 4. Opción B — OpenCode global (todos tus proyectos)

Lo global es solo el *prompt* de los comandos; el harness/CI/ADRs quedan por repo.

```powershell
# Windows (ajusta si tu config vive en ~/.config/opencode)
$dst = "$env:USERPROFILE\.config\opencode\commands"
New-Item -ItemType Directory -Path $dst -Force
Copy-Item .opencode/commands/golden-path.md, .opencode/commands/golden-auto.md $dst/
# Skills Matt + GitNexus ya son globales si las instalaste; si no: instala wayfinder/triage/to-tickets/tdd/code-review + gitnexus
# Por repo solo deja: docs/agents/*.md + .gitnexusrc + harness/ + tests/test_golden_path_puro.py
```

Diferencia clave: en global NO copies `harness.py` ni `ci.yml` (son por repo). En global solo van los dos `.md` de comandos.

## 5. DoD y prohibiciones (no negociar)

DoD (de `.opencode/commands/golden-path.md:31-36`): `CI fail rate <10%`, `uv sync --all-packages` local = `ci.yml`, `harness verify verdict:ok risk:low` sin `UNKNOWN` sin confirmar, `detect_changes` sin `HIGH` ignorado, `pdg:true status:current`. `impact_ratio` solo observado.

Prohibido: saltar `impact before edit` / `detect_changes before commit`; doble slice (`to-tickets` trocea una vez, `gitnexus-plan §7` no re-trocea); `gitnexus-lfg` completo + lanes sueltas a la vez; commitear sin gate humano en pasos destructivos; `push/pr/close/merge` sin OK explícito (aunque uses `/golden-auto`).

Anti-solape: `wayfinder` solo con niebla (>1 sesión / destino difuso); tarea chica (1-2 archivos, <~35 turns) → `gitnexus-work` directo; camino claro → salta a `to-tickets`.

## 6. Punto de retorno

Reversión (ADR-0009): borrar los dos `.md` de comandos + `docs/adr/0008* 0009*` + fila de lesson revierte el comando; ADR y lesson quedan como registro. El harness es append-only (`trajectory.jsonl` está en `.gitignore`, no se commitea).
