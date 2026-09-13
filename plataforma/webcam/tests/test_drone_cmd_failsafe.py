"""Ticket 03 — gestos mano → comandos drone WS con failsafe (sim → atado).

Tabla 057: fist=acercar, open_palm=alejar (paso fijo lento),
none=quieto (deadman), thumbs_up x2 en 3s=aterrizar (x1 no-op).
Sin heartbeat 500ms → corta motores. ABORTED latch → ignora todo.
"""

from __future__ import annotations

from plataforma.webcam.backend.drone_cmd import (
    HEARTBEAT_TIMEOUT_MS,
    LAND_WINDOW_MS,
    Heartbeat,
    LandingArbiter,
    resolve_drone_cmd,
)


def _arbiter() -> LandingArbiter:
    return LandingArbiter(window_ms=LAND_WINDOW_MS)


def test_tabla_gesto_comando() -> None:
    assert (
        resolve_drone_cmd(
            "fist", now_ms=1000, heartbeat_ok=True, aborted=False, arbiter=_arbiter()
        )
        == "acercar"
    )
    assert (
        resolve_drone_cmd(
            "open_palm",
            now_ms=1000,
            heartbeat_ok=True,
            aborted=False,
            arbiter=_arbiter(),
        )
        == "alejar"
    )
    assert (
        resolve_drone_cmd(
            "none", now_ms=1000, heartbeat_ok=True, aborted=False, arbiter=_arbiter()
        )
        == "quieto"
    )


def test_pulgar_simple_no_hace_nada() -> None:
    assert (
        resolve_drone_cmd(
            "thumbs_up",
            now_ms=1000,
            heartbeat_ok=True,
            aborted=False,
            arbiter=_arbiter(),
        )
        is None
    )


def test_pulgar_doble_en_ventana_aterriza() -> None:
    arb = _arbiter()
    assert (
        resolve_drone_cmd(
            "thumbs_up", now_ms=1000, heartbeat_ok=True, aborted=False, arbiter=arb
        )
        is None
    )
    assert (
        resolve_drone_cmd(
            "thumbs_up", now_ms=2500, heartbeat_ok=True, aborted=False, arbiter=arb
        )
        == "aterrizar"
    )


def test_pulgar_doble_fuera_de_ventana_no_aterriza() -> None:
    arb = _arbiter()
    assert (
        resolve_drone_cmd(
            "thumbs_up", now_ms=1000, heartbeat_ok=True, aborted=False, arbiter=arb
        )
        is None
    )
    assert (
        resolve_drone_cmd(
            "thumbs_up",
            now_ms=1000 + LAND_WINDOW_MS + 1,
            heartbeat_ok=True,
            aborted=False,
            arbiter=arb,
        )
        is None
    )


def test_otro_gesto_resetea_conteo_pulgar() -> None:
    arb = _arbiter()
    assert (
        resolve_drone_cmd(
            "thumbs_up", now_ms=1000, heartbeat_ok=True, aborted=False, arbiter=arb
        )
        is None
    )
    assert (
        resolve_drone_cmd(
            "fist", now_ms=1500, heartbeat_ok=True, aborted=False, arbiter=arb
        )
        == "acercar"
    )
    assert (
        resolve_drone_cmd(
            "thumbs_up", now_ms=2000, heartbeat_ok=True, aborted=False, arbiter=arb
        )
        is None
    )


def test_sin_heartbeat_corta_motores() -> None:
    arb = _arbiter()
    assert (
        resolve_drone_cmd(
            "fist", now_ms=1000, heartbeat_ok=False, aborted=False, arbiter=arb
        )
        is None
    )
    assert (
        resolve_drone_cmd(
            "none", now_ms=1000, heartbeat_ok=False, aborted=False, arbiter=arb
        )
        is None
    )


def test_aborted_ignora_todo() -> None:
    arb = _arbiter()
    for label in ("fist", "open_palm", "none", "thumbs_up"):
        assert (
            resolve_drone_cmd(
                label, now_ms=1000, heartbeat_ok=True, aborted=True, arbiter=arb
            )
            is None
        )


def test_label_desconocido_no_op() -> None:
    assert (
        resolve_drone_cmd(
            "pinza", now_ms=1000, heartbeat_ok=True, aborted=False, arbiter=_arbiter()
        )
        is None
    )


def test_heartbeat_expira_a_500ms() -> None:
    hb = Heartbeat(timeout_ms=HEARTBEAT_TIMEOUT_MS)
    assert hb.expired(1000) is True
    hb.mark(1000)
    assert hb.expired(1200) is False
    assert hb.expired(1000 + HEARTBEAT_TIMEOUT_MS + 1) is True
