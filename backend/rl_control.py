"""Frontend-facing RL training controls (local CPU parallel / RunPod GPU DQN)."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
RL_DIR = BACKEND_DIR / "RL"
OUTPUT_DIR = RL_DIR / "output"
PARAMS_PATH = OUTPUT_DIR / "ui_train_params.json"
LOCAL_TRAIN = RL_DIR / "train.py"
LOCAL_AGENTS = BACKEND_DIR / "agents.py"
LOCAL_PID_PATH = OUTPUT_DIR / "local_train.pid"
LOCAL_LOG_PATH = OUTPUT_DIR / "local_train.log"
PARALLEL_TRAIN = RL_DIR / "parallel_train.py"
DQN_TRAIN = RL_DIR / "dqn_train.py"

DEFAULT_PARAMS = {
    "num_games": 300,
    "learning_rate": 0.05,
    "discount_factor": 0.9,
    "epsilon": 0.2,
    "epsilon_decay_factor": 0.995,
    "n_bootstrap_games": 75,
    "use_imitation_learning": True,
    "epsilon_decay_interval": 100,
    "progress_report_interval": 50,
    "opponent_type": "ev_ai",
    # cpu = local parallel tabular Q | gpu = neural DQN (RunPod if remote, else local CUDA)
    "train_device": "cpu",
    # Sweep 2026-07-28: workers=1 in-process + chunk=16 + replay=4 ~61 gps on large Q
    "num_workers": 1,
    "chunk_size": 16,
    "batch_size": 512,
    "hidden_size": 128,
    "train_steps_per_game": 8,
    "n_step": 3,
    "replay_per_game": 4,
    "replay_capacity": 2000,
    "exploration_beta": 0.5,
    # Reward shaping — turn off (or zero weights) for unbiased / solve-mode runs
    "use_reward_shaping": True,
    "shape_step": 0.05,
    "shape_pair": 1.5,
    "shape_high_keep": -0.8,
    "shape_low_keep": 0.3,
    "shape_midhigh_keep": -0.4,
    "shape_flip": 0.1,
    # I/O / safety (CPU parallel trainer)
    "save_trajectories": True,
    "traj_flush_every": 100,
    "q_checkpoint_every": 50_000,
    "stats_stride": 100,
    "stats_max_points": 5_000,
    "coverage_every_n_reports": 5,
    "offline_human_bc_every": 100,
    "offline_human_bc_batch": 32,
    "use_soft_prior": True,
    "soft_prior_max_round": 2,
    "soft_prior_scale": 5.0,
}

# Device-specific training defaults (CPU tabular Q vs GPU neural DQN)
DEVICE_PRESETS: dict[str, dict[str, Any]] = {
    "cpu": {
        "num_workers": 1,
        "chunk_size": 16,
        "learning_rate": 0.05,
        "n_bootstrap_games": 75,
        "progress_report_interval": 50,
        "num_games": 300,
        "epsilon": 0.2,
        "epsilon_decay_factor": 0.995,
        "epsilon_decay_interval": 100,
        "discount_factor": 0.9,
        "use_imitation_learning": True,
        "use_reward_shaping": True,
        "opponent_type": "ev_ai",
        "n_step": 3,
        "replay_per_game": 4,
        "exploration_beta": 0.5,
        "save_trajectories": True,
        "traj_flush_every": 100,
        "q_checkpoint_every": 50_000,
        "stats_stride": 100,
        "stats_max_points": 5_000,
        "coverage_every_n_reports": 5,
        "offline_human_bc_every": 100,
        "offline_human_bc_batch": 32,
        "use_soft_prior": True,
        "soft_prior_max_round": 2,
        "soft_prior_scale": 5.0,
    },
    "gpu": {
        "num_workers": 8,
        "learning_rate": 0.001,
        "n_bootstrap_games": 400,
        "progress_report_interval": 50,
        "num_games": 1000,
        "batch_size": 512,
        "hidden_size": 128,
        "train_steps_per_game": 8,
        "epsilon": 0.2,
        "epsilon_decay_factor": 0.995,
        "epsilon_decay_interval": 100,
        "discount_factor": 0.9,
        "use_imitation_learning": True,
        "use_reward_shaping": True,
        "opponent_type": "ev_ai",
    },
}

_PRESET_KEYS = (
    "num_workers",
    "chunk_size",
    "learning_rate",
    "n_bootstrap_games",
    "progress_report_interval",
    "num_games",
    "batch_size",
    "hidden_size",
    "train_steps_per_game",
    "n_step",
    "replay_per_game",
    "replay_capacity",
    "exploration_beta",
    "epsilon",
    "epsilon_decay_factor",
    "epsilon_decay_interval",
    "discount_factor",
    "use_imitation_learning",
    "use_reward_shaping",
    "opponent_type",
    "shape_step",
    "shape_pair",
    "shape_high_keep",
    "shape_low_keep",
    "shape_midhigh_keep",
    "shape_flip",
    "save_trajectories",
    "traj_flush_every",
    "q_checkpoint_every",
    "stats_stride",
    "stats_max_points",
    "coverage_every_n_reports",
    "offline_human_bc_every",
    "offline_human_bc_batch",
    "use_soft_prior",
    "soft_prior_max_round",
    "soft_prior_scale",
)

_launch_lock = None
_launch_state: dict[str, Any] = {"busy": False, "error": None, "started_at": None}


def _ensure_rl_import() -> None:
    rl_path = str(RL_DIR)
    if rl_path not in sys.path:
        sys.path.insert(0, rl_path)


def _default_device_presets() -> dict[str, dict[str, Any]]:
    return {
        "cpu": dict(DEVICE_PRESETS["cpu"]),
        "gpu": dict(DEVICE_PRESETS["gpu"]),
    }


def _merge_device_presets(saved: Any) -> dict[str, dict[str, Any]]:
    presets = _default_device_presets()
    if not isinstance(saved, dict):
        return presets
    for device in ("cpu", "gpu"):
        block = saved.get(device)
        if isinstance(block, dict):
            presets[device].update({k: block[k] for k in _PRESET_KEYS if k in block})
    return presets


def load_saved_params() -> dict[str, Any]:
    if PARAMS_PATH.exists():
        try:
            data = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
            merged = dict(DEFAULT_PARAMS)
            merged.update({k: data[k] for k in DEFAULT_PARAMS if k in data})
            # Allow forward-compatible keys already in DEFAULT
            for k, v in data.items():
                if k in merged:
                    merged[k] = v
            merged["device_presets"] = _merge_device_presets(data.get("device_presets"))
            return merged
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    out = dict(DEFAULT_PARAMS)
    out["device_presets"] = _default_device_presets()
    return out


def save_params(params: dict[str, Any]) -> dict[str, Any]:
    incoming = dict(params or {})
    existing = load_saved_params()
    presets = _merge_device_presets(incoming.get("device_presets") or existing.get("device_presets"))

    merged = dict(DEFAULT_PARAMS)
    merged.update({k: existing[k] for k in DEFAULT_PARAMS if k in existing})
    merged.update({k: incoming[k] for k in DEFAULT_PARAMS if k in incoming})

    merged["num_games"] = int(merged["num_games"])
    merged["learning_rate"] = float(merged["learning_rate"])
    merged["discount_factor"] = float(merged["discount_factor"])
    merged["epsilon"] = float(merged["epsilon"])
    merged["epsilon_decay_factor"] = float(merged["epsilon_decay_factor"])
    merged["n_bootstrap_games"] = int(merged["n_bootstrap_games"])
    merged["use_imitation_learning"] = bool(merged["use_imitation_learning"])
    merged["epsilon_decay_interval"] = int(merged["epsilon_decay_interval"])
    merged["progress_report_interval"] = int(merged["progress_report_interval"])
    merged["opponent_type"] = str(merged["opponent_type"] or "ev_ai")
    device = str(merged.get("train_device") or "cpu").lower().strip()
    merged["train_device"] = "gpu" if device in ("gpu", "cuda", "dqn") else "cpu"
    merged["num_workers"] = max(1, int(merged.get("num_workers") or 2))
    merged["chunk_size"] = max(1, int(merged.get("chunk_size") or 16))
    merged["batch_size"] = max(32, int(merged.get("batch_size") or 512))
    merged["hidden_size"] = max(32, int(merged.get("hidden_size") or 128))
    merged["train_steps_per_game"] = max(4, int(merged.get("train_steps_per_game") or 8))
    merged["n_step"] = max(1, int(merged.get("n_step") or 3))
    merged["replay_per_game"] = max(0, int(merged.get("replay_per_game") or 0))
    merged["exploration_beta"] = max(0.0, float(merged.get("exploration_beta") or 0.0))
    merged["replay_capacity"] = max(100, int(merged.get("replay_capacity") or 2000))
    merged["use_reward_shaping"] = bool(merged["use_reward_shaping"])
    for key in (
        "shape_step",
        "shape_pair",
        "shape_high_keep",
        "shape_low_keep",
        "shape_midhigh_keep",
        "shape_flip",
    ):
        merged[key] = float(merged[key])
    merged["save_trajectories"] = bool(merged.get("save_trajectories", True))
    merged["traj_flush_every"] = max(1, int(merged.get("traj_flush_every") or 100))
    merged["q_checkpoint_every"] = max(0, int(merged.get("q_checkpoint_every") or 0))
    merged["stats_stride"] = max(1, int(merged.get("stats_stride") or 100))
    merged["stats_max_points"] = max(100, int(merged.get("stats_max_points") or 5000))
    merged["coverage_every_n_reports"] = max(1, int(merged.get("coverage_every_n_reports") or 5))
    merged["offline_human_bc_every"] = max(0, int(merged.get("offline_human_bc_every") or 0))
    merged["offline_human_bc_batch"] = max(1, int(merged.get("offline_human_bc_batch") or 32))
    merged["use_soft_prior"] = bool(merged.get("use_soft_prior", True))
    merged["soft_prior_max_round"] = max(0, int(merged.get("soft_prior_max_round") or 2))
    merged["soft_prior_scale"] = float(merged.get("soft_prior_scale") or 5.0)

    # Persist current form values into the active device's preset
    active = merged["train_device"]
    presets[active] = {
        **presets.get(active, {}),
        **{k: merged[k] for k in _PRESET_KEYS if k in merged},
    }
    merged["device_presets"] = presets

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PARAMS_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def _connect():
    _ensure_rl_import()
    from runpod_train import load_dotenv, refresh_ssh, ssh_base, scp_base

    env = load_dotenv()
    _, host, port = refresh_ssh(env)
    env = load_dotenv()
    return env, host, port, ssh_base(env, host, port), scp_base(env, host, port)


def _clear_local_pid_file() -> None:
    try:
        LOCAL_PID_PATH.unlink(missing_ok=True)
    except TypeError:
        if LOCAL_PID_PATH.exists():
            try:
                LOCAL_PID_PATH.unlink()
            except OSError:
                pass
    except OSError:
        pass


def _pid_is_our_trainer(pid: int) -> bool:
    """True if pid is alive. Stale pid files are cleared by callers when False.

    We intentionally avoid PowerShell/WMI here — those were multi-second and made
    every /api/rl/sync feel like a 500. Trainer scripts clear the pid file on exit;
    PID-reuse false positives are rare and cleared on the next Stop/Start cycle.
    """
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            return str(pid) in out and "python" in out.lower()
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _local_pid() -> int | None:
    if not LOCAL_PID_PATH.exists():
        return None
    try:
        pid = int(LOCAL_PID_PATH.read_text(encoding="utf-8").strip().splitlines()[0])
    except (OSError, ValueError):
        _clear_local_pid_file()
        return None
    if not _pid_is_our_trainer(pid):
        _clear_local_pid_file()
        return None
    return pid


def _local_elapsed(pid: int) -> str | None:
    try:
        if sys.platform == "win32":
            return None
        import psutil  # optional
        p = psutil.Process(pid)
        secs = time.time() - p.create_time()
        m, s = divmod(int(secs), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    except Exception:
        return None


def _stop_local() -> dict[str, Any]:
    pid = _local_pid()
    if pid is None:
        if LOCAL_PID_PATH.exists():
            try:
                LOCAL_PID_PATH.unlink()
            except OSError:
                pass
        return {"ok": True, "stopped": True, "message": "No local training process"}
    try:
        if sys.platform == "win32":
            subprocess.check_call(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    except Exception as e:
        return {"ok": False, "error": f"Failed to stop local pid {pid}: {e}"}
    _clear_local_pid_file()
    # Mark progress not running
    try:
        progress = OUTPUT_DIR / "training_progress.json"
        if progress.exists():
            data = json.loads(progress.read_text(encoding="utf-8"))
            data["running"] = False
            progress.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass
    return {"ok": True, "stopped": True, "message": f"Stopped local training (pid {pid})"}


def _start_local(merged: dict[str, Any]) -> dict[str, Any]:
    if _local_pid() is not None:
        return {
            "ok": False,
            "error": "Local training already running. Stop it first.",
            "running": True,
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    device = merged.get("train_device", "cpu")
    if device == "gpu":
        script = DQN_TRAIN
        env_extra = {
            "NUM_GAMES": str(merged["num_games"]),
            "USE_GPU": "1",
        }
        mode_msg = "local neural DQN (dev only — prefer RunPod via Device=GPU)"
    else:
        script = PARALLEL_TRAIN
        env_extra = {
            "NUM_GAMES": str(merged["num_games"]),
            "NUM_WORKERS": str(merged["num_workers"]),
        }
        mode_msg = f"local parallel tabular Q ({merged['num_workers']} workers -> Supabase on archive)"

    if not script.exists():
        return {"ok": False, "error": f"Trainer script missing: {script}"}

    env = os.environ.copy()
    env.update(env_extra)
    # Ensure backend imports resolve
    env["PYTHONPATH"] = os.pathsep.join(
        [str(BACKEND_DIR), str(RL_DIR), env.get("PYTHONPATH", "")]
    )

    log_f = open(LOCAL_LOG_PATH, "w", encoding="utf-8")
    creationflags = 0
    if sys.platform == "win32":
        # Keep training in the background — do not spawn a visible console window
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )

    proc = subprocess.Popen(
        [sys.executable, "-u", str(script)],
        cwd=str(RL_DIR),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    LOCAL_PID_PATH.write_text(str(proc.pid), encoding="utf-8")
    return {
        "ok": True,
        "started": True,
        "launching": False,
        "local": True,
        "pid": proc.pid,
        "params": merged,
        "message": f"Started {mode_msg} (pid {proc.pid}).",
    }


def _probe_gpu_status(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Probe RunPod / launch lock without caring about local CPU."""
    params = params or load_saved_params()
    gpu: dict[str, Any] = {
        "running": False,
        "launching": bool(_launch_state.get("busy")),
        "launch_error": _launch_state.get("error"),
        "elapsed": None,
        "remote_params": None,
        "error": None,
        "ok": True,
    }
    # Sync launch lock from disk (survives Flask restarts) + surface errors
    try:
        launch = json.loads((OUTPUT_DIR / "launch_status.json").read_text(encoding="utf-8"))
        if launch.get("error") and not gpu["launch_error"]:
            gpu["launch_error"] = launch.get("error")
        if launch.get("busy") and not _launch_state.get("busy"):
            started_at = float(_launch_state.get("started_at") or 0)
            stale = (not started_at) or (time.time() - started_at > 30)
            if stale and launch.get("stage") in ("starting_remote", "uploading", None):
                launch["busy"] = False
                if not launch.get("error"):
                    launch["error"] = (
                        "Launch interrupted (server restarted or worker died). "
                        "Press Start again."
                    )
                    launch["stage"] = "failed"
                (OUTPUT_DIR / "launch_status.json").write_text(
                    json.dumps(launch, indent=2), encoding="utf-8"
                )
                gpu["launch_error"] = launch.get("error")
        elif launch.get("busy") and _launch_state.get("busy"):
            gpu["running"] = True
            gpu["launching"] = True
    except Exception:
        pass

    # Always probe remote — CPU + GPU can run together, and Device may be set to CPU
    try:
        _env, _host, _port, ssh, _ = _connect()
    except SystemExit as e:
        gpu["ok"] = False
        gpu["error"] = str(e)
        return gpu
    except Exception as e:
        gpu["ok"] = False
        gpu["error"] = str(e)
        return gpu

    remote_cmd = r"""
running=0
etime=""
if [ -f /workspace/logs/train.pid ] && ps -p $(cat /workspace/logs/train.pid) >/dev/null 2>&1; then
  running=1
  etime=$(ps -p $(cat /workspace/logs/train.pid) -o etime= 2>/dev/null | tr -d ' ')
fi
echo "RUNNING=$running"
echo "ETIME=$etime"
if [ -f /workspace/Golf_solver/backend/RL/output/last_run_params.json ]; then
  echo "PARAMS_BEGIN"
  cat /workspace/Golf_solver/backend/RL/output/last_run_params.json
  echo
  echo "PARAMS_END"
fi
"""
    try:
        out = subprocess.check_output(
            ssh + ["bash", "-lc", remote_cmd],
            text=True,
            encoding="utf-8",
            errors="replace",
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception as e:
        gpu["ok"] = False
        gpu["error"] = str(e)
        return gpu

    running = "RUNNING=1" in out
    etime = ""
    for line in out.splitlines():
        if line.startswith("ETIME="):
            etime = line.split("=", 1)[1].strip()

    remote_params = None
    if "PARAMS_BEGIN" in out and "PARAMS_END" in out:
        chunk = out.split("PARAMS_BEGIN", 1)[1].split("PARAMS_END", 1)[0].strip()
        try:
            remote_params = json.loads(chunk)
        except json.JSONDecodeError:
            remote_params = None

    gpu.update({
        "ok": True,
        "running": running or bool(_launch_state.get("busy")),
        "launching": bool(_launch_state.get("busy")),
        "elapsed": etime or None,
        "remote_params": remote_params,
    })
    return gpu


def get_status() -> dict[str, Any]:
    """Status for both devices — CPU and GPU can run concurrently."""
    params = load_saved_params()
    local_pid = _local_pid()
    cpu = {
        "running": local_pid is not None,
        "pid": local_pid,
        "elapsed": _local_elapsed(local_pid) if local_pid else None,
    }
    gpu = _probe_gpu_status(params)

    cpu_running = bool(cpu["running"])
    gpu_running = bool(gpu.get("running") or gpu.get("launching"))
    return {
        "ok": True,
        "running": cpu_running or gpu_running,
        "local": cpu_running,
        "cpu_running": cpu_running,
        "gpu_running": gpu_running,
        "launching": bool(gpu.get("launching")),
        "launch_error": gpu.get("launch_error"),
        "elapsed": gpu.get("elapsed") if gpu_running else cpu.get("elapsed"),
        "pid": local_pid,
        "cpu": cpu,
        "gpu": {
            "running": bool(gpu.get("running")),
            "launching": bool(gpu.get("launching")),
            "elapsed": gpu.get("elapsed"),
            "error": gpu.get("error"),
            "launch_error": gpu.get("launch_error"),
        },
        "params": params,
        "remote_params": gpu.get("remote_params"),
        "defaults": {**DEFAULT_PARAMS, "device_presets": _default_device_presets()},
        "device_presets": params.get("device_presets") or _default_device_presets(),
        "train_device": params.get("train_device", "cpu"),
        "error": (
            gpu.get("error")
            if (not gpu.get("ok", True) and params.get("train_device") == "gpu" and not cpu_running)
            else None
        ),
    }


def _stop_remote() -> dict[str, Any]:
    global _launch_state
    _launch_state["busy"] = False
    try:
        (OUTPUT_DIR / "launch_status.json").write_text(
            json.dumps({"busy": False, "error": None, "stage": "stopped"}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass

    try:
        _env, _host, _port, ssh, _ = _connect()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    remote = """
pkill -f "python -u run_remote_train.py" 2>/dev/null || true
pkill -f "python -u dqn_train.py" 2>/dev/null || true
pkill -f "python -u parallel_train.py" 2>/dev/null || true
pkill -f "python -u train.py" 2>/dev/null || true
sleep 1
rm -f /workspace/logs/train.pid
# Mark progress complete so UI sync does not look "live"
if [ -f /workspace/Golf_solver/backend/RL/output/training_progress.json ]; then
  python3 - <<'PY'
import json, os
p='/workspace/Golf_solver/backend/RL/output/training_progress.json'
try:
    d=json.load(open(p))
    d['running']=False
    json.dump(d, open(p,'w'))
except Exception:
    pass
PY
fi
if pgrep -f "run_remote_train.py" >/dev/null 2>&1; then
  echo STILL_RUNNING
  exit 1
fi
echo STOPPED
"""
    try:
        payload = remote.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        proc = subprocess.run(
            ssh + ["bash", "-s"],
            input=payload,
            capture_output=True,
            timeout=45,
            check=False,
        )
        out = (proc.stdout or b"").decode("utf-8", errors="replace")
        err = (proc.stderr or b"").decode("utf-8", errors="replace")
        if proc.returncode != 0 and "STOPPED" not in out:
            return {
                "ok": False,
                "error": "Failed to stop remote process",
                "detail": (err or out)[-500:],
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "stopped": True, "message": "Stopped RunPod GPU training (or it was already finished)."}


def stop_training(device: str | None = None) -> dict[str, Any]:
    """Stop one device or both. device: cpu | gpu | all | auto (selected train_device)."""
    target = (device or "auto").strip().lower()
    if target == "auto":
        target = str(load_saved_params().get("train_device") or "cpu").lower()
    if target not in ("cpu", "gpu", "all"):
        target = "cpu"

    messages: list[str] = []
    ok = True
    if target in ("cpu", "all"):
        result = _stop_local()
        if not result.get("ok"):
            ok = False
            messages.append(result.get("error") or "CPU stop failed")
        else:
            messages.append(result.get("message") or "Stopped CPU")
    if target in ("gpu", "all"):
        result = _stop_remote()
        if not result.get("ok"):
            ok = False
            messages.append(result.get("error") or "GPU stop failed")
        else:
            messages.append(result.get("message") or "Stopped GPU")

    return {
        "ok": ok,
        "stopped": ok,
        "device": target,
        "message": " · ".join(messages) if messages else "Nothing to stop",
        "error": None if ok else " · ".join(messages),
    }

def _get_launch_lock():
    global _launch_lock
    if _launch_lock is None:
        import threading
        _launch_lock = threading.Lock()
    return _launch_lock


def _launch_training_job(merged: dict[str, Any]) -> None:
    """Background worker: upload + remote bootstrap (can take minutes)."""
    global _launch_state
    launch_log = OUTPUT_DIR / "launch_status.json"
    try:
        env, host, port, ssh, (scp_cmd, remote) = _connect()
        _ensure_rl_import()
        from runpod_train import remote_train_script

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        launch_log.write_text(
            json.dumps({"busy": True, "error": None, "stage": "uploading"}, indent=2),
            encoding="utf-8",
        )

        # Upload trainers + agents so pod gets latest code
        try:
            from human_bootstrap import load_human_demo_policy, save_policy_cache

            policy = load_human_demo_policy(refresh=True)
            if policy:
                save_policy_cache(policy)
        except Exception as e:
            print(f"Human demo export for RunPod skipped: {e}")

        human_bootstrap_py = BACKEND_DIR / "human_bootstrap.py"
        human_demos_json = OUTPUT_DIR / "human_demos_bootstrap.json"
        uploads = [
            (LOCAL_TRAIN, "/workspace/train.py.fixed"),
            (LOCAL_AGENTS, "/workspace/agents.py.fixed"),
            (DQN_TRAIN, "/workspace/dqn_train.py.fixed"),
            (PARALLEL_TRAIN, "/workspace/parallel_train.py.fixed"),
            (RL_DIR / "progress_io.py", "/workspace/progress_io.py.fixed"),
            (human_bootstrap_py, "/workspace/human_bootstrap.py.fixed"),
            (human_demos_json, "/workspace/human_demos_bootstrap.json"),
        ]
        for local, remote_path in uploads:
            if local.exists():
                subprocess.check_call(
                    scp_cmd + [str(local), f"{remote}:{remote_path}"],
                    timeout=90,
                )

        launch_log.write_text(
            json.dumps({"busy": True, "error": None, "stage": "starting_remote"}, indent=2),
            encoding="utf-8",
        )
        script = remote_train_script(merged).replace("\r\n", "\n").replace("\r", "\n")
        proc = subprocess.run(
            ssh + ["bash", "-s"],
            input=script.encode("utf-8"),
            capture_output=True,
            timeout=420,
            check=False,
        )
        out = (proc.stdout or b"").decode("utf-8", errors="replace")
        err = (proc.stderr or b"").decode("utf-8", errors="replace")
        (OUTPUT_DIR / "launch_remote.log").write_text(
            (out[-12000:] if out else "") + ("\n--- STDERR ---\n" + err[-4000:] if err else ""),
            encoding="utf-8",
        )
        died = (
            "=== TRAIN DIED IMMEDIATELY ===" in out
            or "Traceback (most recent call last):" in out
            or "RuntimeError:" in out
        )
        success_markers = (
            "=== TRAIN LAUNCHED ===",
            "=== TRAIN FINISHED OR STARTED",
            "DQN TRAINING COMPLETE",
            "TRAINING COMPLETE!",
            "PARALLEL CPU TRAINING COMPLETE",
        )
        if died:
            # Prefer the real exception over a false "launched" banner
            detail = out[-1500:] if out else (err or "remote trainer crashed")
            _launch_state["error"] = f"Remote trainer crashed:\n{detail}"
        elif any(m in out for m in success_markers):
            _launch_state["error"] = None
        elif proc.returncode != 0:
            detail = (err or out or str(proc.returncode))[-1200:]
            _launch_state["error"] = f"Remote launch failed: {detail}"
        else:
            _launch_state["error"] = None
        launch_log.write_text(
            json.dumps(
                {
                    "busy": False,
                    "error": _launch_state.get("error"),
                    "stage": "done" if not _launch_state.get("error") else "failed",
                    "returncode": proc.returncode,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as e:
        _launch_state["error"] = str(e)
        try:
            launch_log.write_text(
                json.dumps({"busy": False, "error": str(e), "stage": "failed"}, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
    finally:
        _launch_state["busy"] = False


def start_training(params: dict[str, Any] | None = None) -> dict[str, Any]:
    import threading

    merged = save_params(params or load_saved_params())
    device = "gpu" if str(merged.get("train_device") or "cpu").lower() == "gpu" else "cpu"

    # CPU and GPU are independent — only block if *that* device is already busy
    if device == "cpu":
        if _local_pid() is not None:
            return {
                "ok": False,
                "error": "Local CPU training already running. Stop CPU first, or switch Device to GPU to start a RunPod job alongside it.",
                "running": True,
                "cpu_running": True,
            }
        return _start_local(merged)

    # GPU → RunPod neural DQN only (no local GPU fallback). CPU may keep running.
    status = get_status()
    if status.get("launching") and not (status.get("gpu") or {}).get("elapsed"):
        started_at = float(_launch_state.get("started_at") or 0)
        if started_at and (time.time() - started_at) > 180:
            _launch_state["busy"] = False
            status = get_status()
    if status.get("gpu_running"):
        return {
            "ok": False,
            "error": "GPU training already running on RunPod. Stop GPU first, or switch Device to CPU to start local tabular training alongside it.",
            "running": True,
            "gpu_running": True,
        }

    try:
        _connect()
    except Exception as e:
        return {
            "ok": False,
            "error": f"GPU training requires RunPod SSH. Could not connect: {e}",
            "params": merged,
        }

    with _get_launch_lock():
        if _launch_state.get("busy"):
            return {
                "ok": True,
                "started": False,
                "launching": True,
                "params": merged,
                "message": "Launch already in progress on RunPod…",
            }
        _launch_state["busy"] = True
        _launch_state["error"] = None
        _launch_state["started_at"] = time.time()
        try:
            (OUTPUT_DIR / "launch_status.json").write_text(
                json.dumps({"busy": True, "error": None, "stage": "queued"}, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    # Force remote script onto DQN path
    merged = {**merged, "train_device": "gpu"}
    save_params(merged)
    threading.Thread(target=_launch_training_job, args=(merged,), daemon=True).start()
    cpu_note = " Local CPU can keep running in parallel." if status.get("cpu_running") else ""
    return {
        "ok": True,
        "started": True,
        "launching": True,
        "params": merged,
        "message": (
            "Launching neural DQN on RunPod. Progress syncs into this page"
            f" (GPU files go to gpu_live/ while CPU owns local output).{cpu_note}"
        ),
    }


def pull_results() -> dict[str, Any]:
    # Local runs already write into OUTPUT_DIR — archive if stats exist
    if _local_pid() is None and (OUTPUT_DIR / "training_stats.json").exists():
        # If train_device is cpu / local completed, just archive
        params = load_saved_params()
        if params.get("train_device") == "cpu":
            archived = None
            try:
                from rl_runs import archive_current_run
                archived = archive_current_run(source="local")
            except Exception as e:
                archived = {"error": str(e)}
            return {
                "ok": True,
                "pulled": ["training_stats.json (local)"],
                "skipped": [],
                "path": str(OUTPUT_DIR),
                "archived": archived,
                "message": (
                    f"Local results archived"
                    + (
                        " + uploaded to Supabase"
                        if isinstance(archived, dict) and archived.get("supabase_uploaded")
                        else ""
                    )
                    + "."
                ),
            }

    try:
        env, host, port, ssh, (scp_cmd, remote) = _connect()
    except Exception as e:
        # Fall back to local archive
        if (OUTPUT_DIR / "training_stats.json").exists():
            try:
                from rl_runs import archive_current_run
                archived = archive_current_run(source="local_fallback")
            except Exception as e2:
                archived = {"error": str(e2)}
            return {
                "ok": True,
                "pulled": ["training_stats.json (local)"],
                "skipped": [],
                "path": str(OUTPUT_DIR),
                "archived": archived,
                "message": f"RunPod unavailable ({e}); archived local files.",
            }
        return {"ok": False, "error": str(e)}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    remote_files = [
        "qtable_train.csv",
        "trajectory_train.csv",
        "training_stats.json",
        "last_run_params.json",
        "dqn_policy.pt",
        "training_progress.json",
    ]
    pulled = []
    skipped = []
    for name in remote_files:
        src = f"{remote}:/workspace/Golf_solver/backend/RL/output/{name}"
        try:
            subprocess.check_call(
                scp_cmd + [src, str(OUTPUT_DIR)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
            )
            pulled.append(name)
        except Exception:
            skipped.append(name)

    archived = None
    if "training_stats.json" in pulled:
        try:
            from rl_runs import archive_current_run
            archived = archive_current_run(source="pull")
        except Exception as e:
            archived = {"error": str(e)}

    return {
        "ok": True,
        "pulled": pulled,
        "skipped": skipped,
        "path": str(OUTPUT_DIR),
        "archived": archived,
    }
