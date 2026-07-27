"""Shared helpers for writing live training progress / stats for the RL UI."""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any

_BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_BASE, "output")


def get_output_path(filename: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, filename)


def _atomic_write_json(path: str, payload: Any) -> None:
    """Write JSON atomically to avoid torn/concatenated files under concurrent readers."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=os.path.basename(path) + ".",
        suffix=".tmp",
        dir=os.path.dirname(path) or ".",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_json_file(path: str, default: Any = None) -> Any:
    """Load JSON; on corrupt/partial files return default instead of raising."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Recover first JSON value if file was concatenated mid-write
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(raw.lstrip())
            return obj
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return default


def save_training_stats_json(training_stats: dict[str, Any], filename: str = "training_stats.json") -> str:
    output_path = get_output_path(filename)
    # Cap series length so the file stays readable for the UI while training
    def _tail(seq, n=5000):
        return list(seq[-n:]) if seq else []

    payload = {
        "games_played": int(training_stats.get("games_played", 0)),
        "wins": int(training_stats.get("wins", 0)),
        "losses": int(training_stats.get("losses", 0)),
        "scores": [float(x) for x in _tail(training_stats.get("scores", []))],
        "opponent_scores": [float(x) for x in _tail(training_stats.get("opponent_scores", []))],
        "qtable_states": [int(x) for x in _tail(training_stats.get("qtable_states", []))],
        "qtable_entries": [int(x) for x in _tail(training_stats.get("qtable_entries", []))],
        "epsilon_values": [float(x) for x in _tail(training_stats.get("epsilon_values", []))],
        "training_times": [float(x) for x in _tail(training_stats.get("training_times", []))],
        "train_device": training_stats.get("train_device"),
        "train_mode": training_stats.get("train_mode"),
    }
    _atomic_write_json(output_path, payload)
    return output_path


def append_progress_checkpoint(
    *,
    game: int,
    games_total: int,
    phase: str,
    win_rate: float,
    avg_score: float,
    states: int,
    epsilon: float,
    filename: str = "training_progress.json",
) -> None:
    """Update training_progress.json in the format the live viz expects."""
    path = get_output_path(filename)
    data = load_json_file(path, default=None) or {
        "ok": True,
        "running": True,
        "checkpoints": [],
        "series": {
            "games": [],
            "avg_scores": [],
            "qtable_states": [],
            "epsilon": [],
            "win_rates": [],
        },
        "summary": {},
    }
    if not isinstance(data.get("checkpoints"), list):
        data["checkpoints"] = []
    series = data.get("series") if isinstance(data.get("series"), dict) else {}
    data["series"] = {
        "games": list(series.get("games") or []),
        "avg_scores": list(series.get("avg_scores") or []),
        "qtable_states": list(series.get("qtable_states") or []),
        "epsilon": list(series.get("epsilon") or []),
        "win_rates": list(series.get("win_rates") or []),
    }

    cp = {
        "game": int(game),
        "phase": str(phase),
        "win_rate": float(win_rate),
        "avg_score": float(avg_score),
        "states": int(states),
        "epsilon": float(epsilon),
    }
    data["checkpoints"].append(cp)
    data["checkpoints"] = data["checkpoints"][-200:]
    s = data["series"]
    s["games"].append(int(game))
    s["avg_scores"].append(float(avg_score))
    s["qtable_states"].append(int(states))
    s["epsilon"].append(float(epsilon))
    s["win_rates"].append(float(win_rate))
    for key in s:
        s[key] = s[key][-200:]

    pct = int(100 * game / games_total) if games_total else 0
    data["ok"] = True
    data["tqdm_pct"] = pct
    data["tqdm_current"] = int(game)
    data["tqdm_total"] = int(games_total)
    data["running"] = game < games_total
    data["summary"] = {
        "games_played": int(game),
        "games_total": int(games_total),
        "pct": pct,
        "avg_score": float(avg_score),
        "final_states": int(states),
        "final_epsilon": float(epsilon),
        "win_rate": float(win_rate),
    }
    _atomic_write_json(path, data)


def mark_progress_complete(filename: str = "training_progress.json") -> None:
    path = get_output_path(filename)
    data = load_json_file(path, default=None)
    if not isinstance(data, dict):
        return
    data["running"] = False
    try:
        _atomic_write_json(path, data)
    except OSError:
        pass
