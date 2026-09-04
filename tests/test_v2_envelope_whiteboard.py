"""Tests v2 envelope único + Whiteboard PercepcionVista + 2 LeakyQueues + VLM 1Hz.

Headless con np.zeros y FakeWebSocket — valida whitelist, seq monotónico,
TTL, ABORTED overlay-only, parse scene_caption.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import numpy as np
import pytest

from plataforma.sim.whiteboard import LeyendaVista, PercepcionVista, WhiteboardState
from plataforma.webcam.backend.config import (
    VLM_INTERVAL,
    YOLO_AREA_MIN,
    YOLO_CONF,
    YOLO_PERSON_AREA_MIN,
    YOLO_PERSON_CONF,
    YOLO_WHITELIST,
)
from plataforma.webcam.backend.ws import (
    AsyncLeakyQueue,
    LeakyQueue,
    make_envelope,
    parse_envelope,
    process_single_frame,
    run_inference,
)

DUMMY_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHB"
    "wgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyM"
    "jIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAEAAQADAS"
    "IAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/"
    "8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIR"
    "AxEAPwCwAA8A/9k="
)


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted: bool = False
        self.sent: list[str] = []
        self._recv: asyncio.Queue[str] = asyncio.Queue()

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, data: str) -> None:
        self.sent.append(data)

    async def receive_text(self) -> str:
        return await self._recv.get()

    def queue_envelope(
        self, type_: str, seq: int, payload: dict[str, Any], ts: int = 1700000000000
    ) -> None:
        self._recv.put_nowait(
            json.dumps({"type": type_, "seq": seq, "ts": ts, "payload": payload})
        )

    def sent_envelopes(self) -> list[dict[str, Any]]:
        return [json.loads(s) for s in self.sent]


# ---------------------------------------------------------------------------
# Whitelist + conf/area
# ---------------------------------------------------------------------------


def test_yolo_whitelist_w30() -> None:
    # W30 curada (S1 mapa #88) — 13 base + 17 indoor, mismo yolo11n.onnx sin coste.
    # Sincronizado con plataforma/webcam/tests/test_v2_envelope_whiteboard.py
    # y config.YOLO_WHITELIST (fuente de verdad); el viejo 13 quedó obsoleto.
    assert len(YOLO_WHITELIST) == 30
    assert "person" in YOLO_WHITELIST
    assert YOLO_WHITELIST == frozenset(
        {
            "person",
            "chair",
            "couch",
            "bottle",
            "cup",
            "cell phone",
            "laptop",
            "keyboard",
            "mouse",
            "book",
            "backpack",
            "handbag",
            "remote",
            "tv",
            "bed",
            "dining table",
            "toilet",
            "potted plant",
            "microwave",
            "oven",
            "sink",
            "refrigerator",
            "clock",
            "vase",
            "toaster",
            "wine glass",
            "bowl",
            "scissors",
            "teddy bear",
            "toothbrush",
        }
    )


def test_yolo_conf_area_umbrales() -> None:
    assert YOLO_CONF == 0.5
    assert YOLO_AREA_MIN == 0.03
    assert YOLO_PERSON_CONF == 0.60
    assert YOLO_PERSON_AREA_MIN == 0.15
    assert VLM_INTERVAL == 30


def test_run_inference_filtra_whitelist_y_area() -> None:
    """Mock YOLO devuelve mezcla person/chair/banana con distintas areas."""
    import plataforma.webcam.backend.ws as ws_mod
    from plataforma.webcam.backend.inference.yolo import Box

    orig_get = ws_mod.get_yolo_detector  # type: ignore[attr-defined]

    class FakeYolo:
        def predict(self, _img: Any | None) -> list[Box]:
            return [
                Box(
                    x=0.1, y=0.1, w=0.4, h=0.4, cls="person", conf=0.70
                ),  # area 0.16 pass
                Box(
                    x=0.1, y=0.1, w=0.2, h=0.2, cls="person", conf=0.55
                ),  # conf <0.60 fail
                Box(
                    x=0.1, y=0.1, w=0.1, h=0.1, cls="person", conf=0.70
                ),  # area 0.01 <0.15 fail
                Box(
                    x=0.1, y=0.1, w=0.2, h=0.2, cls="chair", conf=0.60
                ),  # area 0.04 pass
                Box(
                    x=0.1, y=0.1, w=0.05, h=0.05, cls="chair", conf=0.60
                ),  # area 0.0025 fail
                Box(
                    x=0.1, y=0.1, w=0.4, h=0.4, cls="banana", conf=0.99
                ),  # fuera whitelist
            ]

    ws_mod.get_yolo_detector = lambda models_dir=None: FakeYolo()  # type: ignore[attr-defined,assignment,return-value]
    try:
        boxes, _ = run_inference(DUMMY_JPEG_B64, frame_id=1, ts=1700000000000)
        clss = [b["cls"] for b in boxes]
        assert "person" in clss
        assert "chair" in clss
        assert "banana" not in clss
        # solo 2 deben pasar (person 0.70/0.16 y chair 0.60/0.04)
        assert len(boxes) == 2
        for b in boxes:
            assert b["cls"] in YOLO_WHITELIST
            if b["cls"] == "person":
                assert b["conf"] >= YOLO_PERSON_CONF
                assert b["w"] * b["h"] >= YOLO_PERSON_AREA_MIN
            else:
                assert b["conf"] >= YOLO_CONF
                assert b["w"] * b["h"] >= YOLO_AREA_MIN
    finally:
        ws_mod.get_yolo_detector = orig_get  # type: ignore[attr-defined,assignment]


def test_run_inference_con_np_zeros_frame() -> None:
    """Valida headless con frame np.zeros sin modelo (stub)."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _ = img  # ensure np import used
    boxes, gesto = run_inference(DUMMY_JPEG_B64, frame_id=42, ts=1700000000000)
    assert isinstance(boxes, list)
    assert gesto["frame_id"] == 42
    assert gesto["label"] in ("open_palm", "fist", "thumbs_up", "none")


