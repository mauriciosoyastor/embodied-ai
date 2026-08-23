"""Handler WebSocket /ws/percepcion — envelope D5 + leaky queue N=1.

Contrato D5 (#43) y spec S2-B (#51):
- Envelope {type, seq, ts, payload} con type ∈ {frame,detecciones,gesto,estado}
- Cliente → frame {frame_id,jpeg_b64,width,height}
- Servidor → detecciones {frame_id,boxes} + gesto {frame_id,label,conf}
- boxes: [{x,y,w,h,cls,conf}] normalizadas [0,1]
- label ∈ {open_palm,fist,thumbs_up,none}
- Leaky N=1 servidor: descarta anterior si llega nuevo antes de inferir
- Cliente: ws.bufferedAmount>64KB → salta frame (frontend ws-client.js)

Solo importa inference/{yolo,gesture} vía interfaz — no acopla FSM.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast

from plataforma.webcam.backend.identities import store
from plataforma.webcam.backend.inference.gesture import (
    ALLOWED_LABELS,
    GestoReconocido,
    get_gesture_recognizer,
)
from plataforma.webcam.backend.inference.yolo import get_yolo_detector

# Global clients para broadcast purge (hibrido)
connected_clients: set[WebSocketLike] = set()

# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

EnvelopeType = Literal[
    "frame",
    "detecciones",
    "gesto",
    "estado",
    "enroll_sync",
    "enroll_ack",
    "purge",
    "purge_ack",
    "identities",
]
GestureLabelWs = Literal["open_palm", "fist", "thumbs_up", "none"]


class WebSocketLike(Protocol):
    """Protocolo mínimo para headless tests y FastAPI WebSocket."""

    async def accept(self) -> None: ...
    async def send_text(self, data: str) -> None: ...
    async def receive_text(self) -> str: ...


# ---------------------------------------------------------------------------
# Utilidades puras
# ---------------------------------------------------------------------------


def now_ms() -> int:
    """Unix epoch ms int — D5 ts."""
    return int(time.time() * 1000)


def make_envelope(
    type_: EnvelopeType,
    seq: int,
    payload: dict[str, Any],
    ts: int | None = None,
) -> dict[str, Any]:
    """Envelope D5 serializado."""
    if ts is None:
        ts = now_ms()
    return {"type": type_, "seq": seq, "ts": ts, "payload": payload}


def parse_envelope(raw: str) -> dict[str, Any]:
    """Parsea JSON envelope — lanza ValueError si inválido."""
    data: dict[str, Any] = json.loads(raw)
    has_keys = "type" in data and "seq" in data and "ts" in data and "payload" in data
    if not has_keys:
        msg = f"Envelope incompleto: {data}"
        raise ValueError(msg)
    if data["type"] not in (
        "frame",
        "detecciones",
        "gesto",
        "estado",
        "enroll_sync",
        "purge",
        "enroll_ack",
        "purge_ack",
        "identities",
    ):
        msg = f"Envelope type desconocido: {data['type']}"
        raise ValueError(msg)
    return data


def decode_jpeg_b64(jpeg_b64: str) -> Any | None:
    """Decodifica JPEG base64 a ndarray si opencv disponible; None si stub."""
    try:
        raw = base64.b64decode(jpeg_b64)
    except Exception:
        return None
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Leaky queue N=1
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LeakyQueue[T]:
    """Cola leaky N=1 — si está llena, descarta el más viejo y encola el nuevo.

    Síncrona para tests headless; expone variante asyncio con esperas.
    """

    maxsize: int = 1
    _deque: deque[T] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._deque = deque(maxlen=self.maxsize)

    def put(self, item: T) -> bool:
        """Encola; retorna True si descartó previo (leaky)."""
        discarded = len(self._deque) == self.maxsize and self.maxsize > 0
        # deque con maxlen descarta automáticamente el leftmost
        self._deque.append(item)
        return discarded

    def get(self) -> T | None:
        if not self._deque:
            return None
        return self._deque.popleft()

    def peek(self) -> T | None:
        if not self._deque:
            return None
        return self._deque[0]

    def __len__(self) -> int:
        return len(self._deque)

    def is_empty(self) -> bool:
        return len(self._deque) == 0


class AsyncLeakyQueue[T]:
    """Variante asyncio para el handler real — N=1 con descarte."""

    def __init__(self, maxsize: int = 1) -> None:
        self.maxsize = maxsize
        self._deque: deque[T] = deque(maxlen=maxsize)
        self._cond = asyncio.Condition()

    async def put(self, item: T) -> bool:
        async with self._cond:
            discarded = len(self._deque) == self.maxsize and self.maxsize > 0
            self._deque.append(item)
            self._cond.notify_all()
            return discarded

    async def get(self) -> T:
        async with self._cond:
            while not self._deque:
                await self._cond.wait()
            item = self._deque.popleft()
            return item

    def qsize(self) -> int:
        return len(self._deque)


# ---------------------------------------------------------------------------
# Inferencia pura (desacoplada)
# ---------------------------------------------------------------------------


def run_inference(
    jpeg_b64: str,
    frame_id: int,
    ts: int,
    width: int | None = None,
    height: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Ejecuta YOLO + gesto stub y retorna payloads serializados.

     Returns: (boxes_payload_list, gesto_payload)
    _boxes coords normalizadas [0,1]; cls=str COCO; conf 0-1
     gesto label ∈ allowed, conf 0-1
    """
    _ = width
    _ = height
    img = decode_jpeg_b64(jpeg_b64)
    yolo = get_yolo_detector()
    gesture_rec = get_gesture_recognizer()

    # YOLO
    boxes = yolo.predict(img)
    boxes_payload: list[dict[str, Any]] = []
    for b in boxes:
        # clamp normalizado [0,1] — defensa serialización
        x = max(0.0, min(1.0, float(b.x)))
        y = max(0.0, min(1.0, float(b.y)))
        w = max(0.0, min(1.0, float(b.w)))
        h = max(0.0, min(1.0, float(b.h)))
        conf = max(0.0, min(1.0, float(b.conf)))
        boxes_payload.append(
            {"x": x, "y": y, "w": w, "h": h, "cls": str(b.cls), "conf": conf}
        )

    # Gesto — mapea GestoReconocido → payload wire
    gesto_event: GestoReconocido = gesture_rec.recognize(
        image=img, frame_id=frame_id, ts=ts
    )
    label: str = gesto_event.label
    if label not in ALLOWED_LABELS:
        label = "none"
    # cast para mypy Literal
    gesture_label = cast(GestureLabelWs, label)
    gesto_payload: dict[str, Any] = {
        "frame_id": frame_id,
        "label": gesture_label,
        "conf": max(0.0, min(1.0, float(gesto_event.conf))),
    }
    return boxes_payload, gesto_payload


