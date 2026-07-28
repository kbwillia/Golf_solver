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


def _downsample_indices(n: int, max_points: int) -> list[int]:
    if n <= 0:
        return []
    if n <= max_points:
        return list(range(n))
    # Evenly spaced indices spanning the full run, always include last point
    indices = [int(round(i * (n - 1) / (max_points - 1))) for i in range(max_points)]
    # de-dupe while preserving order
    out: list[int] = []
    seen = set()
    for i in indices:
        if i not in seen:
            seen.add(i)
            out.append(i)
    if out[-1] != n - 1:
        out.append(n - 1)
    return out


def build_series_full(training_stats: dict[str, Any], max_points: int = 2500) -> dict[str, Any] | None:
    """Downsample in-memory per-game arrays into a compact full-run series with absolute game #s."""
    scores = list(training_stats.get("scores") or [])
    opp = list(training_stats.get("opponent_scores") or [])
    states = list(training_stats.get("qtable_states") or [])
    entries = list(training_stats.get("qtable_entries") or [])
    eps = list(training_stats.get("epsilon_values") or [])
    loss = list(training_stats.get("loss_values") or [])
    buffer = list(training_stats.get("buffer_sizes") or [])
    n = max(len(scores), len(opp), len(states), len(entries), len(eps), len(loss), len(buffer), 0)
    if n < 2:
        return None
    games_played = int(training_stats.get("games_played") or n)
    start = max(1, games_played - n + 1)

    def at(seq: list, i: int, cast):
        if not seq:
            return None
        j = min(len(seq) - 1, i)
        v = seq[j]
        if v is None:
            return None
        return cast(v)

    idxs = _downsample_indices(n, max_points)
    series = {
        "games": [start + i for i in idxs],
        "scores": [at(scores, i, float) for i in idxs] if scores else [],
        "opponent_scores": [at(opp, i, float) for i in idxs] if opp else [],
        "qtable_states": [at(states, i, int) for i in idxs] if states else [],
        "qtable_entries": [at(entries, i, int) for i in idxs] if entries else [],
        "epsilon": [at(eps, i, float) for i in idxs] if eps else [],
        "loss": [at(loss, i, float) for i in idxs] if loss else [],
        "buffer_sizes": [at(buffer, i, int) for i in idxs] if buffer else [],
    }
    return series


def save_training_stats_json(training_stats: dict[str, Any], filename: str = "training_stats.json") -> str:
    output_path = get_output_path(filename)
    # Cap high-res series so the file stays readable for the UI while training
    def _tail(seq, n=5000):
        return list(seq[-n:]) if seq else []

    games_played = int(training_stats.get("games_played", 0))
    # Full-run downsample from in-memory arrays (before tailing) — absolute game axis
    series_full = build_series_full(training_stats, max_points=2500)
    # Keep caller-provided series_full if arrays were already tailed but full series exists
    if series_full is None and isinstance(training_stats.get("series_full"), dict):
        series_full = training_stats.get("series_full")

    payload = {
        "games_played": games_played,
        "wins": int(training_stats.get("wins", 0)),
        "losses": int(training_stats.get("losses", 0)),
        "scores": [float(x) for x in _tail(training_stats.get("scores", []))],
        "opponent_scores": [float(x) for x in _tail(training_stats.get("opponent_scores", []))],
        "qtable_states": [int(x) for x in _tail(training_stats.get("qtable_states", []))],
        "qtable_entries": [int(x) for x in _tail(training_stats.get("qtable_entries", []))],
        "epsilon_values": [float(x) for x in _tail(training_stats.get("epsilon_values", []))],
        "training_times": [float(x) for x in _tail(training_stats.get("training_times", []))],
        "loss_values": [
            (None if x is None else float(x))
            for x in _tail(training_stats.get("loss_values", []))
        ],
        "buffer_sizes": [int(x) for x in _tail(training_stats.get("buffer_sizes", []))],
        "train_device": training_stats.get("train_device"),
        "train_mode": training_stats.get("train_mode"),
    }
    if series_full:
        payload["series_full"] = series_full
        payload["series_full_games"] = int(series_full["games"][-1]) if series_full.get("games") else games_played
    # Wall-clock totals must survive the series tail — UI duration depends on these
    if training_stats.get("total_time") is not None:
        try:
            payload["total_time"] = float(training_stats["total_time"])
        except (TypeError, ValueError):
            pass
    if training_stats.get("games_per_sec") is not None:
        try:
            payload["games_per_sec"] = float(training_stats["games_per_sec"])
        except (TypeError, ValueError):
            pass
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
    loss: float | None = None,
    buffer_size: int | None = None,
    train_mode: str | None = None,
    train_device: str | None = None,
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
            "losses": [],
            "buffer_sizes": [],
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
        "losses": list(series.get("losses") or []),
        "buffer_sizes": list(series.get("buffer_sizes") or []),
    }

    cp = {
        "game": int(game),
        "phase": str(phase),
        "win_rate": float(win_rate),
        "avg_score": float(avg_score),
        "states": int(states),
        "epsilon": float(epsilon),
    }
    if loss is not None:
        cp["loss"] = float(loss)
    if buffer_size is not None:
        cp["buffer_size"] = int(buffer_size)
    data["checkpoints"].append(cp)
    data["checkpoints"] = data["checkpoints"][-200:]
    s = data["series"]
    s["games"].append(int(game))
    s["avg_scores"].append(float(avg_score))
    s["qtable_states"].append(int(states))
    s["epsilon"].append(float(epsilon))
    s["win_rates"].append(float(win_rate))
    s["losses"].append(None if loss is None else float(loss))
    s["buffer_sizes"].append(None if buffer_size is None else int(buffer_size))
    for key in s:
        s[key] = s[key][-200:]

    pct = int(100 * game / games_total) if games_total else 0
    data["ok"] = True
    data["tqdm_pct"] = pct
    data["tqdm_current"] = int(game)
    data["tqdm_total"] = int(games_total)
    data["running"] = game < games_total
    if train_mode:
        data["train_mode"] = train_mode
    if train_device:
        data["train_device"] = train_device
    data["summary"] = {
        "games_played": int(game),
        "games_total": int(games_total),
        "pct": pct,
        "avg_score": float(avg_score),
        "final_states": int(states),
        "final_epsilon": float(epsilon),
        "win_rate": float(win_rate),
        "final_loss": None if loss is None else float(loss),
        "buffer_size": None if buffer_size is None else int(buffer_size),
        "train_mode": train_mode,
        "train_device": train_device,
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
