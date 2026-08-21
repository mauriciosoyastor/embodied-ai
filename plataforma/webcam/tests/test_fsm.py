"""Tests S2-C — MissionFSM headless con secuencias sintéticas.

Sin cámara/WS/MediaPipe — solo GestoReconocido sintético.
Cubre histéresis N=5 conf>=0.7, latch ABORTED, reset y on_observacion no-op.
"""

from __future__ import annotations

from plataforma.webcam.backend.fsm import (
    CONF_THRESHOLD,
    HYSTERESIS_N,
    Estado,
    GestoReconocido,
    MissionFSM,
)


def _gesto(
    label: str,
    conf: float = 0.9,
    frame_id: int = 0,
    ts: int = 1700000000000,
) -> GestoReconocido:
    # cast para Literal — tests controlan valores
    return GestoReconocido(
        label=label,  # type: ignore[arg-type]
        conf=conf,
        frame_id=frame_id,
        ts=ts,
    )


def _seq(fsm: MissionFSM, label: str, n: int, conf: float = 0.9) -> Estado:
    estado: Estado = fsm.estado
    for i in range(n):
        estado = fsm.handle_gesto(
            _gesto(label, conf=conf, frame_id=i, ts=1700000000000 + i)
        )
    return estado


# ---------------------------------------------------------------------------
# Estado inicial y no-op
# ---------------------------------------------------------------------------


def test_initial_state_idle() -> None:
    fsm = MissionFSM()
    assert fsm.estado == Estado.IDLE


def test_none_no_op() -> None:
    fsm = MissionFSM()
    for i in range(10):
        assert fsm.handle_gesto(_gesto("none", conf=0.99, frame_id=i)) == Estado.IDLE
    assert fsm.estado == Estado.IDLE


def test_conf_baja_no_transiciona() -> None:
    fsm = MissionFSM()
    # 10 gestos thumbs_up pero conf < threshold → no hay transición
    for i in range(10):
        st = fsm.handle_gesto(_gesto("thumbs_up", conf=0.5, frame_id=i))
        assert st == Estado.IDLE
    # incluso en el límite <0.7
    fsm2 = MissionFSM()
    assert _seq(fsm2, "thumbs_up", 5, conf=0.69) == Estado.IDLE


def test_conf_umbral_inclusive() -> None:
    fsm = MissionFSM()
    assert _seq(fsm, "thumbs_up", 5, conf=CONF_THRESHOLD) == Estado.RUNNING


def test_on_observacion_no_op() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "thumbs_up", 5)
    assert fsm.estado == Estado.RUNNING
    # observación no debe modificar estado
    fsm.on_observacion(frame_id=1, cls="person", conf=0.9, area=0.2)
    assert fsm.estado == Estado.RUNNING
    fsm.on_observacion({"frame_id": 2, "cls": "person", "conf": 0.99, "area": 0.5})
    assert fsm.estado == Estado.RUNNING
    # observación incluso con valores extremos no cambia
    fsm2 = MissionFSM()
    fsm2.on_observacion(frame_id=99, cls="person", conf=0.99, area=0.99)
    assert fsm2.estado == Estado.IDLE


# ---------------------------------------------------------------------------
# Histéresis N=5
# ---------------------------------------------------------------------------


def test_thumbs_up_4_no_transiciona() -> None:
    fsm = MissionFSM()
    assert _seq(fsm, "thumbs_up", 4) == Estado.IDLE
    # quinto dispara
    assert fsm.handle_gesto(_gesto("thumbs_up", frame_id=4)) == Estado.RUNNING


def test_thumbs_up_5_a_running() -> None:
    fsm = MissionFSM()
    assert _seq(fsm, "thumbs_up", 5) == Estado.RUNNING


def test_histeresis_reset_por_gesto_intercalado() -> None:
    fsm = MissionFSM()
    # 3 thumbs_up, 1 fist rompe racha, luego 4 thumbs_up no alcanzan N
    for i in range(3):
        fsm.handle_gesto(_gesto("thumbs_up", frame_id=i))
    assert fsm.estado == Estado.IDLE
    fsm.handle_gesto(_gesto("fist", frame_id=3))
    # racha reinicia
    for i in range(4):
        fsm.handle_gesto(_gesto("thumbs_up", frame_id=10 + i))
    assert fsm.estado == Estado.IDLE
    # quinto consecutivo sí transiciona
    assert fsm.handle_gesto(_gesto("thumbs_up", frame_id=20)) == Estado.RUNNING


