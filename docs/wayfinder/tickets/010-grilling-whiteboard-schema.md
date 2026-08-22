# Ticket 010 — Grilling: Schema del Whiteboard

> Label: `wayfinder:grilling` · Parent: `001-map-orchestrador-sim.md` · Estado: cerrado · Resolución: 2026-08-22

## Resolución

**Decisión HITL Q1-Q3 (aprobado recomendado 2026-08-22):**

- **Q1 Campos** — `WhiteboardState(BaseModel)` en `plataforma/sim/whiteboard.py` (o `state.py`) con: `estado: Literal[SIM_IDLE,SIM_RUNNING,SIM_PAUSED,SIM_ABORTED]`, `last_gesto: GestoReconocido|None`, `last_observation: SimObservation|None`, `last_decision: DecisionAgentica|None`, `metrics: SimMetrics|None`, `frame_id: int`. **Sin `transcript`** — voz queda en `plataforma/webcam` (`percepcion-panel`); sim Whiteboard es puro `obs/gesto/decision/metrics`. Evita acoplamiento.
- **Q2 Ubicación/tipo** — `WhiteboardState` embebido en `MissionState` dataclass (`ctx.state.whiteboard: WhiteboardState`, `ctx.state.estado` alias), `single-writer` (solo nodos `Tick/Decision/Act` mutan `ctx.state`), lectura libre. Solo memoria, no persistencia `whiteboard.json` (fog).
- **Q3 Reducer** — queda en **fog** `Not yet specified`; para `FakeAdapter` headless basta `ctx.state` mutable. Futuro `Join(reducer=reduce_dict_update)` cuando haya bifurcación percepción/voz.

**Spec (para 012):**

```python
from pydantic import BaseModel
from typing import Literal
from plataforma.sim.models import SimObservation, SimMetrics
from fase-1.orchestrator import DecisionAgentica # via sys.path

class GestoReconocido(BaseModel):
    label: Literal["open_palm","fist","thumbs_up","none"]
    conf: float; frame_id: int; ts: float

class WhiteboardState(BaseModel):
    estado: Literal["SIM_IDLE","SIM_RUNNING","SIM_PAUSED","SIM_ABORTED"] = "SIM_IDLE"
    frame_id: int = 0
    last_gesto: GestoReconocido | None = None
    last_observation: SimObservation | None = None
    last_decision: DecisionAgentica | None = None
    metrics: SimMetrics | None = None

@dataclass
class MissionState:
    whiteboard: WhiteboardState = field(default_factory=WhiteboardState)
    # alias: estado property → whiteboard.estado
```

> Estado previo: abierto · HITL → desbloquea 012 parcial

## Question

¿Schema Pydantic del Whiteboard que conecta orquestador ↔ sim?

Decidir (grilling + domain-modeling):
- Campos: `SimObservation` (`x,y,yaw, v_x,v_y,omega, ts, frame_id`, SI/world-frame `CONTEXT.md:47`) + `GestoReconocido` (`label, conf, frame_id, ts`) + `DecisionAgentica` (`accion, razon, nivel_confianza` `fase-1/orchestrator.py:13`) + `SimMetrics` (`steps/s, dt` `CONTEXT.md:49`) — ¿añadir `transcript` voz (`usuario→LLM`) de `plataforma/webcam/frontend/src/main.js:122`?
- ¿Whiteboard es `BaseModel` mutable con `Reducer` futuro (fog) o dict inmutable por ahora? ¿Dónde vive: `plataforma/sim/whiteboard.py` vs `fase-1/whiteboard.py` vs `plataforma/webcam/backend/whiteboard.py`?
- ¿Single writer (orquestador) o multi-writer (sim + percepción)? ¿Thread/async safety?
- ¿Persistencia: solo memoria para prototipo (fog: `whiteboard.json`), no commit?
- Contraste con `CONTEXT.md:20` `Whiteboard` actual (intercambio entre modelos) — ¿redefinir?
- Salida: `whiteboard.py` spec Pydantic + ejemplo `WhiteboardState` serializable, validado `mypy --strict`.

Bloqueado por 008 (forma del GraphState depende de librería). Desbloquea 012.
