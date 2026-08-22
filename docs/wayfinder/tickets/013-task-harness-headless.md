# Ticket 013 — Task: Harnés headless TDD con TestModel

> Label: `wayfinder:task` · Parent: `001-map-orchestrador-sim.md` · Estado: cerrado · Resolución: 2026-08-22

## Resolución

**Hechos (AFK — sin decisión, solo deja baseline verde):**
- Creado `plataforma/sim/` como member uv workspace (`pyproject.toml:46` `members += "plataforma/sim"`), `uv.lock` actualizado con `sim==0.1.0`, `pydantic-ai==2.32.1`/`pydantic-graph==2.32.1` ya disponibles sin instalar `mujoco`/`opencv` pesado
- Modelos `plataforma/sim/models.py:6` `SimObservation`/`CmdVel`/`SimMetrics` (SI/world-frame, clamp `v_x±1.0` `omega±1.5`) + `plataforma/sim/adapter.py:7` `SimAdapter` Protocol + `plataforma/sim/fake_adapter.py:7` `FakeAdapter` (10Hz mock, cinemática diferencial `x+=v·cos(yaw)·dt`, `yaw+=omega·dt`, `steps/s≈10`)
- Tests `plataforma/sim/tests/test_harness.py:7` 3 tests verdes: `test_fake_adapter_obs_advances_on_step` (frame_id 0→1, x avanza), `test_cmd_vel_clamp_via_pydantic` (ValidationError), `test_orquestador_headless_con_testmodel` (monkeypatch dummy `OPENCODE_API_KEY`, `TestModel(custom_output=DecisionAgentica)` → `CmdVel→FakeAdapter.step`)
- Verificación: `uv run ruff check plataforma/sim` ✅, `uv run mypy plataforma/sim` ✅ (6 files, `type: ignore[import-not-found]` para `fase-1/orchestrator`), `uv run pytest plataforma/sim -q` **3 passed in 4.78s** (1 DeprecationWarning `pydantic_graph._utils:67` no bloqueante), `OPENCODE_API_KEY` placeholder sigue sin bloquear (tests usan `TestModel`)
- Desbloquea 011 — `FakeAdapter` throwaway ya tiene stub real que puede evolucionar a prototype

> Estado previo: abierto · Frontera (AFK)

## Question

Trabajo manual previo no-decisivo que desbloquea la frontera: establecer baseline verde `pytest` headless antes de introducir lógica de orquestación.

Hacer (AFK donde sea posible, HITL checklist donde requiera humano):
- Crear paquete `plataforma/sim/` como member `uv` workspace (añadir a `pyproject.toml:46` `tool.uv.workspace.members`), con `pyproject.toml` propio, `__init__.py`, `conftest.py` si necesita `pythonpath=["."]`
- `uv sync --all-packages` verde sin instalar `mujoco`/`opencv` pesado — solo `pydantic`, `pydantic-ai`, `pytest`, `ruff`, `mypy` (path-filtered `plataforma/webcam` no dispara)
- Fixture `HardwareContext(sensor_activo=True, bateria_nivel=80)` + `TestModel(custom_output_args=DecisionAgentica(accion="avanzar",...))` como en `fase-1/test_orchestrator.py:14` — `agent.run_sync` pasa sin red
- Stub `FakeAdapter` mínimo (o import si 011 ya creó prototype) que expone `SimObservation` dummy para que `pytest plataforma/sim -q` tenga al menos 1 test verde
- Verificar `uv run ruff check plataforma/sim && uv run mypy plataforma/sim && uv run pytest plataforma/sim -q` en local y CI `plataforma/webcam/**` no roto
- Registrar hechos en resolución: path creado, `uv.lock` actualizado, tiempo `pytest`, que `OPENCODE_API_KEY` placeholder aún no bloquea tests con `TestModel`

No hay decisión que tomar — solo deja el harness listo. Desbloquea 011. Resolver cuando `pytest` está verde y se puede cerrar sin red.
