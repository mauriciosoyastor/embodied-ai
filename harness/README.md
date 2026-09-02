# Harness — Plan-Execute-Verify (Embodied AI)

> **Origen:** `scraperargenpro/harness/` Ticket 06 (Ning et al. 2026 §3.4) · **Port:** Embodied AI `harness/`
> **Patrón:** loop **Plan → Execute en sandbox → Verify con sensores** con traza inspeccionable.

## Qué demuestra

- **Loop P-E-V** con contrato inspeccionable (`harness/plan.example.json` + `harness/trajectory.jsonl`)
- **3 tiers** `read-only / sandbox-edit (default) / full-access` + default restrictiva
- **Sensores B:** `pytest` + `ruff/mypy` si están + `domain assertions` Embodied AI (`CmdVel clamp ±1.0/±1.5`, `FakeAdapter frame_id`, `SimObservation`, `IdentitiesStore 128-d`) + `evidence bundle`
- **Traza A** append-only: `harness/trajectory.jsonl` + `harness/sensor_logs/<run_id>.log`
- **HITL B:** destructivas + red no listada (solo `localhost`/`huggingface.co`/`api.openai.com` autónomos) gatillan `human_gate`
- **Sandbox-edit** confinado a `harness/output/` · `harness/trajectory.jsonl` · `harness/sensor_logs/` · `plataforma/webcam/backend/models/identities.json` (read-only real, demo en harness)

## Requisitos

- Python 3.12 + `uv` (`uv sync --all-packages`)
- Sin Docker. Sensores corren headless (`FakeAdapter`/`TestModel`) sin MuJoCo/onnx.

## Cómo correr

```powershell
# default restrictiva — sandbox-edit, sin red no listada
python harness/harness.py --allow-network=false --intent "demo: validar sim headless"

# con plan explícito (sim headless)
python harness/harness.py --allow-network=false --plan harness/plan.example.json
python harness/harness.py --allow-network=false --plan harness/plan.sim-headless.json

# plan percepcion webcam (requiere huggingface si baja modelos — gate sin allow-network)
python harness/harness.py --plan harness/plan.webcam-percepcion.json
# si dispara gate: probar con allow-network
python harness/harness.py --tier=full-access --allow-network=true --plan harness/plan.webcam-percepcion.json

# simular red no listada -> dispara human_gate
# editar plan.example.json: "target_url": "https://evil.example.com/exfil"
python harness/harness.py --plan harness/plan.example.json
# luego aprobar:
python harness/harness.py --approve <run_id> --approver mauri
```

Con `uv`:

```powershell
uv run python harness/harness.py --allow-network=false --plan harness/plan.example.json
```

Cada run genera:
- `harness/trajectory.jsonl` (append) — una línea JSON por fase
- `harness/sensor_logs/<run_id>.log` — stdout de pytest/ruff/mypy
- `harness/output/sim_state.json` — estado demo `{frame_id, x, v_x, ...}` con TTL volátil

## Cómo inspeccionar (traza inspeccionable)

`harness/trajectory.jsonl` es grep/cat/jq puro:

```powershell
cat harness/trajectory.jsonl | jq .
cat harness/trajectory.jsonl | jq -s "sort_by(.ts) | .[] | {run_id, phase, verdict, risk: .evidence.risk}"

cat harness/trajectory.jsonl | jq "select(.run_id==\"a1b2c3d4\")"
grep a1b2c3d4 harness/trajectory.jsonl

cat harness/trajectory.jsonl | jq "select(.human_gate.needed==true)"
grep human_gate harness/trajectory.jsonl

cat harness/trajectory.jsonl | jq "select(.phase==\"verify\") | .evidence"
cat harness/sensor_logs/a1b2c3d4.log
cat harness/output/sim_state.json | jq .
```

Sin `jq` (Windows):

```powershell
Get-Content harness/trajectory.jsonl | Select-String "needs-human"
Get-Content harness/trajectory.jsonl | ConvertFrom-Json | Where-Object { $_.phase -eq "verify" } | Select-Object run_id, verdict, @{n="risk";e={$_.evidence.risk}}
Get-Content harness/sensor_logs/a1b2c3d4.log
```

## Esquema trajectory.jsonl

```json
{
  "run_id": "a1b2c3d4",
  "ts": "2026-09-02T10:15:35",
  "phase": "verify",
  "tier": "sandbox-edit",
  "intent": "demo: validar sim headless + traza",
  "files_touched": ["harness/output/sim_state.json"],
  "verdict": "ok | fail | needs-human",
  "evidence": {
    "tests_run": ["pytest"],
    "tests_passed": 1, "tests_failed": 0,
    "linter": {"tool": "ruff", "ok": true},
    "mypy": {"tool": "mypy", "ok": true},
    "domain_assertions": {"checked": 2, "ok": true, "failures": []},
    "uncovered": [],
    "risk": "low|medium|high",
    "risk_reason": "..."
  },
  "human_gate": {"needed": false, "reason": "", "approved_by": null},
  "sensor_log": "harness/sensor_logs/a1b2c3d4.log"
}
```

## Permisos — tabla rápida

| Tier | Puede escribir | Red autónoma | Gate HITL |
|------|---------------|--------------|-----------|
| `read-only` | nada | ninguna | cualquier write/exec/network |
| `sandbox-edit` (default) | `harness/output/`, `harness/trajectory.jsonl`, `harness/sensor_logs/` | `localhost`, `127.0.0.1`, `huggingface.co`, `api.openai.com`, `argenprop.com`, `wa.me` | destructivas + red no listada + write fuera de sandbox |
| `full-access` | todo | con `--allow-network=true` | solo destructivas + red no listada si `allow_network=false` |

Patrones destructivos: `rm -rf`, `push --force`, `.env`, `DROP`, `DELETE FROM`.

## Planes incluidos

- `plan.example.json` — demo sim_state + localhost (run ok sin gate)
- `plan.sim-headless.json` — `plataforma/sim/tests/test_harness.py` TTD FakeAdapter/TestModel
- `plan.webcam-percepcion.json` — `plataforma/webcam` Whitelist W30 (gate si baja modelos sin allow-network)

## Diferencias vs scraper

- `publisher_cache.json` → `harness/output/sim_state.json` (demo) + checks `CmdVel`/`FakeAdapter` reales
- `argenprop.com/wa.me` allowlist se mantiene + se agrega `localhost/huggingface/api.openai`
- `output/publisher_cache.json` real de Embodied AI (`identities.json`) es **read-only** por `.gitignore:22`; el harness escribe solo en `harness/output/` para no contaminar

## Estructura

```
harness/
  harness.py              # loop P-E-V + permisos + sensores + traza
  trajectory.jsonl        # traza append-only (se crea al primer run)
  sensor_logs/<run_id>.log
  output/sim_state.json   # estado demo volátil
  plan.example.json
  plan.sim-headless.json
  plan.webcam-percepcion.json
  README.md
```
