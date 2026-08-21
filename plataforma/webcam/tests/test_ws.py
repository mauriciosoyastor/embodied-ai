"""Tests S2-B — WebSocket envelope + leaky queue + gesto stub (headless).

Sin cámara ni MediaPipe real — FakeWebSocket + frames JPEG sintéticos.
Criterio: pytest plataforma/webcam/backend -k ws verde headless.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import pytest  # noqa: F401

from plataforma.webcam.backend.inference.gesture import GestoReconocido
from plataforma.webcam.backend.ws import (
    AsyncLeakyQueue,
    LeakyQueue,
    make_envelope,
    parse_envelope,
    process_single_frame,
    run_inference,
)

# 1x1 JPEG blanco base64 — válido para decode_jpeg_b64 (cv2 opcional)
DUMMY_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHB"
    "wgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyM"
    "jIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAEAAQADAS"
    "IAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/"
    "8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIR"
    "AxEAPwCwAA8A/9k="
)


class FakeWebSocket:
    """Fake headless compatible con WebSocketLike."""

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

    def queue_raw(self, raw: str) -> None:
        self._recv.put_nowait(raw)

    def queue_envelope(
        self, type_: str, seq: int, payload: dict[str, Any], ts: int = 1700000000000
    ) -> None:
        self._recv.put_nowait(
            json.dumps({"type": type_, "seq": seq, "ts": ts, "payload": payload})
        )

    def sent_envelopes(self) -> list[dict[str, Any]]:
        return [json.loads(s) for s in self.sent]


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


def test_envelope_roundtrip() -> None:
    env = make_envelope("frame", seq=1, payload={"frame_id": 42, "jpeg_b64": "abc"})
    raw = json.dumps(env)
    parsed = parse_envelope(raw)
    assert parsed["type"] == "frame"
    assert parsed["seq"] == 1
    assert isinstance(parsed["ts"], int)
    assert parsed["payload"]["frame_id"] == 42


def test_envelope_requires_fields() -> None:
    with pytest.raises(ValueError, match="Envelope incompleto"):
        parse_envelope(json.dumps({"type": "frame", "seq": 1}))
    with pytest.raises(ValueError, match="type desconocido"):
        parse_envelope(json.dumps({"type": "bogus", "seq": 1, "ts": 1, "payload": {}}))


def test_make_envelope_ts_is_ms_int() -> None:
    env = make_envelope("gesto", seq=5, payload={"label": "none"}, ts=1234567890123)
    assert env["ts"] == 1234567890123
    assert env["type"] == "gesto"
    # auto ts
    env2 = make_envelope("estado", seq=6, payload={})
    assert isinstance(env2["ts"], int)
    assert env2["ts"] > 1_000_000_000_000


# ---------------------------------------------------------------------------
# Serialización D5
# ---------------------------------------------------------------------------


def test_run_inference_boxes_normalizadas_y_gesto_allowed() -> None:
    boxes, gesto = run_inference(DUMMY_JPEG_B64, frame_id=7, ts=1700000000000)
    assert isinstance(boxes, list)
    for b in boxes:
        assert 0.0 <= b["x"] <= 1.0
        assert 0.0 <= b["y"] <= 1.0
        assert 0.0 <= b["w"] <= 1.0
        assert 0.0 <= b["h"] <= 1.0
        assert isinstance(b["cls"], str)
        assert 0.0 <= b["conf"] <= 1.0
    assert gesto["frame_id"] == 7
    assert gesto["label"] in ("open_palm", "fist", "thumbs_up", "none")
    assert 0.0 <= gesto["conf"] <= 1.0
    # GestoReconocido dominio desacoplado
    evento = GestoReconocido(
        label=gesto["label"],
        conf=gesto["conf"],
        frame_id=gesto["frame_id"],
        ts=1700000000000,
    )
    assert evento.label in ("open_palm", "fist", "thumbs_up", "none")


def test_process_single_frame_envia_detecciones_y_gesto_con_seq() -> None:
    async def _inner() -> None:
        fake = FakeWebSocket()
        await fake.accept()
        seq = [0]
        payload = {
            "frame_id": 10,
            "jpeg_b64": DUMMY_JPEG_B64,
            "width": 640,
            "height": 480,
        }
        await process_single_frame(fake, payload, seq)
        assert len(fake.sent) == 2
        envs = fake.sent_envelopes()
        # primer mensaje detecciones
        assert envs[0]["type"] == "detecciones"
        assert envs[0]["seq"] == 1
        assert envs[0]["payload"]["frame_id"] == 10
        assert isinstance(envs[0]["payload"]["boxes"], list)
        # segundo mensaje gesto
        assert envs[1]["type"] == "gesto"
        assert envs[1]["seq"] == 2
        assert envs[1]["payload"]["frame_id"] == 10
        assert envs[1]["payload"]["label"] in ("open_palm", "fist", "thumbs_up", "none")
        # seq incremental across llamadas
        payload2 = {"frame_id": 11, "jpeg_b64": DUMMY_JPEG_B64}
        await process_single_frame(fake, payload2, seq)
        envs2 = fake.sent_envelopes()
        assert envs2[2]["seq"] == 3
        assert envs2[3]["seq"] == 4
        assert envs2[2]["payload"]["frame_id"] == 11
        assert envs2[3]["payload"]["frame_id"] == 11
        # ts es int ms
        for e in envs2:
            assert isinstance(e["ts"], int)

    asyncio.run(_inner())


def test_process_single_frame_correlacion_frame_id() -> None:
    async def _inner() -> None:
        fake = FakeWebSocket()
        seq = [10]
        for fid in [1, 99, 12345]:
            payload = {"frame_id": fid, "jpeg_b64": DUMMY_JPEG_B64}
            before = len(fake.sent)
            await process_single_frame(fake, payload, seq)
            envs = fake.sent_envelopes()[before:]
            assert envs[0]["payload"]["frame_id"] == fid
            assert envs[1]["payload"]["frame_id"] == fid

    asyncio.run(_inner())


# ---------------------------------------------------------------------------
# Leaky queue N=1
# ---------------------------------------------------------------------------


def test_leaky_queue_sync_descarta_anterior() -> None:
    q: LeakyQueue[int] = LeakyQueue(maxsize=1)
    assert q.put(1) is False  # primera no descarta
    assert len(q) == 1
    assert q.peek() == 1
    # segunda — descarta 1, queda 2 (leaky)
    assert q.put(2) is True
    assert len(q) == 1
    assert q.peek() == 2
    assert q.get() == 2
    assert q.is_empty()
    assert q.get() is None


def test_leaky_queue_sync_n1_no_acumula() -> None:
    q: LeakyQueue[dict[str, Any]] = LeakyQueue(maxsize=1)
    q.put({"frame_id": 1})
    q.put({"frame_id": 2})
    q.put({"frame_id": 3})
    assert len(q) == 1
    assert q.get() == {"frame_id": 3}


def test_async_leaky_queue_descarta_si_nuevo_antes_de_consumir() -> None:
    async def _inner() -> None:
        q: AsyncLeakyQueue[int] = AsyncLeakyQueue(maxsize=1)
        # simular dos frames rápidos antes de que processor consuma
        await q.put(1)
        discarded = await q.put(2)
        assert discarded is True
        assert q.qsize() == 1
        val = await q.get()
        assert val == 2  # solo el último sobrevive

    asyncio.run(_inner())


def test_leaky_queue_integration_con_delay() -> None:
    """Simula inference lento: dos frames en cola leaky → solo último se procesa."""

    async def _inner() -> None:
        fake = FakeWebSocket()
        seq = [0]

        # monkeypatch run_inference con delay para simular backpressure
        import plataforma.webcam.backend.ws as ws_mod

        orig = ws_mod.run_inference

        def slow_run(
            jpeg_b64: str,
            frame_id: int,
            ts: int,
            width: int | None = None,
            height: int | None = None,
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            import time as _time

            _time.sleep(0.02)
            return [], {"frame_id": frame_id, "label": "none", "conf": 0.0}

        ws_mod.run_inference = slow_run
        try:
            queue: LeakyQueue[dict[str, Any]] = LeakyQueue(maxsize=1)
            # llegan 3 frames antes de procesar
            queue.put({"frame_id": 1, "jpeg_b64": DUMMY_JPEG_B64})
            queue.put({"frame_id": 2, "jpeg_b64": DUMMY_JPEG_B64})
            queue.put({"frame_id": 3, "jpeg_b64": DUMMY_JPEG_B64})
            assert len(queue) == 1
            latest = queue.get()
            assert latest is not None and latest["frame_id"] == 3
            await process_single_frame(fake, latest, seq)
            envs = fake.sent_envelopes()
            # solo frame 3 fue procesado
            assert envs[0]["payload"]["frame_id"] == 3
            assert envs[1]["payload"]["frame_id"] == 3
        finally:
            ws_mod.run_inference = orig

    asyncio.run(_inner())


# ---------------------------------------------------------------------------
# Gesto como GestoReconocido (desacople FSM)
# ---------------------------------------------------------------------------


def test_gesto_payloadmapea_a_GestoReconocido() -> None:
    _, gesto = run_inference(
        DUMMY_JPEG_B64, frame_id=5, ts=1700000000000, width=640, height=640
    )
    evento = GestoReconocido(
        label=gesto["label"],
        conf=gesto["conf"],
        frame_id=gesto["frame_id"],
        ts=1700000000000,
    )
    assert evento.frame_id == 5
    assert evento.label in ("open_palm", "fist", "thumbs_up", "none")
    assert 0.0 <= evento.conf <= 1.0


def test_app_health_y_ws_importable() -> None:
    from plataforma.webcam.backend.app import app  # noqa: F401

    # ruta health existe
    routes = [getattr(r, "path", "") for r in app.routes]
    assert "/health" in routes
    # ws route existe bajo /ws/percepcion
    ws_routes = [getattr(r, "path", "") for r in app.routes]
    assert any("ws/percepcion" in p for p in ws_routes)


def test_base64_jpeg_sintetico_valido() -> None:
    # el dummy debe ser base64 válido y decodificable
    raw = base64.b64decode(DUMMY_JPEG_B64)
    assert len(raw) > 0
    assert raw[:2] == b"\xff\xd8"  # SOI JPEG
