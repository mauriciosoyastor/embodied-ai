"""Bloquea citas a archivos inexistentes en docs del Golden Path.

Escanea `.opencode/commands/*.md` y `docs/guides/golden-portable.md`,
extrae citas con forma `docs/adr/*`, `docs/agents/*`, `tests/*` y
`harness/*`, y falla si el archivo citado no existe en el repo.
Evita repetir el caso ADR-0007 citado 4 veces pero ausente en HEAD.
Solo stdlib, sin red.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FUENTES = [
    *sorted((REPO / ".opencode" / "commands").glob("*.md")),
    REPO / "docs" / "guides" / "golden-portable.md",
]
PATRON = re.compile(
    r"(docs/adr/[A-Za-z0-9_.\-]+\.md"
    r"|docs/agents/[A-Za-z0-9_.\-]+\.md"
    r"|docs/agents/lessons/[A-Za-z0-9_.\-]+\.md"
    r"|tests/[A-Za-z0-9_.\-]+\.py"
    r"|harness/[A-Za-z0-9_.\-]+\.py)"
)


def main() -> int:
    rotas: list[str] = []
    for fuente in FUENTES:
        if not fuente.is_file():
            continue
        texto = fuente.read_text(encoding="utf-8")
        for cita in sorted(set(PATRON.findall(texto))):
            if not (REPO / cita).is_file():
                rotas.append(f"{fuente.relative_to(REPO)} -> {cita}")
    if rotas:
        print("Citas rotas (el archivo citado no existe):")
        for rota in rotas:
            print(f"  - {rota}")
        return 1
    print("citas-existen: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
