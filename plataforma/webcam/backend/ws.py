"""Handler WebSocket /ws/percepcion — envelope D5 + leaky N=1 + v2.

Contrato D5 (#43) y spec v2 (#81):
- Envelope {type, seq, ts, payload} con types frame/detecciones/gesto/etc.
- 2 AsyncLeakyQueue N=1: fast 10Hz YOLO+gesto, slow 5Hz pose+depth to_thread
- VLM 1Hz scene_caption cada 30 frames Groq→HF→Gemini→mock
- run_inference filtra whitelist 13 clases + conf/area antes de serializar
- seq_counter único, intra_op 2 por Session
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast

from plataforma.webcam.backend.config import (
    VLM_ENABLED,
    VLM_INTERVAL,
    YOLO_AREA_MIN,
    YOLO_CONF,
    YOLO_PERSON_AREA_MIN,
    YOLO_PERSON_CONF,
    YOLO_WHITELIST,
)
from plataforma.webcam.backend.fsm import GestoReconocido as FsmGesto
from plataforma.webcam.backend.fsm import MissionFSM
from plataforma.webcam.backend.identities import store
from plataforma.webcam.backend.inference.gesture import (
    ALLOWED_LABELS,
    GestoReconocido,
    get_gesture_recognizer,
)
from plataforma.webcam.backend.inference.yolo import get_yolo_detector
from plataforma.webcam.backend.metrics import (
    record_dropped_frame,
    record_inference,
    record_total,
)

# Global clients para broadcast purge (hibrido)
connected_clients: set[WebSocketLike] = set()
# FSM singleton para WS — histéresis N=5 latch ABORTED (Ticket 01)
_mission_fsm = MissionFSM()
# último mission emitido para evitar spam de envelopes
_last_mission: str | None = None
# S3 — último PercepcionVista para anclaje voz frame_id
last_atributos: list[dict[str, Any]] = []
last_frame_id: int = 0
last_ts: int = 0

# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

EnvelopeType = Literal[
    "frame",
    "detecciones",
    "gesto",
    "estado",
    "scene_caption",
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
        "scene_caption",
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
    """Decodifica JPEG base64 a ndarray si opencv disponible; None si stub.

    Zero-Copy (041): memoryview evita copy inter-proceso hacia np.ndarray.
    """
    try:
        raw = base64.b64decode(jpeg_b64)
    except Exception:
        return None
    try:
        import cv2
        import numpy as np

        # Zero-Copy: memoryview no copia buffer bytes → np.frombuffer view
        arr = np.frombuffer(memoryview(raw), dtype=np.uint8)
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


def _passes_whitelist(box: Any) -> bool:
    """Filtro whitelist + conf/area previo a serialización."""
    cls = str(getattr(box, "cls", ""))
    if cls not in YOLO_WHITELIST:
        return False
    conf = float(getattr(box, "conf", 0.0))
    w = float(getattr(box, "w", 0.0))
    h = float(getattr(box, "h", 0.0))
    area = max(0.0, w) * max(0.0, h)
    if cls == "person":
        return conf >= YOLO_PERSON_CONF and area >= YOLO_PERSON_AREA_MIN
    return conf >= YOLO_CONF and area >= YOLO_AREA_MIN


# --- AtributoVista helpers S1 (HSV <1ms, sin red) ---

_HSV_BINS = 18
_HSV_COLOR_NAMES = [
    "rojo",
    "naranja",
    "amarillo",
    "verde",
    "cian",
    "azul",
    "violeta",
    "magenta",
    "rojo",
    "rojo",
    "naranja",
    "amarillo",
    "verde",
    "cian",
    "azul",
    "violeta",
    "magenta",
    "rojo",
]
_HSV_HEX = {
    "rojo": "#c0392b",
    "naranja": "#e67e22",
    "amarillo": "#f1c40f",
    "verde": "#27ae60",
    "cian": "#1abc9c",
    "azul": "#2980b9",
    "violeta": "#8e44ad",
    "magenta": "#d252b2",
    "gris": "#7f8c8d",
    "blanco": "#ecf0f1",
    "negro": "#1a1a1a",
    "unknown": "#64748b",
}


def _tamano_from_area(area: float) -> str:
    if area < 0.05:
        return "pequeño"
    if area < 0.15:
        return "mediano"
    return "grande"


def _color_hsv_from_crop(crop: Any) -> tuple[str, str]:
    """Histograma 18 bins H con máscara S>50 V>50 — <0.1ms por crop."""
    if crop is None:
        return "unknown", _HSV_HEX["unknown"]
    try:
        import cv2
        import numpy as np

        if crop.size == 0:
            return "unknown", _HSV_HEX["unknown"]
        # stats para grises
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        # máscara saturación/valor
        mask = ((hsv[:, :, 1] > 50) & (hsv[:, :, 2] > 50)).astype(np.uint8) * 255
        # grises/blanco/negro si poca saturación
        mean_s = float(np.mean(hsv[:, :, 1]))
        mean_v = float(np.mean(hsv[:, :, 2]))
        if mean_s < 35 and mean_v > 200:
            return "blanco", _HSV_HEX["blanco"]
        if mean_v < 40:
            return "negro", _HSV_HEX["negro"]
        if mean_s < 25:
            return "gris", _HSV_HEX["gris"]
        hist = cv2.calcHist([hsv], [0], mask, [_HSV_BINS], [0, 180])
        if hist is None or hist.size == 0 or float(np.sum(hist)) < 10:
            return "gris", _HSV_HEX["gris"]
        dom = int(np.argmax(hist))
        name = _HSV_COLOR_NAMES[dom % len(_HSV_COLOR_NAMES)]
        return name, _HSV_HEX.get(name, _HSV_HEX["unknown"])
    except Exception:
        return "unknown", _HSV_HEX["unknown"]


def _extract_atributos(
    boxes: list[Any],
    img: Any | None,
    frame_id: int,
    ts: int,
    track_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Construye AtributoVista dicts serializables para Envelope detec./Whiteboard."""
    # S2-B: LRU cache por track_id + IoU>0.85 evita recalcular HSV
    try:
        from plataforma.webcam.backend.tracker import (
            get_tracker,  # local import evita ciclo
        )

        tracker = get_tracker()
        lru = tracker.lru
    except Exception:
        tracker = None  # type: ignore
        lru = None  # type: ignore
    out: list[dict[str, Any]] = []
    for idx, b in enumerate(boxes):
        x = max(0.0, min(1.0, float(getattr(b, "x", 0.0))))
        y = max(0.0, min(1.0, float(getattr(b, "y", 0.0))))
        w = max(0.0, min(1.0, float(getattr(b, "w", 0.0))))
        h = max(0.0, min(1.0, float(getattr(b, "h", 0.0))))
        cls = str(getattr(b, "cls", ""))
        conf = max(0.0, min(1.0, float(getattr(b, "conf", 0.0))))
        area = max(0.0, w) * max(0.0, h)
        tamano = _tamano_from_area(area)
        centroide = {
            "x_c": max(0.0, min(1.0, x + w / 2.0)),
            "y_c": max(0.0, min(1.0, y + h / 2.0)),
        }
        bbox = {"x": x, "y": y, "w": w, "h": h}
        # S2-B: track_id persistente vía ByteTrack, fallback idx
        track_id = int(track_ids[idx]) if track_ids and idx < len(track_ids) else idx
        # crop para color — LRU hit evita histograma
        color_name: str = "unknown"
        color_hex: str = _HSV_HEX["unknown"]
        cached = None
        if lru is not None:
            try:
                cached = lru.get(track_id, bbox, now_ms=ts)
            except Exception:
                cached = None
        if cached is not None:
            color_name = str(cached.get("color_hsv", "unknown"))
            color_hex = str(cached.get("color_hex", _HSV_HEX["unknown"]))
        elif img is not None:
            try:
                ih, iw = img.shape[:2]
                x1 = int(round(x * iw))
                y1 = int(round(y * ih))
                x2 = int(round((x + w) * iw))
                y2 = int(round((y + h) * ih))
                x1, x2 = max(0, x1), min(iw, x2)
                y1, y2 = max(0, y1), min(ih, y2)
                if x2 > x1 and y2 > y1:
                    crop = img[y1:y2, x1:x2]
                    color_name, color_hex = _color_hsv_from_crop(crop)
                    if lru is not None:
                        try:
                            lru.put(track_id, bbox, color_name, color_hex, ts=ts)
                        except Exception:
                            pass
            except Exception:
                pass
        # z_rel null en S1 (depth piggyback en slow_processor)
        out.append(
            {
                "track_id": track_id,
                "cls": cls,
                "conf": conf,
                "bbox": bbox,
                "centroide": centroide,
                "tamano": tamano,
                "area": area,
                "z_rel": None,
                "z_m": None,
                "color_hsv": color_name,
                "color_hsv_hex": color_hex,
                "color_vlm": None,
                "color": color_name,
                "frame_id": frame_id,
                "ts": ts,
                "ttl_ms": {
                    "bbox": 100,
                    "color_hsv": 200,
                    "z_rel": 500,
                    "color_vlm": 3000,
                },
                # compat flat para overlay.js ya existente
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
        )
    return out


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
    Filtra por whitelist + conf/area antes de serializar (v2).
    S1: cada box incluye AtributoVista
        (centroide, tamano, area, color_hsv, z_rel) para compat.
    """
    _ = width
    _ = height
    img = decode_jpeg_b64(jpeg_b64)
    yolo = get_yolo_detector()
    gesture_rec = get_gesture_recognizer()

    # YOLO
    boxes = yolo.predict(img)
    # filtra whitelist primero
    filtered: list[Any] = [b for b in boxes if _passes_whitelist(b)]
    # S2-B: track_id persistente ByteTrack IoU>0.5 edad 30
    try:
        from plataforma.webcam.backend.tracker import get_tracker

        tracker = get_tracker()
        track_ids = tracker.update(filtered)
    except Exception:
        track_ids = list(range(len(filtered)))
    # AtributoVista enriquecido S1+S2-B (incluye compat flat x/y/w/h + LRU)
    boxes_payload: list[dict[str, Any]] = _extract_atributos(
        filtered, img, frame_id, ts, track_ids=track_ids
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
# VLM helper
# ---------------------------------------------------------------------------


async def _send_scene_caption(
    websocket: WebSocketLike,
    frame_id: int,
    seq_counter: list[int],
    seq_lock: asyncio.Lock,
    objects: list[str] | None = None,
    image_b64: str | None = None,
) -> None:
    """Genera scene_caption via VLM y envía envelope con seq único."""
    try:
        from plataforma.webcam.backend.inference.vlm import get_vlm_client
    except Exception:
        return
    try:
        client = get_vlm_client()

        def _call() -> Any:
            return client.caption(
                image_b64=image_b64, frame_id=frame_id, objects=objects
            )

        leyenda = await asyncio.to_thread(_call)
        payload: dict[str, Any] = {
            "frame_id": int(leyenda.frame_id),
            "caption": str(leyenda.caption),
            "objects": list(leyenda.objects),
            "conf": float(leyenda.conf),
            "ts": int(leyenda.ts),
            "provider": str(leyenda.provider),
        }
        async with seq_lock:
            seq_counter[0] += 1
            seq = seq_counter[0]
        env = make_envelope("scene_caption", seq, payload, ts=int(leyenda.ts))
        await websocket.send_text(json.dumps(env))
    except Exception:
        return


# ---------------------------------------------------------------------------
# Handler WebSocket real — v2 dual queue + VLM tick
# ---------------------------------------------------------------------------


async def perception_ws_handler(websocket: WebSocketLike) -> None:
    """Handler /ws/percepcion — loop con 2 leaky queues + VLM 1Hz.

    - fast_queue 10Hz para YOLO+gesto (run_inference)
    - slow_queue 5Hz para pose+depth via asyncio.to_thread gather intra2
    - vlm_tick cada VLM_INTERVAL frames para scene_caption
    - seq_counter único con lock para todas las ramas
    """
    await websocket.accept()
    connected_clients.add(websocket)
    seq_counter: list[int] = [0]
    seq_lock = asyncio.Lock()
    fast_queue: AsyncLeakyQueue[dict[str, Any]] = AsyncLeakyQueue(maxsize=1)
    slow_queue: AsyncLeakyQueue[dict[str, Any]] = AsyncLeakyQueue(maxsize=1)
    frame_tick: list[int] = [0]
    slow_tick: list[int] = [0]

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
                async with seq_lock:
                    # handle_enroll_sync usa seq_counter mutable; proteger con lock
                    # pero mantenemos llamada sin lock externo para no bloquear
                    pass
                await handle_enroll_sync(websocket, payload, seq_counter)
                continue
            if typ == "purge":
                await handle_purge(websocket, payload, seq_counter)
                continue
            if typ != "frame":
                continue
            # Leaky: si llega nuevo antes de consumir, descarta anterior
            dropped_fast = await fast_queue.put(payload)
            if dropped_fast:
                try:
                    record_dropped_frame(1)
                except Exception:
                    pass
            # S2-C Zero-Copy: slow_queue guarda referencia img_view sin Base64 copy
            try:
                jpeg_b64_slow = str(payload.get("jpeg_b64", ""))
                img_view = decode_jpeg_b64(jpeg_b64_slow)
                if img_view is None:
                    import numpy as np

                    img_view = np.zeros((480, 640, 3), dtype=np.uint8)
                payload_slow = dict(payload)
                # view por referencia — no serializa Base64 de nuevo en slow path
                payload_slow["img_view"] = img_view  # type: ignore
                payload_slow["_zero_copy"] = True  # type: ignore
                dropped_slow = await slow_queue.put(payload_slow)
                if dropped_slow:
                    try:
                        record_dropped_frame(1)
                    except Exception:
                        pass
            except Exception:
                dropped_fallback = await slow_queue.put(payload)
                if dropped_fallback:
                    try:
                        record_dropped_frame(1)
                    except Exception:
                        pass

    async def fast_processor() -> None:
        while True:
            try:
                frame_payload = await fast_queue.get()
            except asyncio.CancelledError:
                break
            except Exception:
                break
            try:
                # fast inference sincrónico (YOLO+gesto)
                frame_id_any = frame_payload.get("frame_id")
                if not isinstance(frame_id_any, int):
                    continue
                frame_id: int = frame_id_any
                jpeg_b64 = str(frame_payload.get("jpeg_b64", ""))
                width = frame_payload.get("width")
                height = frame_payload.get("height")
                w_int = int(width) if isinstance(width, int) else None
                h_int = int(height) if isinstance(height, int) else None
                ts = now_ms()
                # 041: to_thread libera loop sin pool 4 hilos
                infer_start = time.perf_counter()
                total_start = infer_start
                boxes_payload, gesto_payload = await asyncio.to_thread(
                    run_inference,
                    jpeg_b64,
                    frame_id,
                    ts,
                    w_int,
                    h_int,
                )
                try:
                    infer_ms = (time.perf_counter() - infer_start) * 1000.0
                    total_ms = (time.perf_counter() - total_start) * 1000.0
                    record_inference(infer_ms)
                    record_total(total_ms)
                except Exception:
                    pass
                # S3 — anclaje voz frame_id + actualizar global last_atributos
                try:
                    global last_atributos, last_frame_id, last_ts

                    last_atributos = list(boxes_payload)
                    last_frame_id = frame_id
                    last_ts = ts
                    # S3 dynamic PromptList: si YOLO_WORLD_DYNAMIC_BY_VOZ y payload trae transcript, actualizar  # noqa: E501
                    # (transcript vendría por ws control, no por frame; se maneja en VozHandler)  # noqa: E501
                except Exception:
                    pass
                async with seq_lock:
                    seq_counter[0] += 1
                    det_seq = seq_counter[0]
                det_env = make_envelope(
                    "detecciones",
                    det_seq,
                    {"frame_id": frame_id, "boxes": boxes_payload},
                    ts=ts,
                )
                await websocket.send_text(json.dumps(det_env))
                async with seq_lock:
                    seq_counter[0] += 1
                    gesto_seq = seq_counter[0]
                gesto_env = make_envelope("gesto", gesto_seq, gesto_payload, ts=ts)
                await websocket.send_text(json.dumps(gesto_env))

                # FSM cableada (Ticket 01) — histéresis N=5 latch ABORTED
                try:
                    label_raw = str(gesto_payload.get("label", "none"))
                    conf_raw = float(gesto_payload.get("conf", 0.0))
                    # validar label para fsm
                    if label_raw not in ("open_palm", "fist", "thumbs_up", "none"):
                        label_raw = "none"
                    fsm_event = FsmGesto(
                        label=label_raw,  # type: ignore[arg-type]
                        conf=conf_raw,
                        frame_id=frame_id,
                        ts=ts,
                    )
                    new_state = _mission_fsm.handle_gesto(fsm_event)
                    mission_str = new_state.value
                    global _last_mission
                    # emitir siempre para que frontend refleje aunque no cambie  # noqa: E501
                    # pero throttling: solo si cambió o cada 5 ticks para no spam
                    should_emit = mission_str != _last_mission or frame_tick[0] % 5 == 0
                    if should_emit:
                        _last_mission = mission_str
                        async with seq_lock:
                            seq_counter[0] += 1
                            estado_seq = seq_counter[0]
                        estado_env = make_envelope(
                            "estado",
                            estado_seq,
                            {"mission": mission_str, "frame_id": frame_id},
                            ts=ts,
                        )
                        await websocket.send_text(json.dumps(estado_env))
                except Exception:
                    pass

                # VLM tick cada VLM_INTERVAL frames
                frame_tick[0] += 1
                if VLM_ENABLED and frame_tick[0] % VLM_INTERVAL == 0:
                    objs = [str(b.get("cls", "")) for b in boxes_payload]
                    # no await blocking: lanzar task detached con seq shared
                    asyncio.create_task(
                        _send_scene_caption(
                            websocket,
                            frame_id,
                            seq_counter,
                            seq_lock,
                            objects=objs,
                            image_b64=jpeg_b64,
                        )
                    )
            except Exception:
                # No cerrar WS por error de frame individual
                continue

    async def slow_processor() -> None:
        while True:
            try:
                frame_payload = await slow_queue.get()
            except asyncio.CancelledError:
                break
            except Exception:
                break
            try:
                # Gating 5Hz (Ticket 03): subsampling cada 2 frames  # noqa: E501
                slow_tick[0] += 1
                if slow_tick[0] % 2 == 1:
                    # skip 1 de cada 2 para 5Hz vs 10Hz fast
                    continue
                # si fast tiene backlog, saltar slow para priorizar gestos
                if fast_queue.qsize() > 0:
                    continue
                frame_id_any = frame_payload.get("frame_id")
                if not isinstance(frame_id_any, int):
                    continue
                frame_id: int = frame_id_any
                # S2-C Zero-Copy: si viene img_view por referencia, úsala sin decode
                img = frame_payload.get("img_view")  # type: ignore
                if img is None:
                    jpeg_b64 = str(frame_payload.get("jpeg_b64", ""))
                    img = decode_jpeg_b64(jpeg_b64)
                if img is None:
                    # fallback a zeros para headless tests con b64 dummy inválido
                    try:
                        import numpy as np

                        img = np.zeros((480, 640, 3), dtype=np.uint8)
                    except Exception:
                        continue

                # Reuso boxes_payload (Ticket 02): usa last_atributos si frame cercano, evita doble yolo.predict  # noqa: E501
                boxes_for_depth: list[dict[str, Any]] | None = None
                try:
                    # last_atributos del fast_processor mas reciente; acepta frame_id +-2 o ts reciente  # noqa: E501
                    if last_atributos and last_ts:
                        age_ok = (now_ms() - int(last_ts)) < 300
                        frame_close = abs(int(last_frame_id) - int(frame_id)) <= 2
                        if age_ok or frame_close:
                            boxes_for_depth = [
                                {
                                    "x": float(b.get("x", 0)),
                                    "y": float(b.get("y", 0)),
                                    "w": float(b.get("w", 0)),
                                    "h": float(b.get("h", 0)),
                                }
                                for b in last_atributos
                            ]
                except Exception:
                    boxes_for_depth = None
                # Fallback si no hay cache (headless primer frame)
                if boxes_for_depth is None:
                    cached = frame_payload.get("boxes_payload")  # type: ignore
                    if isinstance(cached, list) and cached:
                        boxes_for_depth = cached  # type: ignore
                from plataforma.webcam.backend.inference.depth import (
                    get_depth_estimator,
                )
                from plataforma.webcam.backend.inference.pose import get_pose_detector

                pose_detector = get_pose_detector()
                depth_estimator = get_depth_estimator()

                # ejecutar ambos en paralelo via to_thread con intra_op 2
                def _pose_call() -> Any:
                    return pose_detector.predict(img)

                def _depth_call() -> Any:
                    dict_boxes = boxes_for_depth  # type: ignore
                    if dict_boxes is None:
                        # ultimo fallback: re-ejecutar YOLO solo si cache miss  # noqa: E501
                        yolo = get_yolo_detector()
                        y_boxes = yolo.predict(img)
                        filtered = [b for b in y_boxes if _passes_whitelist(b)]
                        dict_boxes = [
                            {
                                "x": float(b.x),
                                "y": float(b.y),
                                "w": float(b.w),
                                "h": float(b.h),
                            }
                            for b in filtered
                        ]
                    return depth_estimator.estimate(img, dict_boxes, frame_id=frame_id)

                # gather paralelo sin jitter
                pose_res, depth_res = await asyncio.gather(
                    asyncio.to_thread(_pose_call),
                    asyncio.to_thread(_depth_call),
                )
                # Piggyback opc; no rompe seq; debug estado si hay datos
                # overlay v2 aún no consume, pero mantiene TTL
                _ = pose_res
                _ = depth_res
                # Opcional: enviar estado con posturas/profundidades si no stub
                # Mantenemos seq coherente si emitimos
                # Para no inflar seq en headless stub (pose_res==[]), skip
                if pose_res or depth_res:
                    async with seq_lock:
                        seq_counter[0] += 1
                        st_seq = seq_counter[0]
                    payload_state: dict[str, Any] = {
                        "frame_id": frame_id,
                        "posturas": len(pose_res) if pose_res else 0,
                        "profundidades": len(depth_res) if depth_res else 0,
                    }
                    st_env = make_envelope("estado", st_seq, payload_state)
                    try:
                        await websocket.send_text(json.dumps(st_env))
                    except Exception:
                        pass
            except Exception:
                continue

    recv_task = asyncio.create_task(receiver())
    fast_task = asyncio.create_task(fast_processor())
    slow_task = asyncio.create_task(slow_processor())
    try:
        await asyncio.gather(recv_task, fast_task, slow_task)
    except asyncio.CancelledError:
        pass
    finally:
        connected_clients.discard(websocket)
        for t in (recv_task, fast_task, slow_task):
            t.cancel()
        for t in (recv_task, fast_task, slow_task):
            try:
                await t
            except asyncio.CancelledError:
                pass
