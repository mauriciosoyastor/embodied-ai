# 008 — StateGraph con pydantic-ai vs alternativas (LangGraph / transitions / python-statemachine)

Fecha: 2026-08-21. Investigación contra fuentes primarias (ai.pydantic.dev, PyPI, repo pydantic-ai, LANG-Graph PyPI, repo python-statemachine, verificación local con `uv run --with pydantic-ai`).

> Parent: ticket map Orquestador Cognitivo + Simulación (001-map-orchestrador-sim.md).
> Bloquea: tickets 009 (StateGraph prototipo) y 010 (Whiteboard + DecisionAgéntica).
> Branch de research prevista: `research/stategraph-pydantic`.

## Pregunta

¿`pydantic-graph` (hoy `pydantic_graph` paquete `pydantic-graph`) es la elección correcta para el `StateGraph` headless del Orquestador (prototipo StateGraph + Whiteboard + DecisionAgentica → FakeAdapter con Muse Spark `opencode/muse-spark-1.2-contributor-free` a 10 Hz), frente a LangGraph (Pregel), `transitions` y `python-statemachine`? Evaluar: API Graph/State/Edge, compat con `TestModel`, versión estable, bundle size, licencia MIT, mypy strict python 3.12, peso de dependencias, integración con modelo `openai:opencode`, y trade-offs específicos del repo (uv workspace, path filtering, CI sin mujoco, loop 10 Hz).

## Respuesta corta

**Recomendación: `pydantic-graph` (vía `pydantic-ai-slim`).** Es la única opción que es cero-costo incremental para este repo, mypy-strict nativa, bundle mínimo (~53 KiB), 4 deps livianas, integración directa `Agent(TestModel | openai:opencode/muse-spark-1.2)` dentro de `BaseNode.run()`, y `State`/`GraphRunContext` + `Deps` ya alineados con el Whiteboard/FakeAdapter previsto. LangGraph es potente pero pesado y arrastra `langchain-core` + 3 subpaquetes (5 paquetes efectivos, 9 deps transitivas de `langchain-core`) y problemas mypy abiertos; `transitions`/`python-statemachine` son FSMs síncronas clásicas sin integración LLM/state async — útiles para validar la FSM actual, no para el graph orquestador.

---

## 1. Compat actual del repo (verificado local)

| Fichero | Hallazgo |
|---|---|
| `pyproject.toml:11` (`[project.optional-dependencies] fase1`) | `pydantic-ai>=0.0.10` (rango laxo, permite 2.x). No pin a `pydantic-ai-slim` ni a `pydantic-graph` explícito. |
| `fase-1/orchestrator.py:1-11` | Usa `pydantic_ai.Agent[HardwareContext, DecisionAgentica]` con `model="openai:opencode/muse-spark-1.2-contributor-free"` (override `model` string OpenAI-compat). `Agent` ya delega a graph interno en 2.x. |
| `fase-1/gemini_client.py` | Defaults `MODELO_DEFECTO=opencode/muse-spark-1.2-contributor-free`, normaliza alias `muse-spark-1.2-free`, lee `OPENCODE_API_KEY/CURSOR_API_KEY/OPENAI_API_KEY`. Compatible con `openai:` prefix de pydantic-ai. |
| `fase-1/test_orchestrator.py:29` | `agent.override(model=TestModel(custom_output_args=...))` + `agent.run_sync(...)` — patrón canónico que debe preservarse en el graph. |
| `plataforma/webcam/backend/pyproject.toml:1-14` | `dependencies = [fastapi, uvicorn, onnxruntime==1.29.*, opencv-python==4.14.*, mediapipe==1.0.1, numpy, pydantic>=2]` — **no depende de pydantic-ai** (path filtering intacto). Workspace `uv` (`pyproject.toml:45-46`, `uv.lock:12`) members `["embodied-ai", "webcam-backend"]` desacoplado: añadir `pydantic-ai-slim` solo al miembro orquestador/sim no toca `webcam-backend`. |
| `plataforma/webcam/backend/fsm.py:43-138` | `MissionFSM` con histéresis N=5 (`CONF_THRESHOLD=0.7`) y latch `ABORTED`. API pura, headless, testeable sin cámara. Es el contrato que el `StateGraph` debe envolver (ver §5). |
| `CONTEXT.md:15,55-58` | Define `StateGraph`, `Whiteboard`, `Reducer`, `GestoReconocido`, `handle_gesto`, `ABORTED latch`, y `Muse Spark 1.2 free opencode/muse-spark-1.2-contributor-free vía OpenAI-compatible`. |
| `uv.lock` + `uv pip list` local | Root no tiene `pydantic-ai` instalado sin `--with`; con `--with pydantic-ai` se instala `pydantic-ai==2.32.1`, `pydantic-ai-slim==2.32.1`, `pydantic-graph==2.32.1`, `pydantic==2.13.4`. `webcam-backend` queda limpio. |

