"""Ticket 01 — ingest MJPEG XIAO → WS percepcion (QVGA + snapshot VGA).

Throwaway-free: adapter minimo sin tocar ws.py core. Reusa envelope D5
(make/parse) y AsyncLeakyQueue N=1 del handler real.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from plataforma.webcam.backend.drone_mjpeg import (
    LeakyFrame,
    should_snapshot_vga,
    split_mjpeg_frames,
)
from plataforma.webcam.backend.ws import (
    AsyncLeakyQueue,
    make_envelope,
    parse_envelope,
)

_SOI = b"\xff\xd8\xff"
_EOI = b"\xff\xd9"


def _fake_jpeg(tag: bytes) -> bytes:
    return _SOI + tag + _EOI


def test_split_mjpeg_frames_encuentra_dos() -> None:
    stream = _fake_jpeg(b"a") + b"ruido" + _fake_jpeg(b"bb")
    frames = split_mjpeg_frames(stream)
    assert len(frames) == 2
    assert all(f.startswith(_SOI) and f.endswith(_EOI) for f in frames)


def test_split_mjpeg_sin_frames_vacio() -> None:
    assert split_mjpeg_frames(b"sin marcadores") == []


def test_leaky_guarda_solo_ultimo() -> None:
    async def _go() -> tuple[bool, bool, dict[str, Any], int]:
        q: AsyncLeakyQueue[dict[str, Any]] = AsyncLeakyQueue(maxsize=1)
        first = await q.put({"f": 1})
        second = await q.put({"f": 2})
        got = await q.get()
        return first, second, got, q.qsize()

    first, second, got, size = asyncio.run(_go())
    assert first is False
    assert second is True
    assert got == {"f": 2}
    assert size == 0


def test_should_snapshot_solo_person_alta_conf() -> None:
    dets = [
        {"cls": "person", "conf": 0.82, "area": 0.20},
        {"cls": "chair", "conf": 0.95, "area": 0.30},
    ]
    assert should_snapshot_vga(dets) is True
    assert should_snapshot_vga([{"cls": "person", "conf": 0.40, "area": 0.20}]) is False
    assert should_snapshot_vga([]) is False


def test_envelope_frame_roundtrip() -> None:
    env = make_envelope("frame", 7, {"jpeg_b64": "eA=="})
    raw = json.dumps(env)
    back = parse_envelope(raw)
    assert back["type"] == "frame"
    assert back["seq"] == 7
    assert back["payload"] == {"jpeg_b64": "eA=="}


def test_leaky_frame_descarta_previo() -> None:
    leaky: LeakyFrame[bytes] = LeakyFrame()
    assert leaky.push(_fake_jpeg(b"1")) is False
    assert leaky.push(_fake_jpeg(b"2")) is True
    assert leaky.pop() == _fake_jpeg(b"2")
    assert leaky.pop() is None


def test_qvga_no_acumula_lag() -> None:
    """10 puts seguidos en N=1 dejan 1 frame: sin lag acumulado."""

    async def _go() -> tuple[int, int]:
        q: AsyncLeakyQueue[int] = AsyncLeakyQueue(maxsize=1)
        for i in range(10):
            await q.put(i)
        size = q.qsize()
        last = await q.get()
        return size, last

    size, last = asyncio.run(_go())
    assert size == 1
    assert last == 9