def test_histeresis_reset_por_conf_baja() -> None:
    fsm = MissionFSM()
    for i in range(4):
        fsm.handle_gesto(_gesto("thumbs_up", frame_id=i))
    # conf baja rompe racha
    fsm.handle_gesto(_gesto("thumbs_up", conf=0.6, frame_id=4))
    assert fsm.estado == Estado.IDLE
    # necesita 5 consecutivos nuevos
    assert _seq(MissionFSM(), "thumbs_up", 5) == Estado.RUNNING
    # en la fsm original, necesita 5 más
    assert _seq(fsm, "thumbs_up", 4) == Estado.IDLE
    assert fsm.handle_gesto(_gesto("thumbs_up", frame_id=99)) == Estado.RUNNING


def test_hysteresis_n_const() -> None:
    assert HYSTERESIS_N == 5
    assert CONF_THRESHOLD == 0.7


# ---------------------------------------------------------------------------
# RUNNING ↔ PAUSED
# ---------------------------------------------------------------------------


def test_running_a_paused() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "thumbs_up", 5)
    assert fsm.estado == Estado.RUNNING
    assert _seq(fsm, "open_palm", 5) == Estado.PAUSED


def test_paused_a_running() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "thumbs_up", 5)
    _ = _seq(fsm, "open_palm", 5)
    assert fsm.estado == Estado.PAUSED
    assert _seq(fsm, "thumbs_up", 5) == Estado.RUNNING


def test_idle_open_palm_a_paused() -> None:
    fsm = MissionFSM()
    assert _seq(fsm, "open_palm", 5) == Estado.PAUSED


# ---------------------------------------------------------------------------
# ABORTED latch
# ---------------------------------------------------------------------------


def test_fist_5_a_aborted_desde_idle() -> None:
    fsm = MissionFSM()
    assert _seq(fsm, "fist", 5) == Estado.ABORTED


def test_fist_5_a_aborted_desde_running() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "thumbs_up", 5)
    assert fsm.estado == Estado.RUNNING
    assert _seq(fsm, "fist", 5) == Estado.ABORTED


def test_aborted_latch_bloquea_thumbs_up() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "fist", 5)
    assert fsm.estado == Estado.ABORTED
    # 10 thumbs_up no deben salir de ABORTED
    for i in range(10):
        st = fsm.handle_gesto(_gesto("thumbs_up", frame_id=100 + i))
        assert st == Estado.ABORTED
    assert fsm.estado == Estado.ABORTED


def test_aborted_latch_bloquea_open_palm() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "fist", 5)
    for i in range(10):
        assert fsm.handle_gesto(_gesto("open_palm", frame_id=i)) == Estado.ABORTED


def test_aborted_permanece_con_fist_repetido() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "fist", 5)
    for i in range(5):
        assert fsm.handle_gesto(_gesto("fist", frame_id=i)) == Estado.ABORTED


def test_reset_desde_aborted_a_idle() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "fist", 5)
    assert fsm.estado == Estado.ABORTED
    reset_estado = fsm.reset()
    assert reset_estado is Estado.IDLE
    assert fsm.estado is Estado.IDLE  # type: ignore[comparison-overlap]


def test_reset_luego_thumbs_up_a_running() -> None:
    fsm = MissionFSM()
    _ = _seq(fsm, "fist", 5)
    assert fsm.estado == Estado.ABORTED
    fsm.reset()
    assert _seq(fsm, "thumbs_up", 5) == Estado.RUNNING


def test_secuencia_completa_fsm() -> None:
    """IDLE→RUNNING↔PAUSED→ABORTED→IDLE→RUNNING con histéresis."""
    fsm = MissionFSM()
    assert fsm.estado == Estado.IDLE
    assert _seq(fsm, "thumbs_up", 5) == Estado.RUNNING
    assert _seq(fsm, "open_palm", 5) == Estado.PAUSED
    assert _seq(fsm, "thumbs_up", 5) == Estado.RUNNING
    assert _seq(fsm, "fist", 5) == Estado.ABORTED
    # latch bloquea
    assert _seq(fsm, "thumbs_up", 5) == Estado.ABORTED
    assert _seq(fsm, "open_palm", 5) == Estado.ABORTED
    reset_st = fsm.reset()
    assert reset_st == Estado.IDLE
    assert _seq(fsm, "thumbs_up", 5) == Estado.RUNNING
    # on_observacion intercalada no afecta
    fsm.on_observacion(frame_id=999, cls="person", conf=0.95, area=0.3)
    assert fsm.estado == Estado.RUNNING  # type: ignore


def test_handle_gesto_retorna_estado_actual() -> None:
    fsm = MissionFSM()
    # primer gesto retorna IDLE (histéresis no alcanzada)
    st = fsm.handle_gesto(_gesto("thumbs_up", frame_id=0))
    assert st == Estado.IDLE
    # tras 5 retorna nuevo estado
    for i in range(1, 5):
        st = fsm.handle_gesto(_gesto("thumbs_up", frame_id=i))
    assert st == Estado.RUNNING