# ---------------------------------------------------------------------------
# Envelope scene_caption
# ---------------------------------------------------------------------------


def test_parse_envelope_scene_caption() -> None:
    env = make_envelope(
        "scene_caption",
        seq=99,
        payload={
            "frame_id": 1,
            "caption": "hola",
            "objects": [],
            "conf": 0.9,
            "ts": 1,
            "provider": "mock",
        },
    )
    raw = json.dumps(env)
    parsed = parse_envelope(raw)
    assert parsed["type"] == "scene_caption"
    assert parsed["seq"] == 99
    assert parsed["payload"]["caption"] == "hola"


def test_parse_envelope_rechaza_desconocido() -> None:
    with pytest.raises(ValueError, match="type desconocido"):
        parse_envelope(json.dumps({"type": "foo", "seq": 1, "ts": 1, "payload": {}}))


def test_scene_caption_payload_estructura() -> None:
    env = make_envelope(
        "scene_caption",
        seq=1,
        payload={
            "frame_id": 10,
            "caption": "Una silla y una mesa",
            "objects": ["chair", "couch"],
            "conf": 0.85,
            "ts": 1700000000000,
            "provider": "groq",
        },
    )
    assert env["payload"]["frame_id"] == 10
    assert isinstance(env["payload"]["caption"], str)
    assert isinstance(env["payload"]["objects"], list)
    assert 0.0 <= env["payload"]["conf"] <= 1.0
    assert env["payload"]["provider"] in ("groq", "hf", "gemini", "mock")


def test_vlm_client_mock_siempre_retorna() -> None:
    from plataforma.webcam.backend.inference.vlm import get_vlm_client

    client = get_vlm_client()
    ley = client.caption(frame_id=7, objects=["chair", "book"])
    assert ley.frame_id == 7
    assert isinstance(ley.caption, str)
    assert ley.provider in ("groq", "hf", "gemini", "mock")
    assert 0.0 <= ley.conf <= 1.0
    assert isinstance(ley.objects, tuple)


# ---------------------------------------------------------------------------
# Seq monotónico con 2 queues + VLM tick
# ---------------------------------------------------------------------------


def test_seq_monotonico_fast_slow_vlm() -> None:
    async def _inner() -> None:
        fake = FakeWebSocket()
        seq = [0]
        # simular 3 frames fast
        for fid in [1, 2, 3]:
            payload = {"frame_id": fid, "jpeg_b64": DUMMY_JPEG_B64}
            await process_single_frame(fake, payload, seq)
        envs = fake.sent_envelopes()
        seqs = [e["seq"] for e in envs]
        assert seqs == sorted(seqs)
        # cada frame genera 2 envelopes (detecciones+gesto) → seq +2 por frame
        assert seqs == [1, 2, 3, 4, 5, 6]
        # simular VLM tick manual
        from plataforma.webcam.backend.ws import _send_scene_caption

        # capturar seq antes
        before = seq[0]
        lock = asyncio.Lock()
        await _send_scene_caption(
            fake, frame_id=3, seq_counter=seq, seq_lock=lock, objects=["chair"]
        )
        envs2 = fake.sent_envelopes()
        assert envs2[-1]["type"] == "scene_caption"
        assert envs2[-1]["seq"] == before + 1
        assert envs2[-1]["seq"] > seqs[-1]

    asyncio.run(_inner())


