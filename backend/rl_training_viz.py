"""Aggregate RL training CSVs/JSON into chart-ready payloads for the frontend."""
from __future__ import annotations

import ast
import json
import math
import os
from collections import defaultdict
from typing import Any

import pandas as pd

RL_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RL", "output")


def _path(name: str) -> str:
    return os.path.join(RL_OUTPUT_DIR, name)


def _moving_average(values: list[float], window: int) -> list[float | None]:
    if not values:
        return []
    window = max(1, min(window, len(values)))
    out: list[float | None] = [None] * (window - 1)
    running = sum(values[: window - 1])
    for i in range(window - 1, len(values)):
        running += values[i]
        out.append(running / window)
        running -= values[i - window + 1]
    return out


def _downsample(series: dict[str, list], max_points: int = 500) -> dict[str, list]:
    n = 0
    for v in series.values():
        if isinstance(v, list):
            n = max(n, len(v))
    if n <= max_points or n == 0:
        return series
    step = max(1, n // max_points)
    indices = list(range(0, n, step))
    if indices[-1] != n - 1:
        indices.append(n - 1)
    out: dict[str, list] = {}
    for key, values in series.items():
        if not isinstance(values, list) or len(values) != n:
            out[key] = values
        else:
            out[key] = [values[i] for i in indices]
    return out


def _action_type(action_raw: Any) -> str:
    try:
        action = ast.literal_eval(action_raw) if isinstance(action_raw, str) else action_raw
    except (ValueError, SyntaxError):
        return "unknown"
    if not isinstance(action, dict):
        return "unknown"
    typ = action.get("type")
    if typ == "draw_deck":
        return "draw_keep" if action.get("keep") else "draw_flip"
    if typ == "take_discard":
        return "take_discard"
    return str(typ or "unknown")


def _build_action_series(traj_path: str, max_points: int = 500) -> dict[str, Any]:
    if not os.path.exists(traj_path):
        return {"available": False}

    df = pd.read_csv(traj_path, usecols=["game", "action", "state_key"])
    if df.empty:
        return {"available": False}

    df["action_type"] = df["action"].map(_action_type)
    types = ["take_discard", "draw_keep", "draw_flip"]
    counts = defaultdict(int)
    seen_states: set[str] = set()
    games: list[int] = []
    series = {t: [] for t in types}
    unique_states: list[int] = []

    for game, group in df.groupby("game", sort=True):
        for row in group.itertuples(index=False):
            atype = row.action_type
            counts[atype] += 1
            seen_states.add(str(row.state_key))
        games.append(int(game))
        for t in types:
            series[t].append(counts[t])
        unique_states.append(len(seen_states))

    totals = {t: int(counts[t]) for t in types}
    down = _downsample(
        {"games": games, "unique_states": unique_states, **series},
        max_points=max_points,
    )
    return {
        "available": True,
        "games": down["games"],
        "cumulative": {t: down[t] for t in types},
        "unique_states": down["unique_states"],
        "totals": totals,
        "steps": int(len(df)),
    }


def _build_qvalue_hist(qtable_path: str, bins: int = 40) -> dict[str, Any]:
    if not os.path.exists(qtable_path):
        return {"available": False}

    import numpy as np

    df = pd.read_csv(qtable_path, usecols=["q_value", "state_key", "action_key"])
    if df.empty:
        return {"available": False}

    values = df["q_value"].astype(float).to_numpy()
    counts, edges = np.histogram(values, bins=bins)
    centers = ((edges[:-1] + edges[1:]) / 2.0).tolist()
    return {
        "available": True,
        "bin_centers": centers,
        "counts": counts.tolist(),
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "std": float(values.std()),
        "num_states": int(df["state_key"].nunique()),
        "num_entries": int(len(df)),
    }


def _rolling_win_rate(scores: list[float], opp: list[float], window: int) -> list[float | None]:
    if not scores or not opp or len(scores) != len(opp):
        return []
    out: list[float | None] = []
    wins = 0
    for i, (a, b) in enumerate(zip(scores, opp)):
        if a < b:
            wins += 1
        if i + 1 < window:
            out.append(None)
        else:
            # recompute window
            start = i + 1 - window
            w = sum(1 for x, y in zip(scores[start : i + 1], opp[start : i + 1]) if x < y)
            out.append(w / window)
    return out


def _score_histogram(scores: list[float], bins: int = 20) -> dict[str, Any]:
    """Integer score histogram from 0 through max observed (0 is always included)."""
    if not scores:
        return {"available": False}
    import numpy as np

    max_score = int(max(math.ceil(max(scores)), 0))
    # One bin per integer score: [0,1), [1,2), …, [max, max+1]
    edges = np.arange(0, max_score + 2, dtype=float)
    counts, _ = np.histogram(scores, bins=edges)
    centers = list(range(0, max_score + 1))
    return {
        "available": True,
        "bin_centers": centers,
        "counts": counts.tolist(),
        "min_score": 0,
        "max_score": max_score,
    }


def _build_from_stats(
    stats_path: str,
    max_points: int = 500,
    *,
    bootstrap_games: int | None = None,
) -> dict[str, Any]:
    if not os.path.exists(stats_path):
        return {"available": False}

    with open(stats_path, encoding="utf-8") as f:
        stats = json.load(f)

    scores = [float(x) for x in stats.get("scores", [])]
    opp = [float(x) for x in stats.get("opponent_scores", [])]
    states = [int(x) for x in stats.get("qtable_states", [])]
    entries = [int(x) for x in stats.get("qtable_entries", [])]
    eps = [float(x) for x in stats.get("epsilon_values", [])]
    n = max(len(scores), len(states), len(entries), len(eps), 0)
    games = list(range(1, n + 1))

    def pad(seq: list, fill):
        if len(seq) == n:
            return seq
        if not seq:
            return [fill] * n
        if len(seq) < n:
            mapped = []
            for i in range(n):
                idx = min(len(seq) - 1, int(i * len(seq) / n))
                mapped.append(seq[idx])
            return mapped
        return seq[:n]

    scores = pad(scores, 0.0)
    opp = pad(opp, 0.0) if opp else []
    states = pad(states, 0)
    entries = pad(entries, 0)
    eps = pad(eps, 0.0)

    window = max(5, min(50, n // 20 or 5))
    win_window = max(20, min(200, n // 10 or 20))

    # Score-based wins (reliable)
    score_wins = 0
    if scores and opp and len(scores) == len(opp):
        score_wins = sum(1 for a, b in zip(scores, opp) if a < b)

    series_raw = {
        "games": games,
        "scores": scores,
        "opponent_scores": opp if opp else [None] * n,
        "score_ma": _moving_average(scores, window),
        "opponent_ma": _moving_average(opp, window) if opp else [None] * n,
        "qtable_states": states,
        "qtable_entries": entries,
        "epsilon": eps,
        "rolling_win_rate": _rolling_win_rate(scores, opp, win_window) if opp else [None] * n,
    }
    series = _downsample(series_raw, max_points=max_points)

    games_played = int(stats.get("games_played") or n)
    first = scores[: min(100, len(scores))] if scores else []
    last = scores[-min(100, len(scores)) :] if scores else []

    return {
        "available": True,
        "games_ma_window": window,
        "win_rate_window": win_window,
        "bootstrap_games": bootstrap_games,
        "series": series,
        "score_histogram": _score_histogram(scores),
        "summary": {
            "games_played": games_played,
            "wins": score_wins or int(stats.get("wins", 0)),
            "losses": max(0, games_played - (score_wins or int(stats.get("wins", 0)))),
            "win_rate": ((score_wins or int(stats.get("wins", 0))) / games_played) if games_played else 0.0,
            "avg_score": float(sum(scores) / len(scores)) if scores else None,
            "avg_opponent_score": float(sum(opp) / len(opp)) if opp else None,
            "best_score": float(min(scores)) if scores else None,
            "early_avg_score": float(sum(first) / len(first)) if first else None,
            "late_avg_score": float(sum(last) / len(last)) if last else None,
            "improvement": (
                float(sum(first) / len(first) - sum(last) / len(last)) if first and last else None
            ),
            "final_states": int(states[-1]) if states else 0,
            "final_entries": int(entries[-1]) if entries else 0,
            "final_epsilon": float(eps[-1]) if eps else None,
        },
    }


def _run_stats_path(run_id: str) -> str:
    return os.path.join(RL_OUTPUT_DIR, "runs", run_id, "training_stats.json")


def _run_params(run_id: str) -> dict[str, Any]:
    meta_path = os.path.join(RL_OUTPUT_DIR, "runs", run_id, "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, encoding="utf-8") as f:
                return (json.load(f).get("params") or {})
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def build_compare_series(run_ids: list[str], max_points: int = 400) -> list[dict[str, Any]]:
    out = []
    for rid in run_ids:
        params = _run_params(rid)
        learning = _build_from_stats(
            _run_stats_path(rid),
            max_points=max_points,
            bootstrap_games=params.get("n_bootstrap_games"),
        )
        if not learning.get("available"):
            continue
        meta_path = os.path.join(RL_OUTPUT_DIR, "runs", rid, "meta.json")
        label = rid
        created = None
        if os.path.exists(meta_path):
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
                label = meta.get("created_at_display") or meta.get("label") or rid
                created = meta.get("created_at")
            except (OSError, json.JSONDecodeError):
                pass
        out.append(
            {
                "id": rid,
                "label": label,
                "created_at": created,
                "params": params,
                "summary": learning.get("summary"),
                "series": {
                    "games": learning["series"].get("games"),
                    "score_ma": learning["series"].get("score_ma"),
                    "scores": learning["series"].get("scores"),
                    "rolling_win_rate": learning["series"].get("rolling_win_rate"),
                    "qtable_states": learning["series"].get("qtable_states"),
                    "epsilon": learning["series"].get("epsilon"),
                },
                "bootstrap_games": learning.get("bootstrap_games"),
            }
        )
    return out


GLOSSARY = {
    "epsilon": "Exploration rate: probability of taking a random action instead of the best known Q-value. Higher = more exploration, lower = more exploitation.",
    "learning_rate": "Step size (alpha) for Q-updates. Higher learns faster from each sample but can be unstable; lower is smoother.",
    "discount_factor": "Gamma: how much future rewards count vs immediate reward. Closer to 1 = more long-term planning.",
    "bootstrap": "Imitation phase: the agent copies an EV (expected-value) policy for the first N games to seed the Q-table with reasonable behavior.",
    "reward_shaping": "Dense per-step bonuses/penalties (pair, high keep, etc.) to speed early learning. For a true solve, turn shaping OFF so the agent optimizes only real golf outcomes — shaped rewards can bias the final policy.",
    "q_states": "Number of distinct game situations (state keys) stored in the Q-table.",
    "sa_pairs": "State-action pairs: how many (situation, move) combinations have a Q-value.",
    "q_value": "Estimated quality of taking an action in a state. Higher Q means the agent currently prefers that action.",
    "avg_score": "Mean golf score (lower is better). EV agent baseline is typically around ~12.",
    "win_rate": "Fraction of games where the agent’s score is strictly lower than the opponent’s.",
    "improvement": "Early-window average score minus late-window average. Positive means the agent’s scores got lower (better) over training.",
    "rolling_win_rate": "Win rate over a sliding window of recent games — smoother than overall win rate for spotting learning trends.",
    "ev_baseline": "Typical average score for the hand-coded expected-value agent (~12 in EV vs EV sims). Use this as a performance reference line.",
    "opponent_ma": "Moving average of the opponent’s score over games.",
    "score_ma": "Moving average of the agent’s score — dampens noise so learning trends are easier to see.",
}


def build_training_viz_payload(compare_run_ids: list[str] | None = None) -> dict[str, Any]:
    """Build the full JSON response for GET /api/rl/training."""
    from rl_runs import list_runs

    params = {}
    for name in ("last_run_params.json", "ui_train_params.json"):
        p = _path(name)
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    params = json.load(f)
                break
            except (OSError, json.JSONDecodeError):
                pass

    bootstrap = params.get("n_bootstrap_games")
    stats = _build_from_stats(_path("training_stats.json"), bootstrap_games=bootstrap)
    actions = _build_action_series(_path("trajectory_train.csv"))
    qhist = _build_qvalue_hist(_path("qtable_train.csv"))

    live = {}
    live_path = _path("training_progress.json")
    if os.path.exists(live_path):
        try:
            with open(live_path, encoding="utf-8") as f:
                live = json.load(f)
        except (OSError, json.JSONDecodeError):
            live = {}

    summary = dict(stats.get("summary") or {})
    if qhist.get("available"):
        summary.setdefault("final_states", qhist["num_states"])
        summary.setdefault("final_entries", qhist["num_entries"])
        summary["q_mean"] = qhist["mean"]
        summary["q_std"] = qhist["std"]
    if actions.get("available"):
        summary["trajectory_steps"] = actions["steps"]
        summary["action_totals"] = actions["totals"]
        if not summary.get("games_played") and actions.get("games"):
            summary["games_played"] = int(max(actions["games"]))

    if live.get("summary"):
        for k, v in live["summary"].items():
            if v is not None:
                summary[k] = v

    if not stats.get("available"):
        if live.get("series") and live["series"].get("games"):
            s = live["series"]
            stats = {
                "available": True,
                "games_ma_window": None,
                "from_live_progress": True,
                "bootstrap_games": bootstrap,
                "series": {
                    "games": s.get("games") or [],
                    "scores": s.get("avg_scores") or [],
                    "opponent_scores": [],
                    "score_ma": s.get("avg_scores") or [],
                    "opponent_ma": [],
                    "qtable_states": s.get("qtable_states") or [],
                    "qtable_entries": [],
                    "epsilon": s.get("epsilon") or [],
                    "rolling_win_rate": [],
                },
                "score_histogram": {"available": False},
                "summary": summary,
            }
        elif actions.get("available"):
            stats = {
                "available": True,
                "games_ma_window": None,
                "from_trajectory_fallback": True,
                "bootstrap_games": bootstrap,
                "series": {
                    "games": actions["games"],
                    "scores": [],
                    "opponent_scores": [],
                    "score_ma": [],
                    "opponent_ma": [],
                    "qtable_states": actions.get("unique_states") or [],
                    "qtable_entries": [],
                    "epsilon": [],
                    "rolling_win_rate": [],
                },
                "score_histogram": {"available": False},
                "summary": summary,
            }

    runs = list_runs(limit=40)
    compare_ids = compare_run_ids or []
    # Default compare: up to 3 most recent archived runs with stats
    if not compare_ids:
        compare_ids = [r["id"] for r in runs if r.get("has_stats")][:3]

    files = {
        "training_stats": os.path.exists(_path("training_stats.json")),
        "trajectory": os.path.exists(_path("trajectory_train.csv")),
        "qtable": os.path.exists(_path("qtable_train.csv")),
        "live_progress": os.path.exists(live_path),
    }

    return {
        "ok": any(files.values()) or bool(live.get("ok")) or bool(runs),
        "files": files,
        "summary": summary,
        "params": params,
        "learning": stats,
        "actions": actions,
        "qvalues": qhist,
        "baselines": {
            "ev_avg_score": 12.0,
            "label": "EV agent baseline (~12 avg score)",
        },
        "glossary": GLOSSARY,
        "runs": [
            {
                "id": r.get("id"),
                "label": r.get("created_at_display") or r.get("label"),
                "created_at": r.get("created_at"),
                "summary": r.get("summary"),
                "params": r.get("params"),
                "has_stats": r.get("has_stats"),
            }
            for r in runs
        ],
        "compare": build_compare_series(compare_ids),
        "compare_ids": compare_ids,
        "live": {
            "running": bool(live.get("running")),
            "pct": (live.get("summary") or {}).get("pct"),
            "games_played": (live.get("summary") or {}).get("games_played"),
            "games_total": (live.get("summary") or {}).get("games_total"),
            "pulled_training_stats": bool(live.get("pulled_training_stats")),
        },
    }
