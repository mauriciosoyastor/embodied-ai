# Ticket 008 — Research: StateGraph con pydantic-ai vs alternativas

> Label: `wayfinder:research` · Parent: `001-map-orchestrador-sim.md` · Estado: cerrado · Resolución: 2026-08-22

## Resolución

**Respondido por subagente research (branch `research/stategraph-pydantic`):**

- **Recomendación: `pydantic-graph` vía `pydantic-ai-slim` 2.32.1** — ver hallazgo completo en `docs/agents/research/008-stategraph-pydantic.md` (305 líneas, fuentes primarias ai.pydantic.dev/PyPI/repo). Bundle 53 KiB, MIT, `py.typed`, 4 deps leves (`anyio`, `logfire-api`, `pydantic`, `typing-inspection`), ya viene con `pydantic-ai-slim` (costo 0), `TestModel` dentro de `BaseNode.run()` verificado, `openai:opencode/muse-spark-1.2-contributor-free` nativo, `mypy strict 3.12` ok, `GraphBuilder`/`BaseNode[StateT,DepsT,RunEndT]`/`End`/`GraphRunContext`/`iter()` para 10Hz.
- Descartados: `LangGraph` 1.2.11 (MIT pero 249 KiB + `langchain-core` 9 transitivas → ~5 MB, issues mypy #4140/#1856/#8559, requiere `langchain-openai`), `transitions` 0.9.3 (113 KiB, `six`, sin `py.typed`/LLM), `python-statemachine` 3.2.1 (159 KiB, 0 deps, `py.typed` pero sync-first, sin `Agent`/`TestModel`).
- Repo compat: `fase-1/orchestrator.py:21` `Agent[HardwareContext,DecisionAgentica]` + `TestModel` + `MissionFSM` `fsm.py:43` histéresis N=5 se envuelve en `HandleGestoNode`, no se reemplaza. Workspace `uv` path-filter intacto.
- Plan para 009/010: `MissionState` dataclass + `SimDeps` + `TickNode→HandleGestoNode→DecisionNode(Agent TestModel/openai:opencode)→ActNode→End`, `ctx.state` Whiteboard + `Join(reducer=...)` para Reducer futuro, `graph.render()` mermaid.

> Estado previo: abierto · Frontera (AFK) · Desbloquea 009, 010

## Question

¿`pydantic-graph` / `pydantic-ai` StateGraph nativo vs `LangGraph` vs `transitions`/`pytransitions` para modelar el orquestador, con compatibilidad `openai:opencode/muse-spark-1.2-contributor-free` (vía `openai:opencode/...` en `fase-1/orchestrator.py:21`) y `TestModel` headless?

Investigar:
- `pydantic-ai` tiene `pydantic_graph` (Graph, State, Edge) — ¿versión estable, docs, ejemplo `Agent`→`Graph`? ¿`TestModel` funciona con `Graph.run()`?
- `LangGraph` (Pregel) — bundle size, licencia, ¿requiere `langchain` pesado incompatible con `uv` workspace `plataforma/sim`?
- `transitions` / `python-statemachine` — ligero pero sin integración LLM; ¿cómo inyectar `DecisionAgentica`?
- Compat `numpy<2`, `python 3.12`, `mypy strict` (`pyproject.toml:32`), y si `pydantic-graph` ya está en `pydantic-ai-slim` instalado
- Patrón `HardwareContext` + `Whiteboard` como `GraphState` — ¿estado tipado Pydantic?
- Latencia y testabilidad: ¿cuál permite `pytest` sin red y mock `SimObservation`?

Resolver con subagente research — branch `research/stategraph-pydantic` + puntero contexto en este ticket. Bloquea 009 y 010.

## Bloquea

- 009-grilling-stategraph-estados
- 010-grilling-whiteboard-schema
