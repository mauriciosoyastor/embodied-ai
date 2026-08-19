"""Clasificador de gestos por reglas geometricas (prototipo P2, descartable)."""

import math

DEDOS = [(8, 6), (12, 10), (16, 14), (20, 18)]


def _distancia(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def _pulgar_extendido(lm):
    d_tip = _distancia(lm[4], lm[0])
    d_ip = _distancia(lm[3], lm[0])
    return d_tip > d_ip * 1.15


def clasificar_gesto(lm):
    """lm: lista de 21 landmarks con .x/.y normalizados [0,1], y hacia abajo."""
    dedos = [lm[tip].y < lm[pip].y for (tip, pip) in DEDOS]
    pulgar = _pulgar_extendido(lm)
    n = sum(dedos)
    if n == 4 and pulgar:
        return "open_palm"
    if n == 0 and pulgar:
        return "thumbs_up"
    if n == 0 and not pulgar:
        return "fist"
    return "none"
