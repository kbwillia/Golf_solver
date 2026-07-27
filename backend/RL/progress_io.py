"""Shared helpers for writing live training progress / stats for the RL UI."""
from __future__ import annotations

import json
import os
from typing import Any

_BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_BASE, "output")


def get_output_path(filename: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, filename)


def save_training_stats_json(training_stats: dict[str, Any], filename: str = "training_stats.json") -> str:
    output_path = get_output_path(filename)
    payload = {
        "games_played": int(training_stats.get("games_played", 0)),
        "wins": int(training_stats.get("wins", 0)),
        "losses": int(training_stats.get("losses", 0)),
        "scores": [float(x) for x in training_stats.get("scores", [])],
        "opponent_scores": [float(x) for x in training_stats.get("opponent_scores", [])],
        "qtable_states": [int(x) for x in training_stats.get("qtable_states", [])],
        "qtable_entries": [int(x) for x in training_stats.get("qtable_entries", [])],
        "epsilon_values": [float(x) for x in training_stats.get("epsilon_values", [])],
        "training_times": [float(x) for x in training_stats.get("training_times", [])],
        "train_device": training_stats.get("train_device"),
        "train_mode": training_stats.get("train_mode"),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
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
    data: dict[str, Any] = {
        "ok": True,
        "running": game < games_total,
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
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                data.update({k: existing.get(k, data.get(k)) for k in data})
                data["checkpoints"] = list(existing.get("checkpoints") or [])
                series = existing.get("series") or {}
                data["series"] = {
                    "games": list(series.get("games") or []),
                    "avg_scores": list(series.get("avg_scores") or []),
                    "qtable_states": list(series.get("qtable_states") or []),
                    "epsilon": list(series.get("epsilon") or []),
                    "win_rates": list(series.get("win_rates") or []),
                }
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    cp = {
        "game": int(game),
        "phase": str(phase),
        "win_rate": float(win_rate),
        "avg_score": float(avg_score),
        "states": int(states),
        "epsilon": float(epsilon),
    }
    data["checkpoints"].append(cp)
    # Keep last ~200 checkpoints to bound file size
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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def mark_progress_complete(filename: str = "training_progress.json") -> None:
    path = get_output_path(filename)
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["running"] = False
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