**Conclusión compat:** el repo ya está cableado para `pydantic-ai 2.x` + `openai:opencode` + `TestModel`. No hay conflicto de versiones; solo falta explicitar la dep.

## 2. pydantic-graph — API verificada

### 2.1 Instalación y versionado

- **Versión estable local verificada:** `pydantic-ai==2.32.1`, `pydantic-graph==2.32.1`, `pydantic==2.13.4` (python 3.12). Publicación actual PyPI `pydantic-graph==2.33.0` (misma línea 2.x).
- **Paquete:** `pydantic-graph` (import `pydantic_graph`). `pydantic-ai-slim==2.32.1` declara `pydantic-graph==2.32.1` como dep requerida (no opcional) — **ya viene con `pydantic-ai-slim`**; `pydantic-ai` meta-paquete lo re-exporta. No hay que añadir `pydantic-graph` suelto si se depende de `pydantic-ai-slim`.
- **Licencia:** MIT (`License-Expression: MIT` en METADATA). Clasificador `Development Status :: 5 - Production/Stable`, soporta `3.10–3.14`. Fuentes: `METADATA` local y `https://pypi.org/project/pydantic-graph/`.
- **Docs oficiales:** `https://ai.pydantic.dev/graph/` — nota "Don't use a nail gun unless you need a nail gun": el graph es para casos avanzados, no default para un agent simple. Caso de este ticket **sí** califica (StateGraph + Whiteboard + DecisionAgéntica + simulación).

### 2.2 API Graph / State / Edge (fuente: `pydantic_graph/__init__.py` y `basenode.py` locales)

```python
from pydantic_graph import BaseNode, End, GraphRunContext, GraphBuilder, Edge
from dataclasses import dataclass


@dataclass
class MyState:  # ← "State" del ticket = StateT genérico (dataclass o BaseModel)
    count: int = 0


class MyNode(BaseNode[MyState, None, int]):  # BaseNode[StateT, DepsT, RunEndT]
    foo: int

    async def run(self, ctx: GraphRunContext[MyState, None]) -> AnotherNode | End[int]:
        # ctx.state (mutable, compartido) = Whiteboard
        # ctx.deps  (inyectado)           = FakeAdapter / SimDeps
        # return type Union               = Edge (inferido en runtime, validado + mermaid)
        ...
```

- **`GraphRunContext[StateT, DepsT]`** (`basenode.py:20`): `state: StateT`, `deps: DepsT`. Es el Whiteboard (state mutable pasado por referencia entre nodos) + inyección de deps (adapter, config) como en `pydantic_ai.RunContext`.
- **`BaseNode[StateT, DepsT, NodeRunEndT]`** (`basenode.py:29`): abstract `async def run(self, ctx) -> BaseNode | End[RunEndT]`. Los **Edges se infieren de la anotación de retorno** (`AnotherNode | End[int]`) en runtime y se usan para validación + `graph.render()` (mermaid `stateDiagram-v2`). No hay registro manual de edges separado (aunque `GraphBuilder` también permite `g.edge_from(...).to(...)` para el `start_node`).
- **`End[RunEndT]`** (`basenode.py:54`): `dataclass End(data: RunEndT)` — señala fin del graph.
- **`Edge(label=...)`** (`basenode.py:61`): anotación opcional para labels en mermaid.
- **`GraphBuilder[StateT, DepsT, InputT, OutputT]`** (`graph_builder.py`): `GraphBuilder(state_type=..., deps_type=..., input_type=..., output_type=...)`, `g.node(Cls)`, `g.edge_from(g.start_node).to(step)`, `g.build() -> Graph`. `Graph.run(state=..., deps=..., inputs=...) -> OutputT` (async) y `run_sync` + `iter()` para step-by-step (inspección/traces/time-travel parcial). Nota: `iter()` permite `10 Hz loop` que itera tick a tick y observa `state` sin re-ejecutar todo el graph.
- **Topologías avanzadas:** `Decision`, `Fork`, `Join`/`JoinNode` con reducers (`reduce_dict_update`, `reduce_sum`, `reduce_list_append`, etc.) — el `Reducer` de `CONTEXT.md` mapea a `Join(reducer=...)`.
- **Mermaid:** `print(graph)` / `graph.render(direction="LR")` — útil para docs/agents.

### 2.3 Integración con `Agent` + `TestModel` + `openai:opencode`

