"""VLM 1Hz — scene_caption via Groq → HF → Gemini fallback.

Cadena especificada v2 (D3 #77 / R3 #74):
 Groq llama-4-scout → HF Qwen2.5-VL → Gemini 2.0 Flash → mock
Intra-op num threads no aplica (HTTP); timeout ~300ms p50.
Sincrónico para asyncio.to_thread si se requiere.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LeyendaEscena:
    """Leyenda de escena — payload scene_caption."""

    frame_id: int
    caption: str
    objects: tuple[str, ...]
    conf: float
    ts: int
    provider: str


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mock_caption(frame_id: int, objects: list[str] | None = None) -> LeyendaEscena:
    objs = tuple(objects or [])
    caption = "Escena con " + ", ".join(objs) if objs else "Escena vacia"
    return LeyendaEscena(
        frame_id=frame_id,
        caption=caption,
        objects=objs,
        conf=0.5,
        ts=_now_ms(),
        provider="mock",
    )


class VLMClient:
    """Cliente VLM con cadena de fallback."""

    def __init__(self) -> None:
        self.enabled: bool = True

    def caption(
        self,
        image_b64: str | None = None,
        frame_id: int = 0,
        objects: list[str] | None = None,
    ) -> LeyendaEscena:
        """Genera LeyendaEscena via cadena Groq→HF→Gemini→mock.

        image_b64 opcional — si None, ignora y usa mock con objects.
        No falla: siempre retorna LeyendaEscena (mock si providers fallan).
        """
        _ = image_b64
        ts = _now_ms()
        objs = objects or []

        # 1) Groq llama-4-scout (OpenAI compatible)
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if groq_key:
            try:
                # Intento lazy import sin romper headless si no hay openai
                from openai import OpenAI  # type: ignore

                base_url = (
                    os.getenv("GROQ_BASE_URL", "").strip()
                    or "https://api.groq.com/openai/v1"
                )
                client = OpenAI(api_key=groq_key, base_url=base_url)
                model = (
                    os.getenv("GROQ_VLM_MODEL", "").strip()
                    or "meta-llama/llama-4-scout-17b-16e-instruct"
                )
                # Texto solo — imagen opcional no incluida en headless
                objs_str = ", ".join(objs) or "ninguno"
                prompt = f"Describe en espanol AR escena con: {objs_str}"
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=64,
                )
                txt = (resp.choices[0].message.content or "").strip()
                if txt:
                    return LeyendaEscena(
                        frame_id=frame_id,
                        caption=txt,
                        objects=tuple(objs),
                        conf=0.85,
                        ts=ts,
                        provider="groq",
                    )
            except Exception:
                pass

        # 2) HF Qwen2.5-VL
        hf_token = os.getenv("HF_TOKEN", "").strip()
        if hf_token:
            try:
                from openai import OpenAI  # type: ignore

                hf_base = (
                    os.getenv("HF_BASE_URL", "").strip()
                    or "https://router.huggingface.co/v1"
                )
                client = OpenAI(api_key=hf_token, base_url=hf_base)
                model = (
                    os.getenv("HF_VLM_MODEL", "").strip()
                    or "Qwen/Qwen2.5-VL-7B-Instruct"
                )
                objs_str = ", ".join(objs) or "ninguno"
                prompt = f"Describe en espanol AR escena con: {objs_str}"
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=64,
                )
                txt = (resp.choices[0].message.content or "").strip()
                if txt:
                    return LeyendaEscena(
                        frame_id=frame_id,
                        caption=txt,
                        objects=tuple(objs),
                        conf=0.75,
                        ts=ts,
                        provider="hf",
                    )
            except Exception:
                pass

        # 3) Gemini fallback (via fase-1 gemini_client si disponible)
        google_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if google_key:
            try:
                import pathlib
                import sys

                fase1_path = pathlib.Path(__file__).resolve().parents[4] / "fase-1"
                if str(fase1_path) not in sys.path:
                    sys.path.insert(0, str(fase1_path))
                import gemini_client  # type: ignore

                objs_str = ", ".join(objs) or "ninguno"
                prompt = f"Describe en espanol AR escena con: {objs_str}"
                modelo = (
                    os.getenv("GEMINI_MODEL", "").strip()
                    or gemini_client.MODELO_GEMINI_LEGACY
                )
                txt = gemini_client.responder(prompt, modelo=modelo)
                txt = (txt or "").strip()
                if txt:
                    return LeyendaEscena(
                        frame_id=frame_id,
                        caption=txt,
                        objects=tuple(objs),
                        conf=0.70,
                        ts=ts,
                        provider="gemini",
                    )
            except Exception:
                pass

        # 4) mock final
        mock = _mock_caption(frame_id, objs)
        # mock ya tiene ts nuevo; ajustar provider mock
        return LeyendaEscena(
            frame_id=mock.frame_id,
            caption=mock.caption,
            objects=mock.objects,
            conf=mock.conf,
            ts=ts,
            provider="mock",
        )


def get_vlm_client() -> VLMClient:
    """Factory — siempre retorna cliente (mock si sin keys)."""
    return VLMClient()
