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
    "num_games": 5000,
    "learning_rate": 0.1,
    "discount_factor": 0.9,
    "epsilon": 0.2,
    "epsilon_decay_factor": 0.995,
    "n_bootstrap_games": 1000,
    "use_imitation_learning": True,
    "epsilon_decay_interval": 100,
    "progress_report_interval": 250,
    "opponent_type": "ev_ai",
    # cpu = local parallel tabular Q | gpu = neural DQN (RunPod if remote, else local CUDA)
    "train_device": "cpu",
    "num_workers": max(2, os.cpu_count() or 4),
    "batch_size": 256,
    "hidden_size": 256,
    # Reward shaping — turn off (or zero weights) for unbiased / solve-mode runs
    "use_reward_shaping": True,
    "shape_step": 0.05,
    "shape_pair": 1.5,
    "shape_high_keep": -0.8,
    "shape_low_keep": 0.3,
    "shape_midhigh_keep": -0.4,
    "shape_flip": 0.1,
}

_launch_lock = None
_launch_state: dict[str, Any] = {"busy": False, "error": None, "started_at": None}


def _ensure_rl_import() -> None:
    rl_path = str(RL_DIR)
    if rl_path not in sys.path:
        sys.path.insert(0, rl_path)


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
            return merged
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return dict(DEFAULT_PARAMS)


def save_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_PARAMS)
    merged.update(params or {})
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
    merged["num_workers"] = max(1, int(merged.get("num_workers") or (os.cpu_count() or 4)))
    merged["batch_size"] = max(32, int(merged.get("batch_size") or 256))
    merged["hidden_size"] = max(32, int(merged.get("hidden_size") or 256))
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


_TRAIN_CMD_MARKERS = ("parallel_train.py", "dqn_train.py", "train.py")


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
    """True only if pid is alive AND looks like our RL trainer (avoids PID reuse false positives)."""
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            if str(pid) not in out:
                return False
            # Prefer command-line check so a recycled PID (e.g. a shell) isn't treated as training
            try:
                cmd = subprocess.check_output(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").CommandLine",
                    ],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                ).strip()
            except Exception:
                cmd = ""
            if cmd:
                low = cmd.lower().replace("\\", "/")
                return any(m in low for m in _TRAIN_CMD_MARKERS)
            # Fallback: process image is python (weaker — still better than blind PID match alone)
            return "python" in out.lower()
        os.kill(pid, 0)
        try:
            import psutil

            cmdline = " ".join(psutil.Process(pid).cmdline()).lower().replace("\\", "/")
            return any(m in cmdline for m in _TRAIN_CMD_MARKERS)
        except Exception:
            return True
    except Exception:
        return False


def _local_pid() -> int | None:
    if not LOCAL_PID_PATH.exists():
        return None
    try:
        pid = int(LOCAL_PID_PATH.read_text(encoding="utf-8").strip())
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
        mode_msg = f"local parallel tabular Q ({merged['num_workers']} workers → Supabase on archive)"

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
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

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


def get_status() -> dict[str, Any]:
    params = load_saved_params()
    local_pid = _local_pid()
    if local_pid is not None:
        return {
            "ok": True,
            "running": True,
            "local": True,
            "launching": False,
            "launch_error": None,
            "elapsed": _local_elapsed(local_pid),
            "pid": local_pid,
            "params": params,
            "remote_params": None,
            "defaults": DEFAULT_PARAMS,
            "train_device": params.get("train_device", "cpu"),
        }

    # No local job — optionally probe RunPod when last mode was GPU
    remote = {
        "ok": True,
        "running": bool(_launch_state.get("busy")),
        "local": False,
        "launching": bool(_launch_state.get("busy")),
        "launch_error": _launch_state.get("error"),
        "elapsed": None,
        "params": params,
        "remote_params": None,
        "defaults": DEFAULT_PARAMS,
        "train_device": params.get("train_device", "cpu"),
    }
    if params.get("train_device") != "gpu" and not _launch_state.get("busy"):
        return remote

    try:
        env, host, port, ssh, _ = _connect()
    except SystemExit as e:
        remote["ok"] = False
        remote["error"] = str(e)
        return remote
    except Exception as e:
        remote["ok"] = False
        remote["error"] = str(e)
        return remote

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
        remote["ok"] = False
        remote["error"] = str(e)
        return remote

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

    remote.update({
        "ok": True,
        "running": running or bool(_launch_state.get("busy")),
        "launching": bool(_launch_state.get("busy")),
        "elapsed": etime or None,
        "remote_params": remote_params,
    })
    return remote