- `Agent` interno **ya usa `pydantic_graph`**: `Agent` construye un graph interno (system prompts → model request → tools → output). No hay conflicto; anidar `Agent` dentro de `BaseNode.run()` es el patrón documentado (ej. `genai_email_feedback.py` en `ai.pydantic.dev/graph/` con `email_writer_agent` + `feedback_agent` dentro de nodos).
- **Verificación local (ejecutada):**

  ```python
  from pydantic_ai import Agent
  from pydantic_ai.models.test import TestModel
  from pydantic_graph import BaseNode, End, GraphRunContext


  class Decide(BaseNode[MyState, None, str]):
      async def run(self, ctx):
          agent = Agent(TestModel(), output_type=Out)
          result = await agent.run("decide")  # async, awaitable dentro de node
          ctx.state.last_answer = result.output.answer
          return Finish()


  # Resultado local: TestModel dentro de nodo funciona (state mutado, output propagado)
  ```

  Conclusión: `TestModel` **no** es un modelo del `Graph` en sí — el `Graph` no tiene "model". `TestModel` se usa vía `Agent(TestModel(...))` embebido en un nodo agéntico; `Graph.run()` no toma `model=`. Patrón compatible con `FakeAdapter` tests (inyectar `TestModel` como `deps` o capturar en closure; `agent.override(model=TestModel(...))` también funciona si el `Agent` es global).
- **Integración `openai:opencode/muse-spark-1.2-contributor-free`:** el `Agent` ya soporta `model="openai:opencode/muse-spark-1.2-contributor-free"` (prefix `openai:` genérico, base URL configurable vía `OPENAI_BASE_URL`). En el graph, el nodo agéntico hace `Agent("openai:opencode/muse-spark-1.2-contributor-free", output_type=DecisionAgentica)` igual que `fase-1/orchestrator.py:39`. Sin cambios.

### 2.4 Compat `TestModel` + `Graph.run()` — respuesta directa

| Pregunta | Respuesta |
|---|---|
| ¿`pydantic-graph` ya viene con `pydantic-ai-slim`? | **Sí.** `pydantic-ai-slim 2.32.1 → pydantic-graph==2.32.1` (dependencia requerida). Ver `METADATA` local y `uv pip list`. `pip install pydantic-ai-slim` trae el graph sin paso extra. `pydantic-ai` meta lo re-exporta con el alias conveniencia. |
| ¿`TestModel` funciona con `Graph.run()`? | **Sí, indirectamente.** `Graph` no consume `TestModel` directo; el nodo agéntico hace `await Agent(TestModel(...), output_type=DecisionAgentica).run(...)`. Verificado localmente (async node + TestModel → `state.last_answer='a'`). Alternativa sync en tests: `agent.override(model=TestModel(...))` + `Agent.run_sync` dentro de un nodo que hace `await loop.run_in_executor(...)` si se necesita. |
| ¿Version stable? | **Sí, 2.x Production/Stable.** `pydantic-ai 2.32.1` / `pydantic-graph 2.32.1` (PyPI latest `2.33.0`), MIT, py `>=3.10` (incl. `3.12`). Releases semanales, API estable desde `V1 Sep 2025` (ver §4). |

## 3. Alternativas — análisis

### 3.1 LangGraph (Pregel)

- **Qué es:** graph runtime stateful con `StateGraph` builder, functional API (`@task/@entrypoint`), execution engine Pregel, cycles/subgraphs, conditional edges, checkpointers (memory/Postgres/Redis), `langgraph-sdk`, `langgraph-prebuilt`. Inspiración Pregel + Apache Beam + NetworkX.
- **Versión/PyPI (2026-08-21):** `langgraph==1.2.11` (local verif `1.2.x` estable), `langgraph-checkpoint>=4.1.0`, `langgraph-sdk>=0.4.2`, `langgraph-prebuilt>=1.1.0`, `xxhash>=3.5.0`, `pydantic>=2.7.4`, `requires-python>=3.10`. Licencia MIT, clasificador `Stable`.
- **Deps reales / bundle size:**

  ```
  langgraph 1.2.11
    → langchain-core<2,>=1.4.7  (9 deps transitivas: jsonpatch, langchain-protocol, langsmith, packaging, pydantic, pyyaml, tenacity, typing-extensions, uuid-utils)
    → langgraph-checkpoint>=4.1.0 (→ langchain-core, ormsgpack)
    → langgraph-prebuilt>=1.1.0   (→ langchain-core, langgraph-checkpoint)
    → langgraph-sdk>=0.4.2        (→ httpx, langchain-core, langchain-protocol, orjson, websockets)
    → pydantic>=2.7.4, xxhash>=3.5.0
  ```
  Efectivo: **5 paquetes** mínimos, wheel `langgraph` ~249 KiB (725 KiB sdist), pero tree completo con `langchain-core 1.5.0` + `langsmith` + `orjson` etc. supera **>5 MB** instalado. Fuente: `https://benchclaw.io/langchain-vs-langgraph/` audit (102 py files, 41 importan `langchain_core`), y `pypi.org/pypi/langgraph/json` + `langchain-core` deps.
