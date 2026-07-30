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
    r"(?:States|Params)=(\d+),\s*Epsilon=([0-9.]+)",
    re.IGNORECASE,
)
TQDM_RE = re.compile(
    r"Training (?:Q-learning agent|DQN(?: agent)?):\s+(\d+)%\|.*?\|\s+(\d+)/(\d+)\s+\[",
    re.IGNORECASE,
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
# Prefer progress file existence marker for the UI
if [ -f /workspace/Golf_solver/backend/RL/output/training_progress.json ]; then
  echo "HAS_PROGRESS=1"
else
  echo "HAS_PROGRESS=0"
fi
if [ -f /workspace/Golf_solver/backend/RL/output/training_stats.json ]; then
  echo "HAS_STATS=1"
else
  echo "HAS_STATS=0"
fi
tail -n 120 /workspace/logs/train.log 2>/dev/null || true
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
    head = "\n".join((out or "").splitlines()[:8])
    running = "RUNNING=1" in head
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


GPU_LIVE_DIR = OUTPUT_DIR / "gpu_live"
GPU_PROGRESS_PATH = GPU_LIVE_DIR / "training_progress.json"


def _try_pull_file(env: dict[str, str], name: str, dest_dir: Path | None = None) -> bool:
    scp = _scp_base(env)
    if not scp:
        return False
    scp_cmd, remote = scp
    target_dir = dest_dir or OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    remote_file = f"{remote}:/workspace/Golf_solver/backend/RL/output/{name}"
    try:
        subprocess.check_call(
            scp_cmd + [remote_file, str(target_dir / name)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        return (target_dir / name).exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False


def _load_local_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _write_progress_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def sync_live_progress() -> dict:
    """SSH to RunPod and pull progress/stats.

    If a local CPU trainer is running, GPU artifacts go to output/gpu_live/ so they
    do not clobber the local Q-table / progress files. CPU + GPU can run together.
    """
    local_running = False
    try:
        from rl_control import _local_cpu_active

        _pid, hb = _local_cpu_active()
        local_running = _pid is not None or bool(hb.get("active"))
    except Exception:
        try:
            from rl_control import _local_pid

            local_running = _local_pid() is not None
        except Exception:
            local_running = False

    env = _load_dotenv()
    ssh = _ssh_base(env)
    if not ssh:
        return {
            "ok": False,
            "error": "Missing RUNPOD_SSH_HOST / RUNPOD_SSH_PORT in .env",
            "running": local_running,
            "local": local_running,
            "cpu_running": local_running,
            "gpu_running": False,
        }

    # While CPU owns the main output dir, park GPU sync alongside it
    dest_dir = GPU_LIVE_DIR if local_running else OUTPUT_DIR
    progress_path = GPU_PROGRESS_PATH if local_running else PROGRESS_PATH

    running, log_text = _remote_status_and_log(ssh)
    has_progress = "HAS_PROGRESS=1" in "\n".join(log_text.splitlines()[:8])
    has_stats = "HAS_STATS=1" in "\n".join(log_text.splitlines()[:8])

    pulled_progress = _try_pull_file(env, "training_progress.json", dest_dir=dest_dir) if has_progress else False
    remote_progress = _load_local_json(progress_path) if pulled_progress else None

    should_pull_stats = has_stats and (
        running
        or not (remote_progress or {}).get("running", True)
        or bool((remote_progress or {}).get("summary"))
        or "TRAINING COMPLETE" in log_text
        or "DQN TRAINING COMPLETE" in log_text
        or "PARALLEL CPU TRAINING COMPLETE" in log_text
    )
    if has_stats and running:
        should_pull_stats = True

    # Only write finished GPU stats into the main output dir when CPU is idle
    pulled_stats = False
    if should_pull_stats:
        if local_running:
            pulled_stats = _try_pull_file(env, "training_stats.json", dest_dir=GPU_LIVE_DIR)
        else:
            pulled_stats = _try_pull_file(env, "training_stats.json", dest_dir=OUTPUT_DIR)
    if has_stats and not running and not local_running:
        _try_pull_file(env, "last_run_params.json", dest_dir=OUTPUT_DIR)
        _try_pull_file(env, "dqn_policy.pt", dest_dir=OUTPUT_DIR)

    parsed = _parse_progress(log_text)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gpu_running = bool(running)

    def _base_flags(**extra):
        return {
            "ok": True,
            "running": bool(gpu_running or local_running),
            "gpu_running": gpu_running,
            "cpu_running": local_running,
            "local": local_running,
            "gpu_live_dir": local_running,
            "pulled_training_stats": bool(pulled_stats and not local_running),
            **extra,
        }

    if remote_progress and (remote_progress.get("series") or remote_progress.get("summary")):
        payload = _base_flags(
            pulled_progress=True,
            checkpoints=remote_progress.get("checkpoints") or [],
            tqdm_pct=remote_progress.get("tqdm_pct"),
            tqdm_current=remote_progress.get("tqdm_current"),
            tqdm_total=remote_progress.get("tqdm_total"),
            series=remote_progress.get("series") or {},
            summary=remote_progress.get("summary") or {},
            train_mode=remote_progress.get("train_mode")
            or (remote_progress.get("summary") or {}).get("train_mode"),
            train_device=remote_progress.get("train_device")
            or (remote_progress.get("summary") or {}).get("train_device")
            or "gpu",
        )
        if not running:
            payload["gpu_running"] = False
            if not local_running:
                payload["running"] = False
            payload["summary"] = dict(payload.get("summary") or {})
            if payload["summary"].get("pct") is None and payload.get("tqdm_pct") is not None:
                payload["summary"]["pct"] = payload["tqdm_pct"]
        _write_progress_payload(progress_path, payload)
        if not local_running:
            _write_progress_payload(GPU_PROGRESS_PATH, payload)
        return payload

    payload = _base_flags(
        pulled_progress=False,
        **parsed,
        train_device="gpu",
    )
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

    _write_progress_payload(progress_path, payload)
    if not local_running:
        _write_progress_payload(GPU_PROGRESS_PATH, payload)
    return payload