async def handle_enroll_sync(
    websocket: WebSocketLike,
    payload: dict[str, Any],
    seq_counter: list[int],
) -> None:
    """Guarda enroll_sync en store y responde enroll_ack (bypass LeakyQueue)."""
    rid = str(payload.get("id") or "")
    nombre = str(payload.get("nombre") or "").strip()
    embedding = payload.get("embedding")
    if not rid or not nombre or not isinstance(embedding, list):
        # ack error
        seq_counter[0] += 1
        err = make_envelope(
            "enroll_ack",
            seq_counter[0],
            {"id": rid, "status": "error", "reason": "payload invalido"},
        )
        try:
            await websocket.send_text(json.dumps(err))
        except Exception:
            pass
        return
    try:
        rec = await store.enroll({"id": rid, "nombre": nombre, "embedding": embedding})
        seq_counter[0] += 1
        ack = make_envelope(
            "enroll_ack",
            seq_counter[0],
            {"id": rid, "status": "ok", "count": rec.get("count", 1)},
        )
        await websocket.send_text(json.dumps(ack))
    except Exception as e:
        seq_counter[0] += 1
        err = make_envelope(
            "enroll_ack",
            seq_counter[0],
            {"id": rid, "status": "error", "reason": str(e)},
        )
        try:
            await websocket.send_text(json.dumps(err))
        except Exception:
            pass