- **API:**

  ```python
  from langgraph.graph import StateGraph, END
  from typing import TypedDict, Annotated


  class State(TypedDict):
      count: int


  g = StateGraph(State)
  g.add_node("decide", decide_fn)  # decide_fn(state)->dict patch
  g.add_edge("decide", "act")
  g.add_conditional_edges("act", router)
  app = g.compile(checkpointer=MemorySaver())
  app.invoke({"count": 0})
  ```
  State es `TypedDict` (o `Annotated` con reducers). Nodes retornan **patch dict** (no instancia tipada). Necesita `typing_extensions.TypedDict` si se usa con `pydantic` en `<3.12`/`3.12` con compat mixta (issue #1856).
- **Pros:** topología arbitraria, subgraphs, checkpointing durable + time-travel, interrupts/human-in-loop nativos, LangSmith tracing, ecosistema LangChain, functional API.
- **Contras específicos para este repo:**
  - **Peso CI:** 5 paquetes + `langchain-core` con `langsmith`/`orjson`/`xxhash` etc. — overkill para CI sin mujoco (que busca jobs rápidos con path filtering). Añadirlo al root rompe path filtering si `webcam-backend` queda en mismo tree (aunque workspace lo mitiga, el lock global crece).
  - **Mypy strict 3.12:** problemas abiertos (`Functional API breaks mypy with Never` #4140; `TypedDict typeddict-item` warnings en nodes que retornan patch parcial; `typing.TypedDict` vs `typing_extensions.TypedDict` en 3.12). `StateGraph` impone `TypedDict`+reducers con tipos `Annotated` que no son `BaseModel`/`dataclass` nativos; `py.typed` sí existe pero LangGraph's generics no son tan expresivos como `pydantic_graph` `BaseNode[StateT, DepsT, RunEndT]`.
  - **Integración LLM:** LangGraph no trae `TestModel`; el test harness es `langgraph` con `FakeChatModel` de `langchain-core` — diverge del harness `pydantic_ai` ya usado en `fase-1/test_orchestrator.py`. `openai:opencode/muse-spark-1.2` requeriría `ChatOpenAI` de `langchain-openai` (extra dep) vs. `Agent("openai:opencode/...")` nativo en pydantic-ai.
  - **10 Hz loop:** Pregel está diseñado para workflows batch/checkpointed; el overhead de `PregelNode.__init__` hace `inspect.getsource` + `ast.parse` por nodo en `compile()` (issue #8559) — costo proporcional al tamaño del fichero fuente, no al graph. No crítico pero contrario al constraint `10 Hz`.
  - **Lock-in langchain-core:** 40% de ficheros importan `langchain_core` (`RunnableConfig`, `BaseMessage`, `BaseTool`); aunque no requiera `langchain` umbrella, sí impone `langchain-core` como piso.

### 3.2 `transitions` (pytransitions)

- **PyPI:** `transitions==0.9.3`, `Author Tal Yarkoni`, license MIT, `requires_dist=['six']` (+ opcionales `pygraphviz`, `pytest`). Wheel ~113 KiB, sdist ~1.19 MB. Python `>=3.6` (no typed moderno).
- **Deps/bundle:** **1 dep (`six`)** — el más liviano del lote. Core ~single-file-ish.
- **API (imperativa):**

  ```python
  from transitions import Machine

  m = Machine(
      model=obj,
      states=["IDLE", "RUNNING", "PAUSED", "ABORTED"],
      transitions=[
          {
              "trigger": "handle_gesto",
              "source": "IDLE",
              "dest": "RUNNING",
              "conditions": "is_thumbs_up",
          }
      ],
      initial="IDLE",
  )
  obj.handle_gesto()  # genera método en modelo
  ```
  Callbacks por string o callable, condiciones por `conditions=`/`unless=`.
- **Pros:** peso mínimo, 12 `Machine` variants combinables, probado, diagrams vía `pygraphviz`, sin typing overhead.
- **Contras para este repo:**
  - **No valida estructura** al definir (estados inalcanzables, trap states sin out-edge no se detectan hasta runtime). `python-statemachine` sí valida; `pydantic-graph` lo hace vía tipos.
  - **Sin DI ni async nativo:** `Machine(model=obj)` muta el modelo inyectando triggers; no hay `ctx.state`/`ctx.deps` ni `async def run`. Integrar `Agent`/`TestModel` requiere boilerplate y pierde `Grammar-Constrained Decoding`.
  - **Sin tipado estricto:** no `py.typed`, `mypy strict` no aporta; callbacks por `str` nombres son `F821`-prone (mismo problema que lessons `0001-ruff-f821-imports-en-tests.md`).
  - **Sin reducer/whiteboard:** no hay `State` compartido tipado ni `Join` reducers; hay que inventar Whiteboard externo.

### 3.3 `python-statemachine`

- **PyPI:** `python-statemachine==3.2.1`, `Author Fernando Macedo`, license MIT License, `python>=3.10`, `requires_dist` **vacío en core** (solo extras `diagrams: pydot>=4.0.1`, `io: jsonschema+pyyaml`). Wheel ~159 KiB. Repo declara `ruff`, `mypy`, `pyright` en dev.
- **API (declarativa, validada):**

  ```python
  from statemachine import StateChart, State


  class MissionSM(StateChart):
      idle = State(initial=True)
      running = State()
      paused = State()
      aborted = State(final=True)
      handle_gesto = (
          idle.to(running, cond="is_thumbs_up")
          | idle.to(paused, cond="is_open_palm")
          | running.to(aborted, cond="is_fist")
      )

      def is_thumbs_up(self, event_data): ...


  sm = MissionSM()
  sm.send("handle_gesto")
  ```
  Callbacks con **DI por inspección de firma** (`SignatureAdapter`), guards `cond=`/`unless=`, eventless transitions, scoring/weighted.
- **Pros:** validación estructural al definir clase (rechaza estados sin transiciones), single `StateChart` API (vs 12 Machines), `py.typed` + mypy/pyright, DI, sync+async (`pytest-asyncio`), diagrams `pydot`. Más moderno que `transitions`.
- **Contras para este repo (vs pydantic-graph):**
  - **Sin integración LLM:** no hay `Agent`/`TestModel` ni `format_as_xml`, ni `output_type=DecisionAgentica` Grammar-Constrained. El Whiteboard es externo; el state es la máquina misma, no `ctx.state` mutable tipado con `Deps` (FakeAdapter).
  - **Modelo sync-first:** aunque hay soporte async, el core es event-driven `sm.send("event")` no `await graph.run(state=..., deps=...)` con `BaseNode` async. El `10 Hz loop` tick (`handle_gesto` por frame) encaja como evento, pero el nodo agéntico async (que llama LLM) no es un "state" sino un "invoke" — hay que envolverlo manualmente y manejar `loop.run_in_executor`.
  - **Transiciones requeridas:** el checker exige que todo `State` tenga out-transition; para `ABORTED` final con `reset()` habría que modelar explícito (ok, pero añade ruido vs `End`).
  - **Peso medio:** core 0 deps (mejor que LangGraph), pero con `diagrams`/`io` extra suma `pydot`/`jsonschema`/`pyyaml` — no relevante para headless. Bundle ~159 KiB similar a `pydantic-graph` pero sin reutilizar `pydantic`.

## 4. Tabla comparativa

| Dimensión | **pydantic-graph** (recomendado) | **LangGraph** | **transitions** | **python-statemachine** |
|---|---|---|---|---|
| **Paquete / versión estable** | `pydantic-graph==2.33.0` (local `2.32.1`, Production/Stable, `pydantic-ai-slim` lo trae) | `langgraph==1.2.11`, `langgraph-checkpoint 4.x`, `sdk 0.4.x` (Stable) | `transitions==0.9.3` (estable, maduro) | `python-statemachine==3.2.1` (estable) |
| **Licencia** | **MIT** | **MIT** | **MIT** | **MIT License** |
| **Bundle size (wheel)** | **~53 KiB** (`pydantic-graph`), 14 py files (~179 KiB) | `langgraph` ~249 KiB wheel + `langchain-core` + `checkpoint` + `sdk` + `prebuilt` + `xxhash` (~5 MB+ instalado) | ~113 KiB wheel (+ `six` 33 KiB) | ~159 KiB wheel (0 core deps) |
| **Deps directas** | `anyio>=4.7.0`, `logfire-api>=3.14.1`, `pydantic>=2.12`, `typing-inspection>=0.4.0` (4 leves, ya en tree si `pydantic-ai` está) | **6** (`langchain-core`, `checkpoint`, `prebuilt`, `sdk`, `pydantic`, `xxhash`) + trans 9 de `langchain-core` | **1** (`six`) | **0** core (extras `pydot`, `jsonschema`, `pyyaml`) |
| **Mypy strict py3.12** | **Sí** — `py.typed` presente, genéricos `BaseNode[StateT, DepsT, RunEndT]` + `GraphBuilder[StateT, DepsT, InputT, OutputT]`, cobertura mypy en `pydantic-ai` (`strict=true`, `explicit_package_bases=true`) | `py.typed` sí, pero **issues abiertos**: `Never` en functional API (#4140), `typeddict-item` patch parcial, `typing.TypedDict` vs `typing_extensions.TypedDict` (#1856) | **No** — no `py.typed`, callbacks por `str`, sin generics | **Sí** — `py.typed`, `mypy`/`pyright` en dev, `python_version=3.14` en tool.mypy, validación en definición |
| **Compat TestModel** | **Nativa** — `Agent(TestModel(...)).run()` dentro de `BaseNode.run()` (verificado). `agent.override(model=TestModel(...))` también | No — `FakeChatModel` de `langchain-core` (diverge de `fase-1/test_orchestrator.py`) | No — sin LLM, mock manual | No — idem |
| **Integración `openai:opencode/muse-spark-1.2`** | **Nativa** — `Agent("openai:opencode/muse-spark-1.2-contributor-free")` (OpenAI-compat, `OPENAI_BASE_URL` opcional) | Vía `langchain-openai ChatOpenAI(model="opencode/muse-spark-1.2", base_url=...)` — extra `langchain-openai` | No | No |
| **API Graph/State/Edge** | `BaseNode`, `End`, `GraphRunContext[state,deps]`, `GraphBuilder` con edges inferidos de `-> NodeA \| End`, `reduce_*`, mermaid, `iter()` | `StateGraph(TypedDict)`, `add_node/add_edge/add_conditional_edges`, `compile(checkpointer)`, `invoke/stream`, Pregel | `Machine(model, states, transitions, conditions)` imperativo | `StateChart` declarativo `State(...).to(...)` + `cond=` + DI |
| **Whiteboard (Reducer)** | **Nativo** — `ctx.state` mutable tipado + `Join(reducer=reduce_dict_update/sum/list_append)` = `Reducer` de CONTEXT.md | `Annotated[TypedDict, reducer]` (ej. `add_messages`) — reducers pero sobre `TypedDict` patch | Manual — `model` attrs | Manual — `StateChart` attrs + eventless transitions |
| **Async / 10 Hz loop** | **Async-first** — `async def run(ctx) -> ...`, `await graph.run()`, `async for step in graph.iter()` (tick a 10 Hz) | Async ok, pero `compile()` hace `inspect.getsource`+`ast.parse` por nodo (issue #8559) — overhead build no runtime | Sync (async extension no core) | Sync-first (async via `pytest-asyncio`, no nativo graph async) |
| **Path filtering / uv workspace** | **Cero costo** — añadir `pydantic-ai-slim` a member `plataforma/sim` o root `fase1` extra no toca `plataforma/webcam/backend` (filtra por path). `uv.lock` members intacto | Costo — `langgraph` tree agranda lock global, CI cache más pesado aunque path-filtered | Sin impacto (single dep) | Sin impacto (0 deps) |
| **CI sin mujoco** | **Pasa** — `FakeAdapter` inyectado vía `deps` o `TestModel` (headless, sin env) | Pasa (con `checkpointer=memory`) pero CI instala 5 paquetes extra siempre | Pasa | Pasa |
| **Observabilidad / grafos** | `logfire` (opcional) + `graph.render()` mermaid | `LangSmith` (requiere `langsmith` dep) + mermaid | `pygraphviz`/`pydot` opcional | `pydot` opcional |
| **Curva / docs** | Docs excelentes (`ai.pydantic.dev/graph`), pero "nail gun" — no beginner-friendly, heavy generics | Docs extensas pero dispersas (`langchain-ai/langgraph` monorepo) | Docs simples | Docs buenas (`python-statemachine.readthedocs.io`) |

> Nota pesos: tamaños wheel de `pypi.org/pypi/<pkg>/json` (urls[].size) y tree local `uv pip list` / `METADATA`. LangGraph wheel pequeño pero tree grande; `pydantic-graph` tree ya está si `pydantic-ai` está.

## 5. Trade-offs específicos a este repo (por qué pydantic-graph gana aquí)

1. **Uv workspace + path filtering:** `plataforma/webcam/backend` ya es miembro `uv` desacoplado (`pyproject.toml where=["."] include=["plataforma*"]` + `members=["plataforma/webcam/backend"]` + `packages=[]` en backend). Añadir `pydantic-ai-slim` al workspace root o a un nuevo miembro `plataforma/sim` no dispara el job `webcam` cuando solo cambia `plataforma/sim` (filter `plataforma/webcam/**`). Con LangGraph, el tree `langchain-core → langsmith → orjson` entra al lock global y cache CI aunque el job no lo use; `pydantic-graph` reutiliza `pydantic==2.x` ya presente.

2. **CI sin mujoco / 10 Hz loop:** el graph es **headless** (`FakeAdapter` que implementa `Protocol` con `SimObservation`, `CmdVel`, `SimMetrics`). `GraphRunContext.deps = SimDeps(adapter=FakeAdapter())` permite el loop `async for _ in range(hz): await graph.iter(...)` a 10 Hz sin GIL ni compilación Pregel con parseo de fuente por tick. `MissionFSM.handle_gesto` con histéresis N=5 (~500 ms @10 Hz) se modela como nodo `HandleGesto(BaseNode[MissionState, MissionDeps, ...])` que muta `ctx.state.mission_state: Estado` y deja `on_observacion` como hook no-op (igual que `fsm.py:131`).

3. **Mypy strict 3.12:** `pyproject.toml:31-37` tiene `strict=true`, `explicit_package_bases=true`, `python_version=3.12`. `pydantic-graph` tiene `py.typed` y pasa `mypy` en ese modo (ver `AGENTS.md` checklist `uv run mypy plataforma/webcam && uv run ruff ... && uv run pytest`). LangGraph rompe `strict` con `Never`/`TypedDict` patch; `transitions` no es mypy-usable.

4. **Dependencias livianas:** el ticket pide evaluar bundle size y peso. `pydantic-graph` añade **0 paquetes nuevos** si el repo ya usa `pydantic-ai-slim` (que ya trae 4 deps leves); transición a `langgraph` añade 5 paquetes + 9 transitivos. En un runner GitHub con cache `uv`, eso es diferencia de segundos por job × N jobs.

5. **Integración `Muse Spark opencode/muse-spark-1.2`:** el ticket exige `openai:opencode` model. Solo `pydantic-ai` soporta `Agent("openai:opencode/muse-spark-1.2-contributor-free")` con `OPENCODE_API_KEY` + `OPENAI_BASE_URL` nativos (ver `fase-1/gemini_client.py:20-31`, `orchestrator.py:39`). LangGraph requiere `langchain-openai` wrapper distinto; `transitions`/`statemachine` no tienen model.

6. **Los FSMs no compiten:** `transitions`/`python-statemachine` son FSMs imperativas/declarativas válidas **para envolver `MissionFSM`**, pero el ticket pide `StateGraph + Whiteboard + DecisionAgéntica`. La FSM actual ya es pura y testeada (`fsm.py`). El graph debe **componer** la FSM, no reemplazarla por otra FSM: `HandleGestoNode` delega a `mission_fsm.handle_gesto(GestoReconocido(...))` y `DecisionNode` llama `Agent(DecisionAgentica).run(...)`. Usar `python-statemachine` como engine redundaría con `MissionFSM` sin aportar agéntico.

## 6. Verificación local ejecutada (reproducible)

```bash
uv run --with pydantic-ai python -c "import pydantic_ai; print(pydantic_ai.__version__)"
# 2.32.1
uv pip list  # embebido en run: pydantic-ai 2.32.1, pydantic-ai-slim 2.32.1, pydantic-graph 2.32.1
python -c "import pydantic_graph; print(pydantic_graph.__file__)"
# .../site-packages/pydantic_graph/__init__.py  (14 .py, 179 KiB)
python -c "from pydantic_graph import BaseNode, End, GraphRunContext; help(BaseNode.run)"
# async def run(self, ctx: GraphRunContext[StateT, DepsT]) -> BaseNode | End

# TestModel dentro de nodo (ver §2.3) → OK
uv run --with pydantic-ai python verify_testmodel_in_node.py
# n2 type Decide / n3 type Finish / final done:a count=2 / TESTMODEL INSIDE GRAPH NODE: OK
```

- Pypi sizes vía `https://pypi.org/pypi/{pkg}/json` → `transitions` 113 KiB, `python-statemachine` 159 KiB, `langgraph` 249 KiB, `pydantic-graph` 53 KiB.
- Deps vía `METADATA Requires-Dist` locales (ver tabla §4).

## 7. Plan sugerido para 009/010 (sin código productivo, solo research)

- **Dependencia:** añadir `pydantic-ai-slim` (que trae `pydantic-graph==2.32.1`) al extra `fase1` o a nuevo miembro `plataforma/sim` (`uv add pydantic-ai-slim --optional fase1` o `uv add --project plataforma/sim pydantic-graph`). No tocar `plataforma/webcam/backend`.
- **State:** `MissionState` dataclass (`estado: Estado` de `fsm.py`, `whiteboard: dict | BaseModel` para contexto entre nodos, `last_gesto: GestoReconocido | None`). `SimDeps` dataclass (`adapter: SimAdapter | FakeAdapter`, `agent: Agent[HardwareContext, DecisionAgentica]` lazy).
- **Nodos (Borujo):** `TickNode → HandleGestoNode (wraps MissionFSM.handle_gesto con histéresis) → PercepcionGateNode → DecisionNode (Agent TestModel/openai:opencode) → ActNode (adapter.send_cmd_vel) → End` con `GraphBuilder(state_type=MissionState, deps_type=SimDeps, input_type=GestoReconocido|None, output_type=Estado)`.
- **Whiteboard/Reducer:** `ctx.state.whiteboard` + `Join(reducer=reduce_dict_update)` si se bifurca percepción/voz.
- **Tests:** `FakeAdapter` (ya previsto), `TestModel(custom_output_args=DecisionAgentica(...))`, `Graph.run(state=..., deps=...)` y `graph.iter()` para 10 Hz ticks, `graph.render()` para validar topología.
- **Mypy:** parametrizar todo `BaseNode[StateT, DepsT, Out]` explícito (no omitir `DepsT=None` si `RunEndT` se usa — posicional).
- **CI:** path filter `plataforma/webcam/**` no afectado; job `sim` con `uv sync --all-packages` corre `pytest plataforma/sim -q`.

## 8. Riesgos y notas

- `pydantic-graph` es async; `MissionFSM.handle_gesto` es sync puro. El nodo wrapper debe ser `async def run` y delegar sync sin `await` (no bloquear 10 Hz). Latencia del `DecisionNode` (LLM) dominará el tick — aislar tras gate `GestoReconocido` no-`none`.
- No usar `Graph` para la FSM simple (overkill). El graph es para el **orquestador cognitivo**: Whiteboard compartido + nodo LLM + adapter sim. La FSM `MissionFSM` permanece como lógica pura; el graph la orquesta.
- Si el ticket 009 quiere persistencia/checkpoints o human-in-loop interrupt, `pydantic-graph` no trae checkpointers durables; aportaría `iter()` + serialización manual `state` (`resume_tokens <500B` pattern del comparativo EPYC) — suficiente para FakeAdapter, no para Postgres-backed durable.

## Fuentes

- Pydantic AI — Graphs: `https://ai.pydantic.dev/graph/` (definición `BaseNode`, `GraphRunContext`, `End`, `Edge`, `GraphBuilder`, `pydantic-graph` sin dep `pydantic-ai`, mermaid).
- Pydantic AI — GenAI email feedback graph example (Agent dentro de `BaseNode.run`): `https://ai.pydantic.dev/graph/` §GenAI Example.
- Repo `pydantic-ai` — `pydantic_graph/pyproject.toml` (`anyio`, `logfire-api`, `pydantic`, `typing-inspection`), `pydantic_graph/basenode.py` & `graph_builder.py` (tipos `StateT/DepsT/RunEndT`).
- PyPI `pydantic-graph` `https://pypi.org/project/pydantic-graph/` (MIT, `anyio>=4.7.0 …`, wheel 53 KiB), `pydantic-ai 2.32.1`/`pydantic-graph 2.32.1` local `METADATA`.
- PyPI `langgraph` `https://pypi.org/pypi/langgraph/json` (MIT, `langchain-core<2,>=1.4.7`, `checkpoint`, `prebuilt`, `sdk`, `pydantic`, `xxhash`; wheel 249 KiB).
- LangGraph deps audit `https://benchclaw.io/langchain-vs-langgraph/` (5 paquetes efectivos, 41/102 files importan `langchain_core`, `langchain-core` 9 deps).
- LangGraph `libs/langgraph/pyproject.toml` `https://github.com/langchain-ai/langgraph/blob/4a86705b/libs/langgraph/pyproject.toml` (deps, `requires-python>=3.10`).
- LangGraph issues `#4140` (mypy `Never` functional API) y `#8559` (`inspect.getsource` build overhead).
- `transitions` PyPI `https://pypi.org/project/transitions/` (0.9.3, MIT, `six`).
- `python-statemachine` PyPI `https://pypi.org/project/python-statemachine/` (3.2.1, MIT License, 0 core deps; extras `pydot`, `jsonschema`, `pyyaml`), docs `https://python-statemachine.readthedocs.io/en/stable/` (declarative `StateChart`, `cond=` guards, DI).
- Repo local: `fase-1/orchestrator.py`, `fase-1/gemini_client.py`, `fase-1/test_orchestrator.py`, `pyproject.toml`, `CONTEXT.md`, `plataforma/webcam/backend/fsm.py`, `plataforma/webcam/backend/pyproject.toml`, `uv.lock`.

## Apéndice — snippet mínimo verificado (headless, sin prod)

```python
from dataclasses import dataclass
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_graph import BaseNode, End, GraphRunContext


@dataclass
class MissionState:
    count: int = 0
    last_answer: str = ""


class Out(BaseModel):
    answer: str


class Start(BaseNode[MissionState, None, str]):
    async def run(
        self, ctx: GraphRunContext[MissionState, None]
    ) -> "Decide | End[str]":
        ctx.state.count += 1
        return Decide()


class Decide(BaseNode[MissionState, None, str]):
    async def run(
        self, ctx: GraphRunContext[MissionState, None]
    ) -> "Finish | End[str]":
        agent = Agent(TestModel(), output_type=Out)
        result = await agent.run("decide")
        ctx.state.last_answer = result.output.answer
        return Finish()


class Finish(BaseNode[MissionState, None, str]):
    async def run(self, ctx: GraphRunContext[MissionState, None]) -> End[str]:
        ctx.state.count += 1
        return End(data=f"done:{ctx.state.last_answer} count={ctx.state.count}")


# GraphBuilder(state_type=MissionState, output_type=str) + g.node(...) + g.edge_from(g.start_node).to(start_step)
# Luego: await graph.run(state=MissionState())
# y para prod: Agent("openai:opencode/muse-spark-1.2-contributor-free", output_type=DecisionAgentica)
```
