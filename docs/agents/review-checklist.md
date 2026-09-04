# Checklist doble cierre (Capa 3, Golden Path paso 8+9)

Una sola pasada, un solo fix-cycle. Dos mitades en paralelo:

## Mitad ejecutable (máquina)

`review_gate()` en `harness/harness.py` — corre solo, sin red:

- `APPROVE` → risk low, 0 tests rotos, domain ok. Mergeable tras gate humano del plan.
- `APPROVE_WITH_NOTES` → risk medium (infra, cobertura parcial). Mergeable; notas en el PR.
- `NEEDS-HUMAN` → risk high, tests rotos, domain caído o `impact_ratio >10`. No mergear: 1 fix-cycle, en el re-run solo se reporta.

## Mitad agente (skills, una pasada en paralelo)

1. `gitnexus-review`: blast-radius fuera del diff, taint (`explain`), dependencias (`pdg_query`), tests faltantes, veredicto.
2. `code-review`: dos ejes `Standards` vs `Spec`, sin re-rankear entre ejes.

## Pre-merge (humano)

1. `has_open_gate(run_id)` debe ser `False` (`--approve <run_id>` si hubo gate high).
2. `detect_changes` sin `HIGH` ignorado (`impact_ratio` solo observado).
3. Humano hace merge, cierra el issue con `## Answer`, actualiza `Decisions-so-far`.

## Trazas (no mover)

`harness/trajectory.jsonl` y `trajectory.jsonl` son append-only single-writer y están gitignoradas (lección 0004). No se mueven a `done/`: el historial vive en el archivo, lo temporal no se commitea.
