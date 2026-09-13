"""Ticket 02 — paridad ReID offboard backend ↔ frontend (MobileFaceNet real).

Guarda que el enroll real no rompa el contrato:
backend `identities.py` (128-d, cap 5, umbral 0.42) == frontend
`face-embedding.js` (128-d, umbral 0.42, gris 0.42-0.55).
"""

from __future__ import annotations

import asyncio
import pathlib
import re
from typing import Any

import pytest

from plataforma.webcam.backend import identities as ident

_FRONT = pathlib.Path(__file__).parent.parent / "frontend" / "src" / "face-embedding.js"


def _front_text() -> str:
    return _FRONT.read_text(encoding="utf-8")


def test_backend_constantes_reid() -> None:
    assert ident.EMBED_DIM == 128
    assert ident.CAP == 5
    assert ident.COSINE_THRESHOLD == pytest.approx(0.42)


def test_frontend_constantes_reid() -> None:
    src = _front_text()
    assert re.search(r"EMBEDDING_DIM\s*=\s*128", src)
    assert re.search(r"COSINE_THRESHOLD\s*=\s*0\.42", src)
    assert re.search(r"COSINE_GRAY\s*=\s*\[\s*0\.42\s*,\s*0\.55\s*\]", src)


def test_enroll_promedia_con_cap_5(tmp_path: pathlib.Path) -> None:
    async def _go() -> dict[str, Any]:
        store = ident.IdentitiesStore(path=tmp_path / "identities.json")
        base = [1.0] + [0.0] * 127
        rec = {"id": "x1", "nombre": "mauri", "embedding": base}
        first = await store.enroll(rec)
        assert first["count"] == 1
        for _ in range(7):
            await store.enroll({"id": "nuevo", "nombre": "mauri", "embedding": base})
        all_recs = await store.get_all()
        mauri = [r for r in all_recs if r.get("nombre") == "mauri"]
        assert mauri and mauri[0]["count"] <= ident.CAP + 1
        return mauri[0]

    rec = asyncio.run(_go())
    assert len(rec["embedding"]) == 128


def test_enroll_rechaza_dim_distinta(tmp_path: pathlib.Path) -> None:
    async def _go() -> None:
        store = ident.IdentitiesStore(path=tmp_path / "identities.json")
        with pytest.raises(ValueError):
            await store.enroll({"id": "bad", "nombre": "x", "embedding": [0.0] * 64})

    asyncio.run(_go())
