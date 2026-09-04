#!/usr/bin/env python3
"""
context_injector.py — Productivo para #127 (Golden Path Fusión)
Filtra harness/trajectory.jsonl por files_touched overlap
y emite ## Contexto Episódico (últimos 5 fails).

Uso:
  uv run python harness/context_injector.py --issue 127 \
    --files plataforma/webcam/backend/ws.py --limit 5
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

TRAJ = Path(__file__).parent / "trajectory.jsonl"
# Demo fallback si no existe trajectory.jsonl
DEMO = [
    {
        "phase": "verify",
        "verdict": "fail",
        "evidence": {
            "risk": "high",
            "risk_reason": "blast radius HIGH/UNKNOWN sin confirmar",
            "impact_ratio": 17.5,
        },
        "files_touched": ["plataforma/webcam/backend/ws.py"],
        "ts": "2026-09-03T02:20:00",
        "run_id": "demo-1",
    },
    {
        "phase": "verify",
        "verdict": "fail",
        "evidence": {
            "risk": "high",
            "risk_reason": "ruff F821 Undefined name run_inference",
        },
        "files_touched": ["plataforma/webcam/tests/test_ws.py"],
        "ts": "2026-09-03T01:10:00",
        "run_id": "demo-2",
    },
    {
        "phase": "verify",
        "verdict": "fail",
        "evidence": {"risk": "medium", "risk_reason": "mypy: type issues"},
        "files_touched": [
            "plataforma/webcam/backend/ws.py",
            "plataforma/webcam/backend/yolo.py",
        ],
        "ts": "2026-09-03T00:50:00",
        "run_id": "demo-3",
    },
    {
        "phase": "verify",
        "verdict": "ok",
        "evidence": {"risk": "low"},
        "files_touched": ["plataforma/webcam/backend/ws.py"],
        "ts": "2026-09-02T23:00:00",
        "run_id": "demo-ok",
    },
]


def load_trajectory() -> list[dict]:
    if TRAJ.exists():
        out = []
        for line in TRAJ.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out
    return DEMO


def inject(issue: int, files: list[str], limit: int = 5) -> str:
    traj = load_trajectory()
    # filtra fails con overlap files_touched
    candidates = []
    for rec in reversed(traj):  # últimos primero
        if rec.get("verdict") != "fail":
            continue
        touched = (
            rec.get("files_touched")
            or rec.get("evidence", {}).get("files_touched")
            or []
        )
        # overlap
        overlap = (
            any(any(f in t or t in f for t in touched) for f in files)
            if files and touched
            else True
        )
        if overlap or not files:
            candidates.append(rec)
        if len(candidates) >= limit * 3:  # buffer
            break
    # toma últimos 5 cronológicos
    out = list(reversed(candidates[-limit:]))
    md = []
    md.append("## Contexto Episódico (últimos 5 fails por `files_touched` overlap)")
    md.append(
        f"_Issue #{issue} — filtro: {', '.join(files) if files else 'global'}"  # noqa: E501
        f" — límite {limit} — tokens ~{len(out) * 120} (_estimado_)_"
    )
    md.append("")
    if not out:
        md.append(
            "_Sin fallos previos con overlap — primer intento en estos archivos._"
        )
        return "\n".join(md)
    for r in out:
        ev = r.get("evidence", {})
        md.append(
            f"- `{r.get('ts', '?')}` `run:{r.get('run_id', '?')}`"  # noqa: E501
            f" `phase:{r.get('phase')}` `verdict:fail` `risk:{ev.get('risk')} `"
            f" `files:{','.join(r.get('files_touched', []))}`"
        )
        md.append(
            f"  - razón: `{ev.get('risk_reason', '?')}`"  # noqa: E501
            f" `impact_ratio:{ev.get('impact_ratio', '?')}`"
        )
        # truncated log hint
        md.append(f"  - log: `harness/sensor_logs/{r.get('run_id')}.log`")
    md.append("")
    md.append(
        "_Inyección en `AGENT-BRIEF.md` → `## Contexto Episódico`"  # noqa: E501
        " antes de `## Acceptance`_"
    )
    return "\n".join(md)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Prototype context injector #127")
    ap.add_argument("--issue", type=int, default=127)
    ap.add_argument("--files", nargs="*", default=["plataforma/webcam/backend/ws.py"])
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()
    md = inject(args.issue, args.files, args.limit)
    print(md)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"\n[written to {args.out}]")
    # surface state
    print("\n--- state ---")
    print(f"trajectory lines: {len(load_trajectory())} files filter: {args.files}")