async def handle_purge(
    websocket: WebSocketLike,
    payload: dict[str, Any],
    seq_counter: list[int],
) -> None:
    """Purge broadcast: limpia store y notifica a todos los clientes."""
    all_ = bool(payload.get("all", False))
    ids = payload.get("ids")
    ids_list = [str(x) for x in ids] if isinstance(ids, list) else None
    try:
        n = await store.purge(all_=all_, ids=ids_list)
        seq_counter[0] += 1
        ack = make_envelope("purge_ack", seq_counter[0], {"n": n, "all": all_})
        # broadcast a todos los conectados
        for ws in list(connected_clients):
            try:
                await ws.send_text(json.dumps(ack))
            except Exception:
                pass
        # si no hay broadcast (solo este ws), al menos responde
        if not connected_clients:
            await websocket.send_text(json.dumps(ack))
    except Exception as e:
        seq_counter[0] += 1
        err = make_envelope("purge_ack", seq_counter[0], {"n": 0, "error": str(e)})
        try:
            await websocket.send_text(json.dumps(err))
        except Exception:
            pass


async def process_single_frame(
    websocket: WebSocketLike,
    frame_payload: dict[str, Any],
    seq_counter: list[int],
) -> None:
    """Procesa un frame y envía detecciones + gesto con seq incremental.

    seq_counter es lista mutable [seq] para incrementar across calls.
    """
    frame_id_any = frame_payload.get("frame_id")
    if not isinstance(frame_id_any, int):
        # frame_id debe ser int para correlación
        return
    frame_id: int = frame_id_any
    jpeg_b64 = str(frame_payload.get("jpeg_b64", ""))
    width = frame_payload.get("width")
    height = frame_payload.get("height")
    w_int = int(width) if isinstance(width, int) else None
    h_int = int(height) if isinstance(height, int) else None
    ts = now_ms()

    boxes_payload, gesto_payload = run_inference(
        jpeg_b64=jpeg_b64, frame_id=frame_id, ts=ts, width=w_int, height=h_int
    )

    # detecciones
    seq_counter[0] += 1
    det_env = make_envelope(
        "detecciones",
        seq_counter[0],
        {"frame_id": frame_id, "boxes": boxes_payload},
        ts=ts,
    )
    await websocket.send_text(json.dumps(det_env))

    # gesto
    seq_counter[0] += 1
    gesto_env = make_envelope("gesto", seq_counter[0], gesto_payload, ts=ts)
    await websocket.send_text(json.dumps(gesto_env))


# ---------------------------------------------------------------------------
# Handler WebSocket real
# ---------------------------------------------------------------------------


async def perception_ws_handler(websocket: WebSocketLike) -> None:
    """Handler /ws/percepcion — loop con leaky queue N=1 + enroll_sync/purge bypass.

    Acepta WS, recibe envelopes, aplica leaky queue solo para frame,
    y maneja enroll_sync/purge via branch paralelo (bypass N=1).
    """
    await websocket.accept()
    connected_clients.add(websocket)
    seq_counter: list[int] = [0]
    queue: AsyncLeakyQueue[dict[str, Any]] = AsyncLeakyQueue(maxsize=1)

    async def receiver() -> None:
        while True:
            try:
                raw = await websocket.receive_text()
            except Exception:
                break
            try:
                env = parse_envelope(raw)
            except ValueError:
                continue
            typ = env["type"]
            payload = env["payload"]
            if not isinstance(payload, dict):
                continue
            # Bypass LeakyQueue para control (Ticket 024)
            if typ == "enroll_sync":
                await handle_enroll_sync(websocket, payload, seq_counter)
                continue
            if typ == "purge":
                await handle_purge(websocket, payload, seq_counter)
                continue
            if typ != "frame":
                continue
            # Leaky: si llega nuevo antes de consumir, descarta anterior
            await queue.put(payload)

    async def processor() -> None:
        while True:
            try:
                frame_payload = await queue.get()
            except asyncio.CancelledError:
                break
            except Exception:
                break
            try:
                await process_single_frame(websocket, frame_payload, seq_counter)
            except Exception:
                # No cerrar WS por error de frame individual
                continue

    recv_task = asyncio.create_task(receiver())
    proc_task = asyncio.create_task(processor())
    try:
        await asyncio.gather(recv_task, proc_task)
    except asyncio.CancelledError:
        pass
    finally:
        connected_clients.discard(websocket)
        recv_task.cancel()
        proc_task.cancel()
        # best-effort cancel wait
        try:
            await recv_task
        except asyncio.CancelledError:
            pass
        try:
            await proc_task
        except asyncio.CancelledError:
            pass
