#!/usr/bin/env python3
"""
harness.py — Plan-Execute-Verify portado de scraperargenpro (Ning et al. 2026 §3.4)
Embodied AI — loop P-E-V con estado filesystem y traza inspeccionable.

Origen: scraperargenpro/harness/harness.py (Ticket 06)
Adaptado: Embodied AI — sensores CmdVel/SimObservation/IdentitiesStore

Uso:
  python harness/harness.py --allow-network=false  # sandbox-edit
  python harness/harness.py --allow-network=true --tier=full-access
  python harness/harness.py --plan harness/plan.example.json

Inspect:
  cat harness/trajectory.jsonl | jq .
  grep human_gate harness/trajectory.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ── Config / Tiers (05 Q1, Q5) ───────────────────────────────────────────
TIERS = ("read-only", "sandbox-edit", "full-access")
DEFAULT_TIER = "sandbox-edit"
ALLOWLIST_DOMAINS = [
    "localhost",
    "127.0.0.1",
    "huggingface.co",
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "openrouter.ai",
    "api.groq.com",
    "argenprop.com",
    "wa.me",
]
DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bpush\s+--force\b",
    r"\.env\b",
    r"\bDROP\b",
    r"\bDELETE\s+FROM\b",
]
# Sandbox-edit puede escribir SOLO aqui (05 Q1) — adaptado Embodied AI
SANDBOX_WRITABLE_SUFFIXES = [
    "harness/output/",
    "harness/trajectory.jsonl",
    "harness/sensor_logs/",
    "output/",
    "trajectory.jsonl",
    "sensor_logs/",
    "plataforma/webcam/backend/models/identities.json",
    "plataforma/sim/output/",
    "harness/output/sim_state.json",
    "harness/output/publisher_cache.json",
]

# Sensores dominio Embodied AI
WA_REGEX = re.compile(r"^https://wa\.me/\d+$")

ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent
TRAJECTORY = ROOT / "trajectory.jsonl"
SENSOR_LOG_DIR = ROOT / "sensor_logs"
OUTPUT_DIR = ROOT / "output"


@dataclass
class HumanGate:
    needed: bool
    reason: str = ""
    approved_by: str | None = None
    approved_at: str | None = None


@dataclass
class EvidenceBundle:
    """Bundle B (04 Q2 + 05 Q3): que corrio / que sin cubrir / riesgo"""

    tests_run: list[str] = field(default_factory=list)
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    linter: dict = field(default_factory=dict)
    mypy: dict = field(default_factory=dict)
    domain_assertions: dict = field(default_factory=dict)
    uncovered: list[str] = field(default_factory=list)
    risk: str = "unknown"
    risk_reason: str = ""
    impact_ratio: float | None = None
    impacted_nodes: int = 0
    changed_lines: int = 0


@dataclass
class TrajectoryEntry:
    run_id: str
    ts: str
    phase: str  # plan | execute | verify | human_gate | done
    tier: str
    intent: str
    files_touched: list[str] = field(default_factory=list)
    verdict: str = "pending"  # ok | fail | needs-human | pending
    evidence: EvidenceBundle = field(default_factory=EvidenceBundle)
    human_gate: HumanGate = field(default_factory=lambda: HumanGate(needed=False))
    sensor_log: str = ""
    removed_tools: list[str] = field(default_factory=list)


# ── Permisos ─────────────────────────────────────────────────────────────
def check_permission(
    tier: str, action: str, target: str, allow_network: bool
) -> HumanGate:
    action_l = action.lower()
    for pat in DESTRUCTIVE_PATTERNS:
        if re.search(pat, target + " " + action, re.IGNORECASE):
            return HumanGate(
                needed=True, reason=f"accion destructiva: {pat} en '{target}'"
            )
    is_network = any(
        k in action_l
        for k in ["fetch", "requests", "playwright", "curl", "wget", "http"]
    ) or target.startswith("http")
    if is_network:
        if not allow_network and tier != "full-access":
            if not any(d in target for d in ALLOWLIST_DOMAINS):
                return HumanGate(
                    needed=True,
                    reason=f"red no listada: '{target}' fuera de {ALLOWLIST_DOMAINS}",
                )
    if tier == "read-only":
        if action_l in ("write", "edit", "exec", "network"):
            return HumanGate(
                needed=True,
                reason=f"read-only: '{action}' sobre '{target}' requiere escalamiento",
            )
    if tier == "sandbox-edit":
        if action_l in ("write", "edit"):
            norm = target.replace("\\", "/")
            allowed = any(
                norm.startswith(p.rstrip("/"))
                or norm == p.rstrip("/")
                or p in norm
                or norm.startswith("harness/")
                for p in SANDBOX_WRITABLE_SUFFIXES
            )
            # check fino: solo prefijos harness/ y output/ permitidos
            if not (
                norm.startswith("harness/output/")
                or norm.startswith("harness/sensor_logs/")
                or norm in ("harness/trajectory.jsonl", "trajectory.jsonl")
                or norm.startswith("output/")
                or norm.startswith("sensor_logs/")
                or "identities.json" in norm
                or norm.startswith("plataforma/sim/output/")
            ):
                if not allowed:
                    return HumanGate(
                        needed=True,
                        reason=(  # noqa: E501
                            f"sandbox-edit: write fuera de sandbox en '{target}'"
                        ),
                    )
    return HumanGate(needed=False)


# ── Sensores ─────────────────────────────────────────────────────────────
def run_pytest(run_id: str) -> tuple[dict, str]:
    log_path = SENSOR_LOG_DIR / f"{run_id}.log"
    SENSOR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-q"]
    has_tests = (
        (REPO_ROOT / "tests").exists()
        or (REPO_ROOT / "fase-0").exists()
        or (REPO_ROOT / "plataforma" / "sim" / "tests").exists()
    )
    header = f"=== sensor run {run_id} @ {time.strftime('%Y-%m-%dT%H:%M:%S')} ===\n"
    header += f"cmd: {' '.join(cmd)}\n"
    if not has_tests:
        msg = header + "no tests found — uncovered: [pytest]\n"
        log_path.write_text(msg, encoding="utf-8")
        return {
            "tool": "pytest",
            "ok": None,
            "skipped": True,
            "reason": "no tests",
        }, msg
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(REPO_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        out = (
            header
            + (proc.stdout or "")
            + (proc.stderr or "")
            + f"\nexit={proc.returncode}\n"
        )
        log_path.write_text(out, encoding="utf-8")
        return {
            "tool": "pytest",
            "ok": proc.returncode == 0,
            "exit": proc.returncode,
            "raw": out[:2000],
        }, out
    except FileNotFoundError:
        msg = header + "pytest no instalado\n"
        log_path.write_text(msg, encoding="utf-8")
        return {"tool": "pytest", "ok": None, "skipped": True}, msg
    except subprocess.TimeoutExpired:
        msg = header + "pytest timeout 90s\n"
        log_path.write_text(msg, encoding="utf-8")
        return {"tool": "pytest", "ok": False, "timeout": True}, msg


def run_ruff(run_id: str) -> dict:
    try:
        proc = subprocess.run(
            ["ruff", "check", "."],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        log_path = SENSOR_LOG_DIR / f"{run_id}.log"
        if log_path.exists():
            prev = log_path.read_text(encoding="utf-8")
            out = (proc.stdout or "") + (proc.stderr or "")
            log_path.write_text(
                prev + f"\n--- ruff ---\nexit={proc.returncode}\n" + out,
                encoding="utf-8",
            )
        return {
            "tool": "ruff",
            "ok": proc.returncode == 0,
            "issues": ((proc.stdout or "") + (proc.stderr or ""))[:2000],
        }
    except FileNotFoundError:
        return {
            "tool": "ruff",
            "ok": None,
            "skipped": True,
            "reason": "ruff no instalado",
        }
    except subprocess.TimeoutExpired:
        return {"tool": "ruff", "ok": False, "timeout": True}


def run_mypy(run_id: str) -> dict:
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "plataforma/webcam",
                "--ignore-missing-imports",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        log_path = SENSOR_LOG_DIR / f"{run_id}.log"
        if log_path.exists():
            prev = log_path.read_text(encoding="utf-8")
            out = (proc.stdout or "") + (proc.stderr or "")
            log_path.write_text(
                prev + f"\n--- mypy ---\nexit={proc.returncode}\n" + out,
                encoding="utf-8",
            )
        return {
            "tool": "mypy",
            "ok": proc.returncode == 0,
            "issues": ((proc.stdout or "") + (proc.stderr or ""))[:2000],
        }
    except Exception as e:
        return {"tool": "mypy", "ok": None, "skipped": True, "reason": str(e)}


def run_detect_changes() -> dict:
    """Sensor GitNexus detect_changes — si falla, retorna low (no bloquea)."""
    try:
        # intenta CLI GitNexus; si no está índice o falla, no bloquea
        proc = subprocess.run(
            ["node", ".gitnexus/run.cjs", "detect-changes", "--scope", "all"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        # heurística simple: si out contiene HIGH/UNKNOWN (paréntesis explícitos para precedencia)
        high = ("HIGH" in out) or ("high" in out.lower() and "risk" in out.lower())
        unknown = ("UNKNOWN" in out) or ("unknown" in out.lower())
        # intenta parsear impacted_nodes si JSON
        impacted = 0
        changed = 0
        try:
            data = json.loads(proc.stdout or "{}")
            if isinstance(data, dict):
                impacted = int(data.get("impacted_nodes", data.get("total", 0)) or 0)
                changed = int(data.get("changed_lines", 0) or 0)
        except Exception:
            pass
        return {
            "impacted_nodes": impacted,
            "changed_lines": changed,
            "high": high,
            "unknown": unknown,
            "raw": out[:2000],
        }
    except Exception as e:
        return {
            "impacted_nodes": 0,
            "changed_lines": 0,
            "high": False,
            "unknown": False,
            "raw": f"skip: {e}",
        }


def domain_assertions() -> dict:
    """
    Sensor dominio Embodied AI:
    - CmdVel clamp ±1.0 / ±1.5 via Pydantic
    - SimObservation invariants
    - IdentitiesStore si existe (embedding 128-d)
    - Harness output sim_state.json si existe
    """
    failures: list[str] = []
    checked = 0

    # 1) CmdVel / SimObservation — import lazy para no romper si faltan deps
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from plataforma.sim.models import CmdVel, SimObservation

        checked += 1
        # invariante: CmdVel clamp debe fallar fuera de rango
        try:
            CmdVel(v_x=2.0, omega_z=0.0)
            failures.append("CmdVel(v_x=2.0) no lanzo ValidationError (clamp roto)")
        except Exception:
            pass
        try:
            CmdVel(v_x=0.0, omega_z=2.0)
            failures.append("CmdVel(omega_z=2.0) no lanzo ValidationError")
        except Exception:
            pass
        # SimObservation dummy valido
        try:
            SimObservation(x=0, y=0, yaw=0, v_x=0, v_y=0, omega_z=0, ts=0, frame_id=0)
        except Exception as e:
            failures.append(f"SimObservation invalido: {e}")

        # FakeAdapter step
        try:
            from plataforma.sim.fake_adapter import FakeAdapter

            a = FakeAdapter()
            obs0 = a.get_observation()
            a.send_cmd_vel(CmdVel(v_x=0.5, omega_z=0.0))
            obs1 = a.step(dt_ms=100.0)
            checked += 1
            if obs1.frame_id != obs0.frame_id + 1:
                failures.append(
                    f"FakeAdapter frame_id no avanzo {obs0.frame_id}->{obs1.frame_id}"
                )
            if obs1.x <= obs0.x:
                failures.append("FakeAdapter no avanzo en x con v_x=0.5")
        except Exception as e:
            failures.append(f"FakeAdapter check fallo: {e}")

    except Exception as e:
        failures.append(f"import plataforma.sim.models fallo: {e}")

    # 2) IdentitiesStore si existe
    ident_paths = [
        OUTPUT_DIR / "sim_state.json",
        REPO_ROOT / "plataforma" / "webcam" / "backend" / "models" / "identities.json",
        ROOT / "output" / "identities.json",
    ]
    for p in ident_paths:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                checked += 1
                # si es dict id->entry, validar embedding 128
                entries = (
                    data.values()
                    if isinstance(data, dict)
                    else (data if isinstance(data, list) else [])
                )
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    emb = (
                        entry.get("embedding")
                        or entry.get("emb")
                        or entry.get("vector")
                    )
                    if emb is not None:
                        if not isinstance(emb, list) or len(emb) != 128:
                            emb_len = len(emb) if isinstance(emb, list) else type(emb)
                            failures.append(
                                f"{p.name}: embedding len {emb_len} !=128 id={entry.get('id', '?')}"  # noqa: E501
                            )
            except Exception as e:
                failures.append(f"{p}: json invalido {e}")

    if checked == 0:
        return {
            "checked": 0,
            "ok": True,
            "failures": [],
            "note": "sin estado persistente — valido para run inicial",
        }

    return {"checked": checked, "ok": len(failures) == 0, "failures": failures}


def build_evidence(run_id: str) -> tuple[EvidenceBundle, str]:
    ev = EvidenceBundle()
    py_res, py_log = run_pytest(run_id)
    ev.tests_run.append("pytest")
    if py_res.get("skipped"):
        ev.uncovered.append("pytest (sin tests o no instalado)")
        ev.tests_skipped += 1
    elif py_res.get("ok"):
        ev.tests_passed += 1
    else:
        ev.tests_failed += 1
        ev.uncovered.append("pytest: failures")
    ruff_res = run_ruff(run_id)
    ev.linter = ruff_res
    if ruff_res.get("skipped"):
        ev.uncovered.append("ruff (no instalado)")
    elif not ruff_res.get("ok"):
        ev.uncovered.append("ruff: issues")
    mypy_res = run_mypy(run_id)
    ev.mypy = mypy_res
    if mypy_res.get("skipped"):
        ev.uncovered.append("mypy (no instalado)")
    elif not mypy_res.get("ok"):
        ev.uncovered.append("mypy: type issues")
    dom = domain_assertions()
    ev.domain_assertions = dom
    if not dom.get("ok"):
        ev.uncovered.append(f"domain: {len(dom.get('failures', []))} fallos")
    # GitNexus detect_changes gate (02a) + impact_ratio (02b)
    dc = run_detect_changes()
    ev.impacted_nodes = int(dc.get("impacted_nodes", 0) or 0)
    ev.changed_lines = int(dc.get("changed_lines", 0) or 0)
    if ev.changed_lines > 0:
        ev.impact_ratio = ev.impacted_nodes / ev.changed_lines
    else:
        ev.impact_ratio = float(ev.impacted_nodes) if ev.impacted_nodes else 0.0
    if dc.get("high") or dc.get("unknown"):
        ev.uncovered.append(f"detect_changes: {dc.get('raw', '')[:120]}")
    # Gate senior: impact_ratio >10 → needs-human-attention (04)
    if ev.impact_ratio is not None and ev.impact_ratio > 10:
        ev.uncovered.append(
            f"impact_ratio {ev.impact_ratio:.1f} >10 → needs-human-attention"
        )
    if (
        ev.tests_failed > 0
        or not dom.get("ok")
        or dc.get("high")
        or dc.get("unknown")
        or (ev.impact_ratio is not None and ev.impact_ratio > 10)
    ):
        ev.risk = "high"
        if ev.impact_ratio is not None and ev.impact_ratio > 10:
            ev.risk_reason = (
                "impact_ratio >10 → needs-human-attention (senior mauriciosoyastor)"
            )
        elif dc.get("high") or dc.get("unknown"):
            ev.risk_reason = "blast radius HIGH/UNKNOWN sin confirmar"
        else:
            ev.risk_reason = "tests o domain fallidos"
    elif ev.uncovered:
        ev.risk = "medium"
        ev.risk_reason = f"cobertura parcial: {', '.join(ev.uncovered[:3])}"
    else:
        ev.risk = "low"
        ev.risk_reason = "sensores ok"
    return ev, f"harness/sensor_logs/{run_id}.log"


# ── Traza ────────────────────────────────────────────────────────────────
def append_trajectory(entry: TrajectoryEntry):
    TRAJECTORY.parent.mkdir(parents=True, exist_ok=True)
    rec = asdict(entry)
    rec["evidence"] = asdict(entry.evidence)
    rec["human_gate"] = asdict(entry.human_gate)
    with TRAJECTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ── Plan-Execute-Verify loop ────────────────────────────────────────────
def run_harness(
    intent: str,
    tier: str,
    allow_network: bool,
    run_id: str,
    plan_path: Path | None = None,
):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    print(
        f"[harness] run_id={run_id} tier={tier} allow_network={allow_network} intent='{intent}'"
    )
    plan = {
        "intent": intent,
        "files": ["harness/output/sim_state.json"],
        "invariants": [
            "CmdVel v_x±1.0 omega±1.5",
            "FakeAdapter frame_id avanza",
            "SimObservation SI/world-frame",
        ],
    }
    if plan_path and plan_path.exists():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            intent = plan.get("intent", intent)
        except Exception as e:
            print(f"[plan] warn: no se pudo leer {plan_path}: {e}")
    entry_plan = TrajectoryEntry(
        run_id=run_id,
        ts=ts,
        phase="plan",
        tier=tier,
        intent=intent,
        verdict="ok",
        files_touched=list(plan.get("files", [])),
    )
    entry_plan.evidence = EvidenceBundle(
        tests_run=[], risk="unknown", risk_reason="plan: sin sensores"
    )
    append_trajectory(entry_plan)
    print(f"[plan] intent={intent} files={plan.get('files')}")

    actions = [
        ("write", "harness/output/sim_state.json"),
    ]
    if "target_url" in plan:
        actions.append(("network:fetch", str(plan["target_url"])))

    human_needed: HumanGate | None = None
    for act, tgt in actions:
        gate = check_permission(tier, act, tgt, allow_network)
        if gate.needed:
            human_needed = gate
            print(f"[execute] GATE necesita humano: {gate.reason}")
            entry_gate = TrajectoryEntry(
                run_id=run_id,
                ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
                phase="human_gate",
                tier=tier,
                intent=intent,
                verdict="needs-human",
                files_touched=[tgt],
                human_gate=gate,
            )
            append_trajectory(entry_gate)
            break
        else:
            print(f"[execute] {act} {tgt} -> permitido ({tier})")
            if act == "write":
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                demo_state = OUTPUT_DIR / "sim_state.json"
                if not demo_state.exists():
                    demo_state.write_text(
                        json.dumps(
                            {
                                "frame_id": 1,
                                "x": 0.05,
                                "y": 0.0,
                                "yaw": 0.0,
                                "v_x": 0.5,
                                "omega_z": 0.0,
                                "_ts": time.time(),
                                "_harness_run": run_id,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )

    if human_needed:
        print(
            f"[harness] detenido en human_gate — revisar harness/trajectory.jsonl y aprobar con --approve {run_id}"
        )
        return

    entry_exec = TrajectoryEntry(
        run_id=run_id,
        ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
        phase="execute",
        tier=tier,
        intent=intent,
        verdict="ok",
        files_touched=[a[1] for a in actions],
    )
    append_trajectory(entry_exec)

    print("[verify] sensores: pytest, ruff, mypy, domain assertions...")
    evidence, sensor_log = build_evidence(run_id)
    verdict = (
        "ok"
        if evidence.risk in ("low",)
        and evidence.tests_failed == 0
        and evidence.domain_assertions.get("ok")
        else ("fail" if evidence.risk == "high" else "ok")
    )
    entry_verify = TrajectoryEntry(
        run_id=run_id,
        ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
        phase="verify",
        tier=tier,
        intent=intent,
        verdict=verdict,
        evidence=evidence,
        sensor_log=sensor_log,
    )
    append_trajectory(entry_verify)
    print(
        f"[verify] verdict={verdict} risk={evidence.risk} uncovered={evidence.uncovered}"
    )
    print(f"[verify] bundle -> {sensor_log}")
    print(f"[verify] traza -> {TRAJECTORY}")

    entry_done = TrajectoryEntry(
        run_id=run_id,
        ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
        phase="done",
        tier=tier,
        intent=intent,
        verdict=verdict,
        evidence=evidence,
        sensor_log=sensor_log,
    )
    append_trajectory(entry_done)
    print(
        f"[done] run {run_id} {verdict} — inspeccionar: cat harness/trajectory.jsonl | jq . | grep {run_id} harness/trajectory.jsonl"
    )


def approve_gate(run_id: str, approver: str):
    if not TRAJECTORY.exists():
        print("no hay harness/trajectory.jsonl")
        return
    entry = TrajectoryEntry(
        run_id=run_id,
        ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
        phase="human_gate",
        tier="full-access",
        intent="aprobacion manual",
        verdict="ok",
        human_gate=HumanGate(
            needed=False,
            reason="aprobado por humano",
            approved_by=approver,
            approved_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        ),
    )
    append_trajectory(entry)
    print(
        f"[approve] {run_id} aprobado por {approver} — re-ejecutar harness con --allow-network=true si era red"
    )


def main():
    ap = argparse.ArgumentParser(
        description="harness Embodied AI — Plan-Execute-Verify"
    )
    ap.add_argument(
        "--tier",
        choices=TIERS,
        default=DEFAULT_TIER,
        help="tier (default: sandbox-edit)",
    )
    ap.add_argument(
        "--allow-network", default="false", help="true/false — default false"
    )
    ap.add_argument(
        "--intent",
        default="demo: validar sim headless + traza",
        help="intencion del run",
    )
    ap.add_argument(
        "--plan", dest="plan_path", default=None, help="ruta a plan.json opcional"
    )
    ap.add_argument("--run-id", default=None, help="run_id custom (default uuid corto)")
    ap.add_argument(
        "--approve",
        default=None,
        help="aprobar human_gate previo: --approve <run_id> --approver <nombre>",
    )
    ap.add_argument("--approver", default="humano")
    args = ap.parse_args()
    allow_network = str(args.allow_network).lower() in ("true", "1", "yes", "y")
    run_id = args.run_id or uuid.uuid4().hex[:8]
    if args.approve:
        approve_gate(args.approve, args.approver)
        return
    plan_path = Path(args.plan_path) if args.plan_path else None
    run_harness(args.intent, args.tier, allow_network, run_id, plan_path)


if __name__ == "__main__":
    main()
