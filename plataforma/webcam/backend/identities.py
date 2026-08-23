"""IdentitiesStore — hibrido localStorage + identities.json (Ticket 025).

Schema: {id: nanoid, nombre, embedding: float[128], count, updatedAt: ISO}
Promedio: hat_e = normalize(e_old * min(N,5) + e_new) con cap 5
Lock: asyncio.Lock + tmp->replace atomico (win32 safe, sin fcntl)
"""

from __future__ import annotations

import asyncio
import datetime
import json
import math
import pathlib
import tempfile
from typing import Any

IDENTITIES_PATH = pathlib.Path(__file__).parent / "models" / "identities.json"
EMBED_DIM = 128
CAP = 5
COSINE_THRESHOLD = 0.42


def l2_normalize(vec: list[float]) -> list[float]:
    s = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / s for x in vec]


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class IdentitiesStore:
    """Store thread-safe para WS handlers y app lifespan."""

    def __init__(self, path: pathlib.Path | None = None) -> None:
        self.path = path or IDENTITIES_PATH
        self._lock = asyncio.Lock()
        self._data: list[dict[str, Any]] = []
        self._loaded = False

    async def load(self) -> list[dict[str, Any]]:
        async with self._lock:
            return await self._load_locked()

    async def _load_locked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            self._data = []
            self._loaded = True
            return self._data
        try:
            raw = self.path.read_text(encoding="utf-8")
            arr = json.loads(raw)
            if isinstance(arr, list):
                # validar 128-d
                self._data = [x for x in arr if isinstance(x, dict) and x.get("id")]
            else:
                self._data = []
        except Exception:
            self._data = []
        self._loaded = True
        return list(self._data)

    async def get_all(self) -> list[dict[str, Any]]:
        async with self._lock:
            if not self._loaded:
                await self._load_locked()
            return list(self._data)

    async def enroll(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Inserta o promedia por id. rec debe tener id,nombre,embedding[128]."""
        # validar embedding
        emb = rec.get("embedding")
        if not isinstance(emb, list) or len(emb) != EMBED_DIM:
            raise ValueError(f"embedding debe ser lista {EMBED_DIM}")
        # l2 normalize entrante
        emb_norm = l2_normalize([float(x) for x in emb])
        rid = str(rec.get("id") or "")
        nombre = str(rec.get("nombre") or "").strip()
        if not rid or not nombre:
            raise ValueError("id y nombre requeridos")
        async with self._lock:
            if not self._loaded:
                await self._load_locked()
            # buscar existente por id
            idx = next((i for i, x in enumerate(self._data) if x.get("id") == rid), -1)
            if idx >= 0:
                # idempotencia: ya existe, retornar sin duplicar
                return self._data[idx]
            # Si mismo nombre existe, promediar con cap 5
            same_idx = next(
                (i for i, x in enumerate(self._data) if x.get("nombre") == nombre), -1
            )
            if same_idx >= 0:
                old = self._data[same_idx]
                old_emb = old.get("embedding", [])
                old_cnt = int(old.get("count", 1))
                cap_cnt = min(old_cnt, CAP)
                # hat_e = normalize(e_old*min(N,5)+e_new)
                avg = [(old_emb[i] * cap_cnt + emb_norm[i]) for i in range(EMBED_DIM)]
                avg_norm = l2_normalize(avg)
                old["embedding"] = avg_norm
                old["count"] = min(old_cnt + 1, CAP + 1)  # cap 6 max (5+1)
                old["updatedAt"] = _now_iso()
                await self._save_locked()
                return old
            # nueva
            new_rec = {
                "id": rid,
                "nombre": nombre,
                "embedding": emb_norm,
                "count": 1,
                "updatedAt": _now_iso(),
                "source": rec.get("source", "ws"),
            }
            self._data.append(new_rec)
            await self._save_locked()
            return new_rec

    async def purge(self, all_: bool = True, ids: list[str] | None = None) -> int:
        async with self._lock:
            if not self._loaded:
                await self._load_locked()
            if all_:
                n = len(self._data)
                self._data = []
            else:
                ids_set = set(ids or [])
                before = len(self._data)
                self._data = [x for x in self._data if x.get("id") not in ids_set]
                n = before - len(self._data)
            await self._save_locked()
            return n

    async def _save_locked(self) -> None:
        # write atomico tmp->replace
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(self._data, ensure_ascii=False, indent=2)
        # tempfile en mismo dir para atomicidad
        tmp_path: pathlib.Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=str(self.path.parent),
                suffix=".tmp",
            ) as f:
                f.write(data)
                tmp_path = pathlib.Path(f.name)
            tmp_path.replace(self.path)
        finally:
            if tmp_path and tmp_path.exists() and tmp_path != self.path:
                try:
                    tmp_path.unlink()
                except Exception:
                    pass


# Singleton global para app y ws
store = IdentitiesStore()
