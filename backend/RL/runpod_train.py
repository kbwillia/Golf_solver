#!/usr/bin/env python3
"""One-command RunPod RL training for Golf_solver.

Like conversation-insights-hub's gpu_session_start.py: run this from your PC,
and it handles SSH refresh + remote setup + train.

Usage (from repo root):
  python backend/RL/runpod_train.py
  python backend/RL/runpod_train.py --games 50000
  python backend/RL/runpod_train.py --detach   # launch only, no wait/pull
  python backend/RL/runpod_train.py --status
  python backend/RL/runpod_train.py --pull
  python backend/RL/runpod_train.py --follow
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
LOCAL_OUTPUT = Path(__file__).resolve().parent / "output"
LOCAL_TRAIN = Path(__file__).resolve().parent / "train.py"


def load_dotenv() -> dict[str, str]:
    vals: dict[str, str] = {}
    if not ENV_PATH.exists():
        return vals
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        vals[k] = v
        os.environ.setdefault(k, v)
    return vals


def upsert_env(key: str, value: str) -> None:
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        if re.match(rf"^\s*{re.escape(key)}\s*=", line):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"# Auto-updated by runpod_train.py")
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.environ[key] = value


def api_get_pod(api_key: str, pod_id: str) -> dict:
    req = urllib.request.Request(
        f"https://rest.runpod.io/v1/pods/{pod_id}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def refresh_ssh(env: dict[str, str]) -> tuple[str, str, int]:
    """Return (pod_id, ssh_host, ssh_port). Prefer direct TCP (needed for scp)."""
    api_key = (env.get("RUNPOD_API_KEY") or "").strip()
    pod_id = (env.get("RUNPOD_POD_ID") or "").strip()
    if not api_key or not pod_id:
        raise SystemExit("Set RUNPOD_API_KEY and RUNPOD_POD_ID in .env")

    pod = api_get_pod(api_key, pod_id)
    status = str(pod.get("desiredStatus") or pod.get("status") or "").upper()

    runtime = pod.get("runtime") or {}
    ports = runtime.get("ports") or []
    ssh_host = None
    ssh_port = None
    for p in ports:
        ptype = str(p.get("type") or "").lower()
        private = p.get("private")
        try:
            private_i = int(private) if private is not None else -1
        except (TypeError, ValueError):
            private_i = -1
        # Direct TCP SSH: private 22, or any tcp with a public port when named ssh
        if private_i == 22 and (ptype in {"tcp", ""} or "tcp" in ptype):
            ssh_host = p.get("ip")
            try:
                ssh_port = int(p.get("public"))
            except (TypeError, ValueError):
                ssh_port = None
            if ssh_host and ssh_port:
                break

    # Fallback: values already in .env (Connect tab "SSH over exposed TCP")
    if not ssh_host or not ssh_port:
        ssh_host = (env.get("RUNPOD_SSH_HOST") or "").strip() or None
        try:
            ssh_port = int(env.get("RUNPOD_SSH_PORT") or 0) or None
        except ValueError:
            ssh_port = None
        if ssh_host and ssh_port:
            print(
                f"API had no SSH mapping yet; using .env {ssh_host}:{ssh_port} "
                f"(status={status})"
            )

    if not ssh_host or not ssh_port:
        raise SystemExit(
            f"Pod {pod_id} has no SSH port mapping yet (status={status}).\n"
            "In RunPod Connect tab, copy 'SSH over exposed TCP' into .env:\n"
            "  RUNPOD_SSH_HOST=...\n"
            "  RUNPOD_SSH_PORT=...\n"
            "  RUNPOD_SSH_USER=root\n"
            "Also set RUNPOD_SSH_GATEWAY_USER from the ssh.runpod.io line "
            "(user before @), then retry."
        )

    upsert_env("RUNPOD_SSH_HOST", str(ssh_host))
    upsert_env("RUNPOD_SSH_PORT", str(ssh_port))
    # Keep gateway user if present (ssh only; scp needs TCP above)
    gw = (env.get("RUNPOD_SSH_GATEWAY_USER") or "").strip()
    if gw:
        upsert_env("RUNPOD_SSH_GATEWAY_USER", gw)
    print(f"Pod {pod_id} SSH -> root@{ssh_host}:{ssh_port} ({status})")
    return pod_id, str(ssh_host), int(ssh_port)


def ssh_base(env: dict[str, str], host: str, port: int) -> list[str]:
    """Direct TCP SSH (supports scp). Always use root@host -p port."""
    key = env.get("RUNPOD_SSH_KEY_PATH") or str(Path.home() / ".ssh" / "id_ed25519")
    return [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=20",
        "-i",
        key,
        "-p",
        str(port),
        f"root@{host}",
    ]


def scp_base(env: dict[str, str], host: str, port: int) -> tuple[list[str], str]:
    key = env.get("RUNPOD_SSH_KEY_PATH") or str(Path.home() / ".ssh" / "id_ed25519")
    return [
        "scp",
        "-o",
        "StrictHostKeyChecking=no",
        "-i",
        key,
        "-P",
        str(port),
    ], f"root@{host}"


def remote_train_script(params: dict | None = None) -> str:
    # Single remote bootstrap+train. Uses /workspace so it survives container restarts.
    # Use a raw string (not an f-string) so nested quotes/braces in the remote
    # script do not break Python parsing on Windows.
    params = params or {}
    num_games = int(params.get("num_games", 2000))
    learning_rate = float(params.get("learning_rate", 0.1))
    discount_factor = float(params.get("discount_factor", 0.9))
    epsilon = float(params.get("epsilon", 0.2))
    epsilon_decay_factor = float(params.get("epsilon_decay_factor", 0.995))
    n_bootstrap_games = int(params.get("n_bootstrap_games", min(250, num_games // 8)))
    use_imitation = 1 if params.get("use_imitation_learning", True) else 0
    epsilon_decay_interval = int(params.get("epsilon_decay_interval", 100))
    progress_report_interval = int(
        params.get("progress_report_interval", max(100, num_games // 20))
    )
    opponent_type = str(params.get("opponent_type", "ev_ai"))
    use_reward_shaping = 1 if params.get("use_reward_shaping", True) else 0
    shape_step = float(params.get("shape_step", 0.05))
    shape_pair = float(params.get("shape_pair", 1.5))
    shape_high_keep = float(params.get("shape_high_keep", -0.8))
    shape_low_keep = float(params.get("shape_low_keep", 0.3))
    shape_midhigh_keep = float(params.get("shape_midhigh_keep", -0.4))
    shape_flip = float(params.get("shape_flip", 0.1))
    train_device = str(params.get("train_device", "gpu")).lower().strip()
    if train_device not in ("gpu", "cpu"):
        train_device = "gpu"
    batch_size = int(params.get("batch_size", 512))
    hidden_size = int(params.get("hidden_size", 256))
    train_steps_per_game = int(params.get("train_steps_per_game", 16))
    num_workers = int(params.get("num_workers") or (os.cpu_count() or 8))

    script = r'''#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "=== CUDA check ==="
nvidia-smi -L
python - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA not available on this pod"
print("torch", torch.__version__, "device", torch.cuda.get_device_name(0))
PY

echo "=== Repo ==="
cd /workspace
# Skip git sync when uploaded overrides are present — avoids dirty-tree merge aborts
if [ -f /workspace/dqn_train.py.fixed ] || [ -f /workspace/train.py.fixed ]; then
  echo "Using uploaded trainer overrides; skipping git pull"
  if [ ! -d /workspace/Golf_solver/backend/RL ]; then
    git clone https://github.com/kbwillia/Golf_solver.git || true
  fi
  cd /workspace/Golf_solver || exit 1
else
  if [ -d Golf_solver/.git ]; then
    cd Golf_solver
    git stash push -u -m "runpod-pre-pull" >/dev/null 2>&1 || true
    git fetch --all >/dev/null 2>&1 || true
    git checkout Jagjit >/dev/null 2>&1 || git checkout main >/dev/null 2>&1 || true
    git pull >/dev/null 2>&1 || true
  else
    git clone https://github.com/kbwillia/Golf_solver.git || true
    cd Golf_solver || exit 1
    git checkout Jagjit >/dev/null 2>&1 || git checkout main >/dev/null 2>&1 || true
  fi
fi

echo "=== Venv ==="
if [ ! -x /workspace/venv/bin/python ]; then
  python3 -m venv /workspace/venv --system-site-packages || python -m venv /workspace/venv --system-site-packages
fi
# shellcheck disable=SC1091
source /workspace/venv/bin/activate
pip install -q --upgrade pip || true
pip install -q numpy pandas tqdm scipy python-dotenv || true
# Torch usually comes from the RunPod image via --system-site-packages
python - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA not available on this pod"
print("torch", torch.__version__, "device", torch.cuda.get_device_name(0))
PY

echo "=== Local overrides (if uploaded) ==="
if [ -f /workspace/train.py.fixed ]; then
  cp /workspace/train.py.fixed /workspace/Golf_solver/backend/RL/train.py
fi
if [ -f /workspace/agents.py.fixed ]; then
  cp /workspace/agents.py.fixed /workspace/Golf_solver/backend/agents.py
fi
if [ -f /workspace/dqn_train.py.fixed ]; then
  cp /workspace/dqn_train.py.fixed /workspace/Golf_solver/backend/RL/dqn_train.py
fi
if [ -f /workspace/parallel_train.py.fixed ]; then
  cp /workspace/parallel_train.py.fixed /workspace/Golf_solver/backend/RL/parallel_train.py
fi
if [ -f /workspace/progress_io.py.fixed ]; then
  cp /workspace/progress_io.py.fixed /workspace/Golf_solver/backend/RL/progress_io.py
fi

echo "=== Stub supabase for headless RL ==="
cat > /workspace/Golf_solver/backend/data_upset.py <<'PY'
# Stub for RunPod RL training - no Supabase uploads.

def upload_game_state(*args, **kwargs):
    return None

def upload_chatbot_message(*args, **kwargs):
    return None

def upload_llm_call_info(*args, **kwargs):
    return None
PY

# Tiny launcher — hyperparameters come from env
cat > /workspace/Golf_solver/backend/RL/run_remote_train.py <<'PY'
import json
import os
import numpy as np

def env_float(key, default):
    return float(os.environ.get(key, str(default)))

def env_int(key, default):
    return int(os.environ.get(key, str(default)))

num_games = env_int("NUM_GAMES", 2000)
learning_rate = env_float("LEARNING_RATE", 0.1)
discount_factor = env_float("DISCOUNT_FACTOR", 0.9)
epsilon = env_float("EPSILON", 0.2)
epsilon_decay_factor = env_float("EPSILON_DECAY_FACTOR", 0.995)
n_bootstrap_games = env_int("N_BOOTSTRAP_GAMES", min(250, num_games // 8))
use_imitation_learning = os.environ.get("USE_IMITATION", "1") != "0"
epsilon_decay_interval = env_int("EPSILON_DECAY_INTERVAL", 100)
progress_report_interval = env_int("PROGRESS_REPORT_INTERVAL", max(100, num_games // 20))
opponent_type = os.environ.get("OPPONENT_TYPE", "ev_ai")
use_reward_shaping = os.environ.get("USE_REWARD_SHAPING", "1") != "0"
shape_step = env_float("SHAPE_STEP", 0.05)
shape_pair = env_float("SHAPE_PAIR", 1.5)
shape_high_keep = env_float("SHAPE_HIGH_KEEP", -0.8)
shape_low_keep = env_float("SHAPE_LOW_KEEP", 0.3)
shape_midhigh_keep = env_float("SHAPE_MIDHIGH_KEEP", -0.4)
shape_flip = env_float("SHAPE_FLIP", 0.1)
train_device = os.environ.get("TRAIN_DEVICE", "gpu").lower().strip()
batch_size = env_int("BATCH_SIZE", 512)
hidden_size = env_int("HIDDEN_SIZE", 256)
train_steps_per_game = env_int("TRAIN_STEPS", 16)
num_workers = env_int("NUM_WORKERS", 8)

params = {
    "num_games": num_games,
    "learning_rate": learning_rate,
    "discount_factor": discount_factor,
    "epsilon": epsilon,
    "epsilon_decay_factor": epsilon_decay_factor,
    "n_bootstrap_games": n_bootstrap_games,
    "use_imitation_learning": use_imitation_learning,
    "epsilon_decay_interval": epsilon_decay_interval,
    "progress_report_interval": progress_report_interval,
    "opponent_type": opponent_type,
    "use_reward_shaping": use_reward_shaping,
    "shape_step": shape_step,
    "shape_pair": shape_pair,
    "shape_high_keep": shape_high_keep,
    "shape_low_keep": shape_low_keep,
    "shape_midhigh_keep": shape_midhigh_keep,
    "shape_flip": shape_flip,
    "train_device": train_device,
    "train_mode": "dqn_parallel" if train_device == "gpu" else "tabular_parallel",
    "batch_size": batch_size,
    "hidden_size": hidden_size,
    "train_steps_per_game": train_steps_per_game,
    "num_workers": num_workers,
}
print("Starting remote training with params:")
print(json.dumps(params, indent=2))
os.makedirs("output", exist_ok=True)
with open("output/last_run_params.json", "w", encoding="utf-8") as f:
    json.dump(params, f, indent=2)

if train_device == "gpu":
    from dqn_train import train_dqn_agent
    dqn_lr = learning_rate if learning_rate < 0.05 else 0.001
    agent, training_stats = train_dqn_agent(
        num_games=num_games,
        opponent_type=opponent_type,
        verbose=True,
        use_gpu=True,
        learning_rate=dqn_lr,
        discount_factor=discount_factor,
        epsilon=epsilon,
        epsilon_decay_factor=epsilon_decay_factor,
        n_bootstrap_games=n_bootstrap_games,
        use_imitation_learning=use_imitation_learning,
        epsilon_decay_interval=epsilon_decay_interval,
        progress_report_interval=progress_report_interval,
        batch_size=batch_size,
        hidden_size=hidden_size,
        train_steps_per_game=train_steps_per_game,
        num_workers=num_workers,
        use_reward_shaping=use_reward_shaping,
        shape_step=shape_step,
        shape_pair=shape_pair,
        shape_high_keep=shape_high_keep,
        shape_low_keep=shape_low_keep,
        shape_midhigh_keep=shape_midhigh_keep,
        shape_flip=shape_flip,
    )
    print("TRAINING COMPLETE!")
    print(f"Params: {agent.param_count()}")
else:
    from parallel_train import train_qlearning_agent_parallel
    agent, training_stats = train_qlearning_agent_parallel(
        num_games=num_games,
        opponent_type=opponent_type,
        verbose=True,
        num_workers=num_workers,
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        epsilon_decay_factor=epsilon_decay_factor,
        n_bootstrap_games=n_bootstrap_games,
        use_imitation_learning=use_imitation_learning,
        epsilon_decay_interval=epsilon_decay_interval,
        progress_report_interval=progress_report_interval,
        use_reward_shaping=use_reward_shaping,
        shape_step=shape_step,
        shape_pair=shape_pair,
        shape_high_keep=shape_high_keep,
        shape_low_keep=shape_low_keep,
        shape_midhigh_keep=shape_midhigh_keep,
        shape_flip=shape_flip,
    )
    print("TRAINING COMPLETE!")
    print(f"States: {len(agent.q_table)}")

print(f"Win rate: {training_stats['wins']/max(1, training_stats['games_played']):.2%}")
print(f"Average score: {np.mean(training_stats['scores']):.2f}")
PY

mkdir -p /workspace/Golf_solver/backend/RL/output /workspace/logs
pkill -f "python -u run_remote_train.py" 2>/dev/null || true
pkill -f "python -u dqn_train.py" 2>/dev/null || true
pkill -f "python -u train.py" 2>/dev/null || true
cd /workspace/Golf_solver/backend/RL
# Clear stale progress so the UI does not show an old finished job as live
rm -f /workspace/Golf_solver/backend/RL/output/training_progress.json
export NUM_GAMES=__NUM_GAMES__
export LEARNING_RATE=__LEARNING_RATE__
export DISCOUNT_FACTOR=__DISCOUNT_FACTOR__
export EPSILON=__EPSILON__
export EPSILON_DECAY_FACTOR=__EPSILON_DECAY_FACTOR__
export N_BOOTSTRAP_GAMES=__N_BOOTSTRAP_GAMES__
export USE_IMITATION=__USE_IMITATION__
export EPSILON_DECAY_INTERVAL=__EPSILON_DECAY_INTERVAL__
export PROGRESS_REPORT_INTERVAL=__PROGRESS_REPORT_INTERVAL__
export OPPONENT_TYPE=__OPPONENT_TYPE__
export USE_REWARD_SHAPING=__USE_REWARD_SHAPING__
export SHAPE_STEP=__SHAPE_STEP__
export SHAPE_PAIR=__SHAPE_PAIR__
export SHAPE_HIGH_KEEP=__SHAPE_HIGH_KEEP__
export SHAPE_LOW_KEEP=__SHAPE_LOW_KEEP__
export SHAPE_MIDHIGH_KEEP=__SHAPE_MIDHIGH_KEEP__
export SHAPE_FLIP=__SHAPE_FLIP__
export TRAIN_DEVICE=__TRAIN_DEVICE__
export BATCH_SIZE=__BATCH_SIZE__
export HIDDEN_SIZE=__HIDDEN_SIZE__
export TRAIN_STEPS=__TRAIN_STEPS__
export NUM_WORKERS=__NUM_WORKERS__
PYTHON_BIN=/workspace/venv/bin/python
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN=$(command -v python3 || command -v python)
fi
nohup env \
  NUM_GAMES="$NUM_GAMES" \
  LEARNING_RATE="$LEARNING_RATE" \
  DISCOUNT_FACTOR="$DISCOUNT_FACTOR" \
  EPSILON="$EPSILON" \
  EPSILON_DECAY_FACTOR="$EPSILON_DECAY_FACTOR" \
  N_BOOTSTRAP_GAMES="$N_BOOTSTRAP_GAMES" \
  USE_IMITATION="$USE_IMITATION" \
  EPSILON_DECAY_INTERVAL="$EPSILON_DECAY_INTERVAL" \
  PROGRESS_REPORT_INTERVAL="$PROGRESS_REPORT_INTERVAL" \
  OPPONENT_TYPE="$OPPONENT_TYPE" \
  USE_REWARD_SHAPING="$USE_REWARD_SHAPING" \
  SHAPE_STEP="$SHAPE_STEP" \
  SHAPE_PAIR="$SHAPE_PAIR" \
  SHAPE_HIGH_KEEP="$SHAPE_HIGH_KEEP" \
  SHAPE_LOW_KEEP="$SHAPE_LOW_KEEP" \
  SHAPE_MIDHIGH_KEEP="$SHAPE_MIDHIGH_KEEP" \
  SHAPE_FLIP="$SHAPE_FLIP" \
  TRAIN_DEVICE="$TRAIN_DEVICE" \
  BATCH_SIZE="$BATCH_SIZE" \
  HIDDEN_SIZE="$HIDDEN_SIZE" \
  TRAIN_STEPS="$TRAIN_STEPS" \
  NUM_WORKERS="$NUM_WORKERS" \
  "$PYTHON_BIN" -u run_remote_train.py > /workspace/logs/train.log 2>&1 &
echo $! > /workspace/logs/train.pid
sleep 8
echo "PID $(cat /workspace/logs/train.pid) NUM_GAMES=$NUM_GAMES TRAIN_DEVICE=$TRAIN_DEVICE PYTHON=$PYTHON_BIN"
tail -n 40 /workspace/logs/train.log || true
if ! ps -p "$(cat /workspace/logs/train.pid)" >/dev/null 2>&1; then
  if grep -Eq "TRAINING COMPLETE|DQN TRAINING COMPLETE|PARALLEL CPU TRAINING COMPLETE|Starting remote training" /workspace/logs/train.log 2>/dev/null; then
    echo "=== TRAIN FINISHED OR STARTED (process already exited) ==="
  else
    echo "=== TRAIN DIED IMMEDIATELY ==="
    tail -n 80 /workspace/logs/train.log || true
    exit 1
  fi
else
  ps -p "$(cat /workspace/logs/train.pid)" -o pid,etime,cmd || true
fi
echo "=== TRAIN LAUNCHED ==="
'''
    return (
        script.replace("__NUM_GAMES__", str(num_games))
        .replace("__LEARNING_RATE__", str(learning_rate))
        .replace("__DISCOUNT_FACTOR__", str(discount_factor))
        .replace("__EPSILON__", str(epsilon))
        .replace("__EPSILON_DECAY_FACTOR__", str(epsilon_decay_factor))
        .replace("__N_BOOTSTRAP_GAMES__", str(n_bootstrap_games))
        .replace("__USE_IMITATION__", str(use_imitation))
        .replace("__EPSILON_DECAY_INTERVAL__", str(epsilon_decay_interval))
        .replace("__PROGRESS_REPORT_INTERVAL__", str(progress_report_interval))
        .replace("__OPPONENT_TYPE__", opponent_type)
        .replace("__USE_REWARD_SHAPING__", str(use_reward_shaping))
        .replace("__SHAPE_STEP__", str(shape_step))
        .replace("__SHAPE_PAIR__", str(shape_pair))
        .replace("__SHAPE_HIGH_KEEP__", str(shape_high_keep))
        .replace("__SHAPE_LOW_KEEP__", str(shape_low_keep))
        .replace("__SHAPE_MIDHIGH_KEEP__", str(shape_midhigh_keep))
        .replace("__SHAPE_FLIP__", str(shape_flip))
        .replace("__TRAIN_DEVICE__", train_device)
        .replace("__BATCH_SIZE__", str(batch_size))
        .replace("__HIDDEN_SIZE__", str(hidden_size))
        .replace("__TRAIN_STEPS__", str(train_steps_per_game))
        .replace("__NUM_WORKERS__", str(num_workers))
    )


def remote_is_running(env: dict[str, str], host: str, port: int) -> bool:
    """True if the remote train PID is still alive."""
    check = r"""
