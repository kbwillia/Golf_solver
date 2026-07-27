"""Live sync helpers: pull RunPod training progress into local RL/output for the viz page."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

RL_DIR = Path(__file__).resolve().parent / "RL"
OUTPUT_DIR = RL_DIR / "output"
PROGRESS_PATH = OUTPUT_DIR / "training_progress.json"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

GAME_LINE_RE = re.compile(
    r"Game\s+(\d+)\s*:\s*(\S+)\s*\|\s*Win rate=([0-9.]+)%,\s*Avg score=([0-9.]+),\s*"
    r"States=(\d+),\s*Epsilon=([0-9.]+)",
    re.IGNORECASE,
)
TQDM_RE = re.compile(
    r"Training Q-learning agent:\s+(\d+)%\|.*?\|\s+(\d+)/(\d+)\s+\[",
)


def _load_dotenv() -> dict[str, str]:
    vals: dict[str, str] = {}
    if not ENV_PATH.exists():
        return vals
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def _ssh_base(env: dict[str, str]) -> list[str] | None:
    host = (env.get("RUNPOD_SSH_HOST") or "").strip()
    port = (env.get("RUNPOD_SSH_PORT") or "").strip()
    if not host or not port:
        return None
    key = env.get("RUNPOD_SSH_KEY_PATH") or str(Path.home() / ".ssh" / "id_ed25519")
    return [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=12",
        "-o",
        "BatchMode=yes",
        "-i",
        key,
        "-p",
        str(port),
        f"root@{host}",
    ]


def _scp_base(env: dict[str, str]) -> tuple[list[str], str] | None:
    host = (env.get("RUNPOD_SSH_HOST") or "").strip()
    port = (env.get("RUNPOD_SSH_PORT") or "").strip()
    if not host or not port:
        return None
    key = env.get("RUNPOD_SSH_KEY_PATH") or str(Path.home() / ".ssh" / "id_ed25519")
    return (
        [
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ConnectTimeout=12",
            "-o",
            "BatchMode=yes",
            "-i",
            key,
            "-P",
            str(port),
        ],
        f"root@{host}",
    )


def _remote_status_and_log(ssh: list[str]) -> tuple[bool, str]:
    remote = r"""
running=0
if [ -f /workspace/logs/train.pid ] && ps -p $(cat /workspace/logs/train.pid) >/dev/null 2>&1; then
  running=1
  ps -p $(cat /workspace/logs/train.pid) -o etime= 2>/dev/null | tr -d ' '
fi
echo "RUNNING=$running"
tail -n 80 /workspace/logs/train.log 2>/dev/null || true
"""
    try:
        out = subprocess.check_output(
            ssh + ["bash", "-lc", remote],
            text=True,
            encoding="utf-8",
            errors="replace",
            stderr=subprocess.DEVNULL,
            timeout=25,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)
    running = "RUNNING=1" in (out or "").splitlines()[:5]
    return running, out or ""


def _parse_progress(log_text: str) -> dict:
    points = []
    for m in GAME_LINE_RE.finditer(log_text):
        points.append(
            {
                "game": int(m.group(1)),
                "phase": m.group(2),
                "win_rate": float(m.group(3)) / 100.0,
                "avg_score": float(m.group(4)),
                "states": int(m.group(5)),
                "epsilon": float(m.group(6)),
            }
        )
    # Dedupe by game, keep last
    by_game = {p["game"]: p for p in points}
    points = [by_game[g] for g in sorted(by_game)]

    pct = None
    current = None
    total = None
    for m in TQDM_RE.finditer(log_text):
        pct = int(m.group(1))
        current = int(m.group(2))
        total = int(m.group(3))

    return {
        "checkpoints": points,
        "tqdm_pct": pct,
        "tqdm_current": current,
        "tqdm_total": total,
    }


def _try_pull_stats(env: dict[str, str]) -> bool:
    scp = _scp_base(env)
    if not scp:
        return False
    scp_cmd, remote = scp
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    remote_file = f"{remote}:/workspace/Golf_solver/backend/RL/output/training_stats.json"
    try:
        subprocess.check_call(
            scp_cmd + [remote_file, str(OUTPUT_DIR / "training_stats.json")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=40,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False


def sync_live_progress() -> dict:
    """SSH to RunPod, parse train.log, optionally pull training_stats.json."""
    # Never overwrite local artifacts while a local trainer owns the files
    try:
        from rl_control import _local_pid
        if _local_pid() is not None:
            return {
                "ok": True,
                "running": True,
                "local": True,
                "pulled_training_stats": False,
                "skipped_remote": True,
            }
    except Exception:
        pass

    env = _load_dotenv()
    ssh = _ssh_base(env)
    if not ssh:
        return {
            "ok": False,
            "error": "Missing RUNPOD_SSH_HOST / RUNPOD_SSH_PORT in .env",
            "running": False,
        }

    running, log_text = _remote_status_and_log(ssh)
    parsed = _parse_progress(log_text)
    # Only pull remote stats when a remote job is active (avoid clobbering local files)
    pulled_stats = _try_pull_stats(env) if running else False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "running": running,
        "pulled_training_stats": pulled_stats,
        **parsed,
    }
    # If we only have sparse checkpoints, synthesize a mini series for the viz
    cps = parsed["checkpoints"]
    if cps:
        payload["series"] = {
            "games": [c["game"] for c in cps],
            "avg_scores": [c["avg_score"] for c in cps],
            "qtable_states": [c["states"] for c in cps],
            "epsilon": [c["epsilon"] for c in cps],
            "win_rates": [c["win_rate"] for c in cps],
        }
        last = cps[-1]
        payload["summary"] = {
            "games_played": parsed["tqdm_current"] or last["game"],
            "games_total": parsed["tqdm_total"],
            "pct": parsed["tqdm_pct"],
            "avg_score": last["avg_score"],
            "final_states": last["states"],
            "final_epsilon": last["epsilon"],
            "win_rate": last["win_rate"],
        }
    elif parsed["tqdm_current"]:
        payload["summary"] = {
            "games_played": parsed["tqdm_current"],
            "games_total": parsed["tqdm_total"],
            "pct": parsed["tqdm_pct"],
        }

    PROGRESS_PATH.write_text(json.dumps(payload), encoding="utf-8")
    return payload