def stop_training() -> dict[str, Any]:
    # Prefer local stop if a local pid exists
    if _local_pid() is not None or LOCAL_PID_PATH.exists():
        return _stop_local()

    try:
        env, host, port, ssh, _ = _connect()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    remote = r"""
pkill -f "python -u run_remote_train.py" 2>/dev/null || true
pkill -f "python -u dqn_train.py" 2>/dev/null || true
pkill -f "python -u parallel_train.py" 2>/dev/null || true
pkill -f "python -u train.py" 2>/dev/null || true
sleep 1
if [ -f /workspace/logs/train.pid ] && ps -p $(cat /workspace/logs/train.pid) >/dev/null 2>&1; then
  echo STILL_RUNNING
  exit 1
fi
echo STOPPED
"""
    try:
        out = subprocess.check_output(
            ssh + ["bash", "-lc", remote],
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": "Failed to stop remote process", "detail": (e.output or "")[-500:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "stopped": True, "message": out.strip() or "STOPPED"}


def _get_launch_lock():
    global _launch_lock
    if _launch_lock is None:
        import threading
        _launch_lock = threading.Lock()
    return _launch_lock


def _launch_training_job(merged: dict[str, Any]) -> None:
    """Background worker: upload + remote bootstrap (can take minutes)."""
    global _launch_state
    try:
        env, host, port, ssh, (scp_cmd, remote) = _connect()
        _ensure_rl_import()
        from runpod_train import remote_train_script

        # Upload trainers + agents so pod gets latest code
        uploads = [
            (LOCAL_TRAIN, "/workspace/train.py.fixed"),
            (LOCAL_AGENTS, "/workspace/agents.py.fixed"),
            (DQN_TRAIN, "/workspace/dqn_train.py.fixed"),
            (PARALLEL_TRAIN, "/workspace/parallel_train.py.fixed"),
            (RL_DIR / "progress_io.py", "/workspace/progress_io.py.fixed"),
        ]
        for local, remote_path in uploads:
            if local.exists():
                subprocess.check_call(
                    scp_cmd + [str(local), f"{remote}:{remote_path}"],
                    timeout=60,
                )

        script = remote_train_script(merged)
        proc = subprocess.run(
            ssh + ["bash", "-s"],
            input=script.encode("utf-8"),
            capture_output=True,
            timeout=300,
            check=False,
        )
        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", errors="replace")[-800:]
            out = (proc.stdout or b"").decode("utf-8", errors="replace")[-800:]
            _launch_state["error"] = f"Remote launch failed: {err or out or proc.returncode}"
        else:
            _launch_state["error"] = None
    except Exception as e:
        _launch_state["error"] = str(e)
    finally:
        _launch_state["busy"] = False


def start_training(params: dict[str, Any] | None = None) -> dict[str, Any]:
    import threading

    merged = save_params(params or load_saved_params())
    status = get_status()
    if status.get("running"):
        where = "locally" if status.get("local") else "on RunPod"
        return {
            "ok": False,
            "error": f"Training already running {where}. Stop it first, then start with new params.",
            "running": True,
        }

    # CPU → local parallel tabular; results archived + uploaded to Supabase from this machine
    if merged.get("train_device") == "cpu":
        return _start_local(merged)

    # GPU → RunPod neural DQN only (no local GPU fallback)
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

    # Force remote script onto DQN path
    merged = {**merged, "train_device": "gpu"}
    save_params(merged)
    threading.Thread(target=_launch_training_job, args=(merged,), daemon=True).start()
    return {
        "ok": True,
        "started": True,
        "launching": True,
        "params": merged,
        "message": "Launching neural DQN on RunPod. Pull + archive when done to save results to Supabase.",
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