if [ -f /workspace/logs/train.pid ] && ps -p $(cat /workspace/logs/train.pid) >/dev/null 2>&1; then
  echo RUNNING
else
  echo DONE
fi
"""
    out = subprocess.check_output(
        ssh_base(env, host, port) + ["bash", "-lc", check],
        text=True,
    )
    return "RUNNING" in out


def remote_log_tail(env: dict[str, str], host: str, port: int, n: int = 3) -> str:
    cmd = f"tail -n {n} /workspace/logs/train.log 2>/dev/null || true"
    try:
        return subprocess.check_output(
            ssh_base(env, host, port) + ["bash", "-lc", cmd],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def cmd_wait(env: dict[str, str], host: str, port: int, poll_s: float = 5.0) -> None:
    """Block until remote training finishes; print progress and pull live stats."""
    print("Waiting for remote training to finish...")
    time.sleep(2)
    last_shown = ""
    pull_every = 3  # pull training_stats.json every N polls
    polls = 0
    while remote_is_running(env, host, port):
        snippet = remote_log_tail(env, host, port, n=2)
        progress_lines = [
            ln for ln in snippet.splitlines()
            if "Game " in ln or "TRAINING COMPLETE" in ln or "Win rate" in ln
        ]
        show = progress_lines[-1] if progress_lines else snippet.splitlines()[-1] if snippet else ""
        if show and show != last_shown:
            show = show.split("\r")[-1].strip()
            if show:
                print(show)
                last_shown = show
        polls += 1
        if polls % pull_every == 0:
            try:
                # Prefer full helper (writes training_progress.json + pulls stats)
                sys.path.insert(0, str(ROOT / "backend"))
                from rl_live_sync import sync_live_progress
                live = sync_live_progress()
                if live.get("summary"):
                    s = live["summary"]
                    print(
                        f"  [viz sync] {s.get('games_played')}/{s.get('games_total')} "
                        f"({s.get('pct')}%) avg={s.get('avg_score')} states={s.get('final_states')}"
                    )
            except Exception as e:
                print(f"  [viz sync] skipped: {e}")
        time.sleep(poll_s)
    print("Remote training finished.")


def cmd_train(
    env: dict[str, str],
    host: str,
    port: int,
    games: int,
    *,
    wait_and_pull: bool = True,
) -> None:
    # Upload local train.py (has the stub-agent fix) then run remote bootstrap.
    scp_cmd, remote = scp_base(env, host, port)
    if LOCAL_TRAIN.exists():
        subprocess.check_call(
            scp_cmd + [str(LOCAL_TRAIN), f"{remote}:/workspace/train.py.fixed"]
        )
        print("Uploaded local train.py")

    script = remote_train_script({"num_games": games})
    # Write remote script via stdin to avoid Windows quoting hell
    ssh = ssh_base(env, host, port)
    proc = subprocess.run(
        ssh + ["bash", "-s"],
        input=script.encode("utf-8"),
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"Remote train failed with code {proc.returncode}")
    print(f"\nTraining launched ({games} games).")

    if not wait_and_pull:
        print("  Status:  python backend/RL/runpod_train.py --status")
        print("  Follow:  python backend/RL/runpod_train.py --follow")
        print("  Pull:    python backend/RL/runpod_train.py --pull")
        return

    cmd_wait(env, host, port)
    print("Pulling results...")
    cmd_pull(env, host, port)


def cmd_status(env: dict[str, str], host: str, port: int) -> None:
    remote = r"""
