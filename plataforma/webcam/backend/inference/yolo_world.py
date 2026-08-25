"""YOLO-World s wrapper stub S3 — open-vocab PromptList.

Headless sin modelo (is_stub True) hasta que `models/yolo-world-s.onnx` exista.
API compatible con YoloDetector: predict + set_classes + save stub.
S3: lazy bajo flag YOLO_WORLD_ENABLED, slow_queue 2Hz, PromptList 20+8.
"""

from __future__ import annotations

import pathlib
from typing import Any

from plataforma.webcam.backend.config import YOLO_WORLD_PROMPTLIST_STATIC


class YoloWorldDetector:
    """Detector YOLO-World s stub — S3.

    Sin modelo: is_stub True, predict → [].
    Con modelo: usaría onnxruntime con txt_feats dinámico (stub).
    048: cache _txt_feats_static 20x512 offline + warmup(10) piggyback slow 2Hz.
    """

    def __init__(
        self,
        model_path: pathlib.Path | None = None,
        prompt_list: list[str] | None = None,
    ) -> None:
        self.model_path = model_path
        self.prompt_list: list[str] = list(prompt_list or YOLO_WORLD_PROMPTLIST_STATIC)
        self.is_stub: bool = True
        self._session: Any | None = None
        self._txt_feats_static: Any | None = None
        if model_path is not None and model_path.exists():
            try:
                import onnxruntime as ort  # type: ignore

                opts = ort.SessionOptions()
                opts.graph_optimization_level = (
                    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                )
                opts.intra_op_num_threads = 2
                opts.inter_op_num_threads = 1
                try:
                    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL  # type: ignore
                except Exception:
                    pass
                self._session = ort.InferenceSession(
                    str(model_path),
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                self.is_stub = False
                # 048 cache offline txt_feats 1x20x512 (stub zeros; real CLIP ViT-B/32 512-d)  # noqa: E501
                try:
                    import numpy as np  # type: ignore

                    self._txt_feats_static = np.zeros(
                        (1, len(self.prompt_list), 512), dtype=np.float32
                    )
                except Exception:
                    self._txt_feats_static = None
            except Exception:
                self._session = None
                self._txt_feats_static = None
                self.is_stub = True

    def set_classes(self, prompts: list[str]) -> None:
        """Actualiza PromptList — debounce y max 8 lo maneja ws.py S3."""
        # filtrar vacíos, limitar 8, normalizar
        cleaned = [str(p).strip() for p in prompts if str(p).strip()]
        if len(cleaned) > 8:
            cleaned = cleaned[:8]
        if cleaned:
            self.prompt_list = cleaned
            # invalidar cache txt_feats si dinámica (max 8) 048 1xNx512
            try:
                import numpy as np  # type: ignore

                self._txt_feats_static = np.zeros(
                    (1, len(self.prompt_list), 512), dtype=np.float32
                )
            except Exception:
                self._txt_feats_static = None

    def warmup(self, n: int = 10) -> None:
        """Precalienta ORT graph + cache txt_feats — amortiza cold-start igual que YoloDetector."""  # noqa: E501
        if self._session is None or self.is_stub:
            return
        try:
            import numpy as np  # type: ignore

            sess: Any = self._session
            input_name: str = sess.get_inputs()[0].name  # type: ignore
            dummy_img = np.random.randn(1, 3, 640, 640).astype(np.float32)
            # dummy txt_feats 1x8x512 si modelo espera segundo input dinámico  # noqa: E501
            dummy_txt = np.zeros(
                (1, min(8, len(self.prompt_list)), 512), dtype=np.float32
            )
            for _ in range(max(0, n)):
                try:
                    inputs = {input_name: dummy_img}
                    # si modelo tiene 2 inputs, añadir txt_feats
                    if len(sess.get_inputs()) > 1:  # type: ignore
                        txt_name: str = sess.get_inputs()[1].name  # type: ignore
                        inputs[txt_name] = dummy_txt
                    sess.run(None, inputs)  # type: ignore
                except Exception:
                    # fallback solo imagen
                    sess.run(None, {input_name: dummy_img})  # type: ignore
        except Exception:
            return

    def predict(
        self, image: Any | None = None, conf_thr: float | None = None
    ) -> list[Any]:
        """Stub S3: sin modelo → [] ; con modelo real delegaría a ORT (no implementado)."""  # noqa: E501
        _ = image, conf_thr
        return []

    def save(self, path: pathlib.Path) -> None:
        """Re-parametrizado stub — no-op S3."""
        _ = path


_world_singleton: YoloWorldDetector | None = None


def get_yolo_world_detector(
    models_dir: pathlib.Path | None = None,
    prompt_list: list[str] | None = None,
) -> YoloWorldDetector:
    global _world_singleton
    if _world_singleton is None:
        if models_dir is None:
            models_dir = pathlib.Path(__file__).parent.parent / "models"
        candidate = models_dir / "yolo-world-s.onnx"
        pl = prompt_list or YOLO_WORLD_PROMPTLIST_STATIC
        if candidate.exists():
            _world_singleton = YoloWorldDetector(candidate, pl)
        else:
            _world_singleton = YoloWorldDetector(None, pl)
    elif prompt_list is not None:
        _world_singleton.set_classes(prompt_list)
    return _world_singleton


# helper S3: extracción PromptList desde transcript voz
def extract_prompts_from_transcript(text: str) -> list[str]:
    """Regex simple S3: detecta 'mirá/buscá/dónde está/qué color' + noun fuera W30."""
    import re

    low = text.lower()
    triggers = [
        "mira",
        "mirá",
        "busca",
        "buscá",
        "donde esta",
        "dónde está",
        "que color",
        "qué color",
        "hay",
        "ves",
    ]
    if not any(t in low for t in triggers):
        return []
    # extraer nouns tras trigger (simple split por , . y)
    # buscar frase después de trigger hasta . o ?
    m = re.search(
        r"(?:mira|busca|donde esta|qué color es|que color es|hay|ves)\s+([^.?]+)", low
    )
    if not m:
        return []
    phrase = m.group(1).strip()
    # split por y/,/con
    parts = re.split(r"\s+y\s+|\s*,\s*|\s+con\s+", phrase)
    prompts = [p.strip() for p in parts if len(p.strip()) >= 3 and len(p.strip()) <= 40]
    # filtrar si es W30 ya conocido — solo dinámicos nuevos
    from plataforma.webcam.backend.config import YOLO_WHITELIST

    out: list[str] = []
    for p in prompts:
        # si la frase contiene clase W30 exacta, no es nuevo vocab
        if any(cls in p for cls in YOLO_WHITELIST):
            # aun así puede ser compuesto "taza roja" donde taza ∈ W30 pero rojo es atributo → sí es dinámico  # noqa: E501
            if (
                "roja" in p
                or "rojo" in p
                or "amarillo" in p
                or "negro" in p
                or "azul" in p
            ):
                out.append(p)
            continue
        out.append(p)
    return out[:8]
