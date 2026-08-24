"""Mirror backend de PercepcionVista — reexporta desde sim/whiteboard."""

from __future__ import annotations

from plataforma.sim.whiteboard import (  # type: ignore[import-not-found]
    LeyendaVista,
    PercepcionVista,
    WhiteboardState,
)

__all__ = ["LeyendaVista", "PercepcionVista", "WhiteboardState"]