if [ -f /workspace/logs/train.pid ] && ps -p $(cat /workspace/logs/train.pid) >/dev/null 2>&1; then
  echo RUNNING
  ps -p $(cat /workspace/logs/train.pid) -o pid,etime,cmd
else
  echo DONE_OR_IDLE
fi
echo --- last log lines ---
tail -n 40 /workspace/logs/train.log 2>/dev/null || echo "(no log yet)"
echo --- outputs ---
ls -lh /workspace/Golf_solver/backend/RL/output/ 2>/dev/null || true
"""
    subprocess.check_call(ssh_base(env, host, port) + ["bash", "-lc", remote])


def cmd_follow(env: dict[str, str], host: str, port: int) -> None:
    subprocess.check_call(
        ssh_base(env, host, port) + ["bash", "-lc", "tail -n 50 -f /workspace/logs/train.log"]
    )


def cmd_pull(env: dict[str, str], host: str, port: int) -> None:
    LOCAL_OUTPUT.mkdir(parents=True, exist_ok=True)
    scp_cmd, remote = scp_base(env, host, port)
    remote_files = [
        f"{remote}:/workspace/Golf_solver/backend/RL/output/qtable_train.csv",
        f"{remote}:/workspace/Golf_solver/backend/RL/output/trajectory_train.csv",
        f"{remote}:/workspace/Golf_solver/backend/RL/output/training_stats.json",
    ]
    # training_stats.json may be missing on older runs — pull what exists
    for remote_path in remote_files:
        try:
            subprocess.check_call(scp_cmd + [remote_path, str(LOCAL_OUTPUT)])
        except subprocess.CalledProcessError:
            name = remote_path.rsplit("/", 1)[-1]
            print(f"Skipped missing remote file: {name}")
    print(f"Downloaded results to {LOCAL_OUTPUT}")


def main() -> None:
    parser = argparse.ArgumentParser(description="One-command Golf RL training on RunPod")
    parser.add_argument("--games", type=int, default=2000, help="num_games for train.py")
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Launch training and exit (skip wait + auto-pull)",
    )
    parser.add_argument("--status", action="store_true", help="Show remote train status/log")
    parser.add_argument("--follow", action="store_true", help="Tail remote train.log")
    parser.add_argument("--pull", action="store_true", help="Download Q-table + trajectory")
    args = parser.parse_args()

    env = load_dotenv()
    _, host, port = refresh_ssh(env)
    env = load_dotenv()  # pick up refreshed host/port

    if args.status:
        cmd_status(env, host, port)
        return
    if args.follow:
        cmd_follow(env, host, port)
        return
    if args.pull:
        cmd_pull(env, host, port)
        return

    cmd_train(env, host, port, args.games, wait_and_pull=not args.detach)


if __name__ == "__main__":
    main()