def test_leaky_queue_dual_fast_slow() -> None:
    async def _inner() -> None:
        fast: AsyncLeakyQueue[dict[str, Any]] = AsyncLeakyQueue(maxsize=1)
        slow: AsyncLeakyQueue[dict[str, Any]] = AsyncLeakyQueue(maxsize=1)
        # push 3 frames rápidos
        await fast.put({"frame_id": 1})
        await fast.put({"frame_id": 2})
        assert fast.qsize() == 1
        val = await fast.get()
        assert val["frame_id"] == 2
        # slow mantiene N=1 independiente
        await slow.put({"frame_id": 10})
        await slow.put({"frame_id": 11})
        assert slow.qsize() == 1
        val2 = await slow.get()
        assert val2["frame_id"] == 11

        # sync variant también
        q: LeakyQueue[int] = LeakyQueue(maxsize=1)
        assert q.put(1) is False
        assert q.put(2) is True
        assert q.get() == 2

    asyncio.run(_inner())


# ---------------------------------------------------------------------------
# Whiteboard PercepcionVista TTL + ABORTED overlay-only
# ---------------------------------------------------------------------------


def test_percepcion_vista_ttl() -> None:
    pv = PercepcionVista(
        frame_id=1,
        detecciones=[{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "cls": 0.0, "conf": 0.9}],  # type: ignore[arg-type]
        ts_detecciones=time.time(),
        posturas=[{"x": 0.5, "y": 0.5}],  # type: ignore[arg-type]
        ts_posturas=time.time(),
        profundidades=[{"z_rel": 0.5}],  # type: ignore[arg-type]
        ts_profundidades=time.time(),
        leyenda=LeyendaVista(
            caption="test",
            objects=[],
            conf=0.9,
            ts=time.time(),
            provider="mock",
            frame_id=1,
        ),
        ts_leyenda=time.time(),
    )
    # fresh ahora
    assert pv.is_detecciones_fresh() is True
    assert pv.is_posturas_fresh() is True
    assert pv.is_profundidades_fresh() is True
    assert pv.is_leyenda_fresh() is True
    # simular expiración detecciones 0.1s
    future = time.time() + 0.5
    assert pv.is_detecciones_fresh(now=future) is False
    # posturas TTL 1.0s
    assert pv.is_posturas_fresh(now=future) is True
    assert pv.is_posturas_fresh(now=time.time() + 1.5) is False
    # profundidades TTL 1.0s
    assert pv.is_profundidades_fresh(now=time.time() + 1.5) is False
    # leyenda TTL 2.0s
    assert pv.is_leyenda_fresh(now=time.time() + 1.5) is True
    assert pv.is_leyenda_fresh(now=time.time() + 2.5) is False


def test_whiteboard_aborted_overlay_only_no_muta() -> None:
    wb = WhiteboardState(estado="SIM_RUNNING", frame_id=1)
    ok = wb.update_percepcion(frame_id=10, detecciones=[{"x": 0.1}])  # type: ignore[arg-type]
    assert ok is True
    assert wb.percepcion_vista is not None
    assert wb.percepcion_vista.frame_id == 10
    # pasar a ABORTED
    wb.estado = "SIM_ABORTED"
    ok2 = wb.update_percepcion(frame_id=99, detecciones=[{"x": 0.9}])  # type: ignore[arg-type]
    assert ok2 is False
    # no mutó
    assert wb.percepcion_vista is not None
    assert wb.percepcion_vista.frame_id == 10
    assert wb.percepcion_vista.detecciones == [{"x": 0.1}]  # type: ignore[comparison-overlap]


def test_whiteboard_percepcion_vista_fields() -> None:
    wb = WhiteboardState()
    wb.update_percepcion(
        frame_id=5,
        detecciones=[{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}],  # type: ignore[arg-type]
        posturas=[{"keypoints": []}],  # type: ignore[arg-type]
        profundidades=[{"z_rel": 0.3}],  # type: ignore[arg-type]
        leyenda=LeyendaVista(
            caption="una silla",
            objects=["chair"],
            conf=0.8,
            ts=time.time(),
            provider="mock",
            frame_id=5,
        ),
    )
    pv = wb.percepcion_vista
    assert pv is not None
    assert pv.frame_id == 5
    assert len(pv.detecciones) == 1
    assert len(pv.posturas) == 1
    assert len(pv.profundidades) == 1
    assert pv.leyenda is not None
    assert pv.leyenda.caption == "una silla"


def test_perception_ws_handler_existe_y_importable() -> None:
    from plataforma.webcam.backend.ws import perception_ws_handler

    assert callable(perception_ws_handler)


def test_whiteboard_importable_backend() -> None:
    from plataforma.webcam.backend.whiteboard import PercepcionVista as PV2

    assert PV2 is not None


def test_app_vision_caption_route_existe() -> None:
    from plataforma.webcam.backend.app import app

    routes = [getattr(r, "path", "") for r in app.routes]
    assert "/vision/caption" in routes
    assert "/health" in routes
