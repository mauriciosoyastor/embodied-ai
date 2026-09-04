# Checklist copiable — Golden portable (pegar en el nuevo repo)

- [ ] `.gitnexusrc` = `{"pdg": true}`
- [ ] `.opencode/commands/golden-path.md` + `golden-auto.md` copiados
- [ ] `docs/adr/0007* 0008* 0009*` + `docs/agents/domain.md triage-labels.md issue-tracker.md` + `lessons/0007*`
- [ ] `harness/harness.py check_context.py README.md plan.example.json` (adapta `domain_assertions()`)
- [ ] `tests/test_golden_path_puro.py` en verde
- [ ] `pyproject.toml`: `packages.find`, `pytest pythonpath=["."]`, `mypy`, `dev=[ruff,mypy,pytest,pre-commit]`
- [ ] `ci.yml`: `uv sync --all-packages` → ruff → format → mypy → pytest → check_context → pre-commit
- [ ] `.gitignore`: `node_modules/ dist/ trajectory.jsonl .opencode/node_modules/ harness/output/ harness/sensor_logs/`
- [ ] `CONTEXT.md` sin `.py:<num>` (salvo `harness/harness.py:<num>`); corre `python harness/check_context.py`
- [ ] `node .gitnexus/run.cjs analyze --index-only --pdg` → `status:current`
- [ ] Global OpenCode (opcional): solo los 2 `.md` a `~/.config/opencode/commands/`
