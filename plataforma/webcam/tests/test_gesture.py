"""Tests S2-A gesto — headless con landmarks sintéticos.

Valida reglas geométricas open_palm/fist/thumbs_up/none sin cámara ni modelo.
"""

from __future__ import annotations

import pathlib
from types import SimpleNamespace
from typing import Any

from plataforma.webcam.backend.inference.gesture import (
    ALLOWED_LABELS,
    GestoReconocido,
    GestureRecognizer,
    classify_gesture,
    gesto_confidence,
    get_gesture_recognizer,
)


def _lm(x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(x=x, y=y, z=0.0)


def _make_landmarks(dedos_extendidos: list[bool], pulgar_extendido: bool) -> list[Any]:
    """Crea 21 landmarks sintéticos con y controlado para regla dedos.

    dedos_extendidos: [index,middle,ring,pinky] bool
    pulgar_extendido: bool vía distancia muñeca
    """
    lm: list[SimpleNamespace] = [_lm(0.5, 0.5) for _ in range(21)]
    # muñeca 0
    lm[0] = _lm(0.0, 0.0)
    # pulgar: ip 3 y tip 4 — distancia desde muñeca
    if pulgar_extendido:
        lm[3] = _lm(0.1, 0.0)
        lm[4] = _lm(0.3, 0.0)  # lejos → extendido
    else:
        lm[3] = _lm(0.1, 0.0)
        lm[4] = _lm(0.05, 0.0)  # cerca → no extendido
    # dedos: pares (tip,pip) = (8,6),(12,10),(16,14),(20,18)
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    for i, ext in enumerate(dedos_extendidos):
        tip = tips[i]
        pip = pips[i]
        if ext:
            lm[pip] = _lm(0.5, 0.6)
            lm[tip] = _lm(0.5, 0.3)  # tip más arriba (y menor)
        else:
            lm[pip] = _lm(0.5, 0.3)
            lm[tip] = _lm(0.5, 0.6)  # tip más abajo
    return lm


def test_classify_open_palm() -> None:
    lm = _make_landmarks([True, True, True, True], pulgar_extendido=True)
    assert classify_gesture(lm) == "open_palm"


def test_classify_fist() -> None:
    lm = _make_landmarks([False, False, False, False], pulgar_extendido=False)
    assert classify_gesture(lm) == "fist"


def test_classify_thumbs_up() -> None:
    lm = _make_landmarks([False, False, False, False], pulgar_extendido=True)
    assert classify_gesture(lm) == "thumbs_up"


def test_classify_none_mixto() -> None:
    # dos dedos arriba → no es ninguno de los 3 → none
    lm = _make_landmarks([True, True, False, False], pulgar_extendido=False)
    assert classify_gesture(lm) == "none"
    lm2 = _make_landmarks([True, False, False, False], pulgar_extendido=True)
    assert classify_gesture(lm2) == "none"


def test_classify_landmarks_incompletos() -> None:
    assert classify_gesture([]) == "none"
    assert classify_gesture([_lm(0, 0) for _ in range(5)]) == "none"


def test_gesto_confidence() -> None:
    assert gesto_confidence("none") == 0.0
    assert 0.0 < gesto_confidence("open_palm") <= 1.0
    assert 0.0 < gesto_confidence("fist") <= 1.0
    assert 0.0 < gesto_confidence("thumbs_up") <= 1.0


def test_gesture_recognizer_stub_headless() -> None:
    rec = GestureRecognizer(None)
    assert rec.is_stub is True
    # sin imagen → none
    g = rec.recognize(image=None, frame_id=1, ts=1000)
    assert g.label == "none"
    assert g.conf == 0.0
    assert g.frame_id == 1
    # sin modelo, aunque haya imagen dummy → none
    g2 = rec.recognize(image=object(), frame_id=2, ts=2000)
    assert g2.label == "none"


def test_get_gesture_recognizer_stub_headless() -> None:
    rec = get_gesture_recognizer(models_dir=pathlib.Path("/tmp/inexistente_xyz"))
    assert rec.is_stub is True
    g = rec.recognize(image=None, frame_id=5, ts=5000)
    assert g.label in ALLOWED_LABELS


def test_recognize_landmarks_headless() -> None:
    rec = GestureRecognizer(None)
    lm_palm = _make_landmarks([True, True, True, True], True)
    g = rec.recognize_landmarks(lm_palm, frame_id=10, ts=1234)
    assert g.label == "open_palm"
    assert g.frame_id == 10
    assert g.ts == 1234
    assert 0.0 < g.conf <= 1.0

    lm_fist = _make_landmarks([False, False, False, False], False)
    g2 = rec.recognize_landmarks(lm_fist, frame_id=11, ts=1235)
    assert g2.label == "fist"

    lm_thumb = _make_landmarks([False, False, False, False], True)
    g3 = rec.recognize_landmarks(lm_thumb, frame_id=12, ts=1236)
    assert g3.label == "thumbs_up"


def test_gesto_reconocido_es_desacoplado() -> None:
    g = GestoReconocido(label="open_palm", conf=0.9, frame_id=7, ts=9999)
    assert g.label in ALLOWED_LABELS
    assert isinstance(g.conf, float)


def test_ws_run_inference_gesto_allowed_via_stub() -> None:
    """ws.run_inference debe retornar gesto en ALLOWED_LABELS aun sin modelo."""
    from plataforma.webcam.backend.ws import run_inference

    dummy_jpeg = (
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHB"
        "wgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyM"
        "jIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAEAAQA"
        "DASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAA"
        "AAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMB"
        "AAIRAxEAPwCwAA8A/9k="
    )
    _boxes, gesto = run_inference(dummy_jpeg, frame_id=42, ts=1700000000000)
    assert gesto["label"] in ALLOWED_LABELS
    assert gesto["frame_id"] == 42
    assert 0.0 <= gesto["conf"] <= 1.0
    evento = GestoReconocido(
        label=gesto["label"],
        conf=gesto["conf"],
        frame_id=gesto["frame_id"],
        ts=1700000000000,
    )
    assert evento.label in ALLOWED_LABELS


def test_gesture_recognizer_con_imagen_numpy_sin_modelo_sigue_none() -> None:
    import numpy as np

    rec = GestureRecognizer(None)
    fake = np.zeros((480, 640, 3), dtype=np.uint8)
    g = rec.recognize(image=fake, frame_id=1, ts=1)
    assert g.label == "none"
    # imagen inválida (2D) → none defensivo
    bad: Any = np.zeros((640, 640), dtype=np.uint8)
    g2 = rec.recognize(image=bad, frame_id=1, ts=1)
    assert g2.label == "none"


def test_classify_gesture_todos_los_labels_permitidos() -> None:
    for ext, thumb, expected in [
        ([True, True, True, True], True, "open_palm"),
        ([False, False, False, False], False, "fist"),
        ([False, False, False, False], True, "thumbs_up"),
        ([True, False, False, False], False, "none"),
    ]:
        lm = _make_landmarks(ext, thumb)
        label = classify_gesture(lm)
        assert label == expected
        assert label in ALLOWED_LABELS
