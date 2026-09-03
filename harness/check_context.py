#!/usr/bin/env python3
"""Guard linter CONTEXT.md — Slice 5: evita .py:line fuera de harness allowlist."""

import re
import sys
from pathlib import Path

ALLOW = re.compile(r"harness/harness\.py:\d+")
PAT = re.compile(r"\.py:\d+")
# regex example line itself should not trigger
ALLOW_EXAMPLE = re.compile(r"Linter de Documentaci")


def check(path: Path = Path("CONTEXT.md")) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    violations = []
    for i, line in enumerate(text.splitlines(), 1):
        if ALLOW_EXAMPLE.search(line):
            continue
        if PAT.search(line) and not ALLOW.search(line):
            violations.append(f"{i}:{line[:120]}")
    if violations:
        # use utf-8 safe print
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        print("CONTEXT.md linter FAIL - anclas .py:\\d+ fuera de allowlist:")
        for v in violations:
            try:
                print(" ", v)
            except UnicodeEncodeError:
                print(" ", v.encode("utf-8", errors="replace").decode())
        print("Ver ADR-0007 Linter de Documentacion - mover a ADR/prototype.")
        return 1
    print("CONTEXT.md linter OK")
    return 0


if __name__ == "__main__":
    sys.exit(check())
