"""Aggregate RL training CSVs/JSON into chart-ready payloads for the frontend."""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from typing import Any

import pandas as pd

RL_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RL", "output")

# mtime caches — sync polls every few seconds; avoid re-parsing multi-MB CSVs each time
_FILE_CACHE: dict[str, tuple[float, int, Any]] = {}
_HUMAN_DEMO_CACHE: tuple[float, Any] | None = None
_HUMAN_DEMO_TTL_SEC = 30.0


def _path(name: str) -> str:
    return os.path.join(RL_OUTPUT_DIR, name)


def _cached_file_build(path: str, builder, *args, **kwargs):
    """Return builder(path, ...) result, cached while path mtime+size are unchanged."""
    if not path or not os.path.exists(path):
        return builder(path, *args, **kwargs)
    try:
        st = os.stat(path)
        key = f"{path}|{getattr(builder, '__name__', 'fn')}|{args}|{tuple(sorted(kwargs.items()))}"
        hit = _FILE_CACHE.get(key)
        if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
            return hit[2]
        value = builder(path, *args, **kwargs)
        _FILE_CACHE[key] = (st.st_mtime, st.st_size, value)
        return value
    except OSError:
        return builder(path, *args, **kwargs)


def _human_demo_summary_cached() -> dict[str, Any]:
    """Fetch human demo hole scores from Supabase, TTL-cached for sync polls."""
    import importlib
    import time

    global _HUMAN_DEMO_CACHE
    now = time.monotonic()
    if _HUMAN_DEMO_CACHE and (now - _HUMAN_DEMO_CACHE[0]) < _HUMAN_DEMO_TTL_SEC:
        cached = _HUMAN_DEMO_CACHE[1]
        # Don't keep serving a failed import/error for the full TTL
        if cached.get("available") or not cached.get("error"):
            return cached
    try:
        import data_upset as _du

        fetch = getattr(_du, "fetch_human_demo_score_summary", None)
        if fetch is None:
            _du = importlib.reload(_du)
            fetch = getattr(_du, "fetch_human_demo_score_summary", None)
        if fetch is None:
            value = {
                "available": False,
                "error": "fetch_human_demo_score_summary missing — restart Flask (python run_app.py)",
                "used_in_bootstrap": False,
            }
        else:
            value = fetch()
    except Exception as e:
        value = {"available": False, "error": str(e), "used_in_bootstrap": False}
    _HUMAN_DEMO_CACHE = (now, value)
    return value


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
    # Fast path: trajectory rows are stringified dicts — avoid ast.literal_eval per row
    if isinstance(action_raw, str):
        if "take_discard" in action_raw:
            return "take_discard"
        if "draw_deck" in action_raw or "draw_flip" in action_raw:
            low = action_raw.lower()
            if "'keep': true" in low or '"keep": true' in low:
                return "draw_keep"
            return "draw_flip"
        return "unknown"
    if isinstance(action_raw, dict):
        typ = action_raw.get("type")
        if typ == "draw_deck":
            return "draw_keep" if action_raw.get("keep") else "draw_flip"
        if typ == "take_discard":
            return "take_discard"
        return str(typ or "unknown")
    return "unknown"


def _build_action_series(traj_path: str, max_points: int = 500) -> dict[str, Any]:
    if not os.path.exists(traj_path):
        return {"available": False}

    # Huge trajectory CSVs — only scan a tail so the RL API stays responsive
    try:
        size = os.path.getsize(traj_path)
    except OSError:
        size = 0
    if size > 12_000_000:
        return _build_action_series_tail(traj_path, max_points=max_points, max_bytes=2_500_000)

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


def _build_action_series_tail(
    traj_path: str, max_points: int = 500, max_bytes: int = 2_500_000
) -> dict[str, Any]:
    """Parse only the end of a large trajectory file for action charts."""
    import csv

    try:
        with open(traj_path, "rb") as bf:
            bf.seek(0, os.SEEK_END)
            end = bf.tell()
            start = max(0, end - max_bytes)
            bf.seek(start)
            raw = bf.read().decode("utf-8", errors="ignore")
    except OSError:
        return {"available": False, "truncated": True}

    if start > 0:
        nl = raw.find("\n")
        raw = raw[nl + 1 :] if nl >= 0 else raw
    with open(traj_path, "r", encoding="utf-8", errors="ignore") as f:
        header = f.readline().strip()
    text = header + "\n" + raw
    reader = csv.DictReader(text.splitlines())
    types = ["take_discard", "draw_keep", "draw_flip"]
    counts = defaultdict(int)
    by_game: dict[int, dict[str, int]] = {}
    steps = 0
    for row in reader:
        try:
            g = int(row.get("game") or 0)
        except (TypeError, ValueError):
            continue
        atype = _action_type(row.get("action"))
        counts[atype] += 1
        steps += 1
        bucket = by_game.setdefault(g, {t: 0 for t in types})
        if atype in bucket:
            bucket[atype] += 1
    if not by_game:
        return {"available": False, "truncated": True}
    games = sorted(by_game)
    cum = {t: 0 for t in types}
    series = {t: [] for t in types}
    g_out = []
    for g in games:
        for t in types:
            cum[t] += by_game[g].get(t, 0)
            series[t].append(cum[t])
        g_out.append(g)
    down = _downsample({"games": g_out, **series}, max_points=max_points)
    return {
        "available": True,
        "truncated": True,
        "games": down["games"],
        "cumulative": {t: down[t] for t in types},
        "unique_states": [],
        "totals": {t: int(counts[t]) for t in types},
        "steps": steps,
    }


def _count_csv_data_rows(path: str) -> int:
    """Fast newline count (data rows ≈ lines − 1)."""
    try:
        with open(path, "rb") as f:
            n = sum(buf.count(b"\n") for buf in iter(lambda: f.read(1 << 20), b""))
        return max(0, n - 1)
    except OSError:
        return 0


def _build_qvalue_hist(qtable_path: str, bins: int = 40) -> dict[str, Any]:
    """Q-table summary without loading the full CSV into pandas.

    Huge tables without a visits column use a fast line-count path so the RL
    API stays responsive (human demos / cumulative strip still load).
    """
    if not os.path.exists(qtable_path):
        return {"available": False}

    import csv
    import random
    import numpy as np

    try:
        size = os.path.getsize(qtable_path)
    except OSError:
        size = 0

    try:
        with open(qtable_path, "r", encoding="utf-8", errors="ignore") as f:
            header_line = f.readline()
    except OSError:
        return {"available": False}
    header_l = header_line.lower()
    has_visits_col = "visits" in header_l

    # Fast path: big table, no visit tracking yet — SA pairs via newline count
    if size > 20_000_000 and not has_visits_col:
        entries = _count_csv_data_rows(qtable_path)
        return {
            "available": True,
            "bin_centers": [],
            "counts": [],
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "num_states": None,
            "num_entries": entries,
            "states_partial": True,
            "sampled_hist": True,
            "fast_path": True,
            "has_visits": False,
        }

    well_visited_min = 5
    n = 0
    states: set[str] = set()
    has_visits = False
    visit_sum = 0.0
    well = 0
    q_sum = 0.0
    q_min = None
    q_max = None
    sample_cap = 40_000
    sample: list[float] = []
    sample_seen = 0
    track_states = size < 25_000_000
    stride = 1 if size < 40_000_000 else 4

    try:
        with open(qtable_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                n += 1
                if track_states:
                    sk = row.get("state_key") or ""
                    if sk:
                        states.add(sk)
                if n % stride != 0 and not has_visits_col:
                    continue
                try:
                    qv = float(row.get("q_value") or 0.0)
                except (TypeError, ValueError):
                    qv = 0.0
                q_sum += qv
                q_min = qv if q_min is None else min(q_min, qv)
                q_max = qv if q_max is None else max(q_max, qv)
                sample_seen += 1
                if len(sample) < sample_cap:
                    sample.append(qv)
                else:
                    j = random.randint(0, sample_seen - 1)
                    if j < sample_cap:
                        sample[j] = qv
                if has_visits_col:
                    has_visits = True
                    try:
                        v = int(float(row.get("visits") or 0))
                    except (TypeError, ValueError):
                        v = 0
                    visit_sum += v
                    if v >= well_visited_min:
                        well += 1
    except OSError:
        return {"available": False}

    if n == 0:
        return {"available": False}

    q_n = max(1, sample_seen)
    values = np.asarray(sample, dtype=float) if sample else np.asarray([0.0])
    hist_counts, edges = np.histogram(values, bins=bins)
    centers = ((edges[:-1] + edges[1:]) / 2.0).tolist()
    out: dict[str, Any] = {
        "available": True,
        "bin_centers": centers,
        "counts": hist_counts.tolist(),
        "min": float(q_min if q_min is not None else 0.0),
        "max": float(q_max if q_max is not None else 0.0),
        "mean": float(q_sum / q_n),
        "std": float(values.std()) if len(values) else 0.0,
        "num_states": len(states) if track_states else None,
        "num_entries": n,
        "states_partial": not track_states,
        "sampled_hist": True,
        "fast_path": False,
    }
    if has_visits:
        completion = well / n
        out["has_visits"] = True
        out["completion_pct"] = float(completion)
        out["sparsity_index"] = float(1.0 - completion)
        out["mean_visits"] = float(visit_sum / n)
        out["well_visited_min"] = well_visited_min
    else:
        out["has_visits"] = False
    return out


def _counts_as_win(our: float, opp: float) -> bool:
    """Strict lower score wins; 0-0 ties count as a win."""
    return our < opp or (our == 0 and opp == 0)


def _rolling_win_rate(scores: list[float], opp: list[float], window: int) -> list[float | None]:
    if not scores or not opp or len(scores) != len(opp):
        return []
    out: list[float | None] = []
    for i, (a, b) in enumerate(zip(scores, opp)):
        if i + 1 < window:
            out.append(None)
        else:
            start = i + 1 - window
            w = sum(1 for x, y in zip(scores[start : i + 1], opp[start : i + 1]) if _counts_as_win(x, y))
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

    try:
        from progress_io import load_json_file
        stats = load_json_file(stats_path, default=None)
    except Exception:
        stats = None
        try:
            with open(stats_path, encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            stats = None
    if not isinstance(stats, dict):
        return {"available": False, "error": "training_stats.json unreadable"}

    games_played = int(stats.get("games_played") or 0)
    train_mode = str(stats.get("train_mode") or "")
    train_device = str(stats.get("train_device") or "")

    # Prefer compact full-run series (absolute game #s spanning the whole job)
    full = stats.get("series_full") if isinstance(stats.get("series_full"), dict) else None
    use_full = bool(full and full.get("games") and len(full["games"]) >= 2)

    hist_scores = [float(x) for x in stats.get("scores", [])]
    hist_opp = [float(x) for x in stats.get("opponent_scores", [])]

    if use_full:
        games = [int(x) for x in full["games"]]
        n = len(games)

        def _align(seq, cast, fill=None):
            if not seq:
                return [] if fill is None else [fill] * n
            out = []
            for i in range(n):
                j = min(len(seq) - 1, i)
                v = seq[j]
                out.append(fill if v is None and fill is not None else (None if v is None else cast(v)))
            return out

        scores = _align(full.get("scores") or hist_scores, float, 0.0)
        opp = _align(full.get("opponent_scores") or hist_opp, float, 0.0) if (full.get("opponent_scores") or hist_opp) else []
        states = _align(full.get("qtable_states") or [], int, 0)
        entries = _align(full.get("qtable_entries") or [], int, 0)
        eps = _align(full.get("epsilon") or [], float, 0.0)
        loss_vals = _align(full.get("loss") or [], float, None) if full.get("loss") else []
        buffer_sizes = _align(full.get("buffer_sizes") or [], int, 0) if full.get("buffer_sizes") else []
        if not train_mode:
            train_mode = "dqn" if loss_vals else "tabular"
    else:
        scores = list(hist_scores)
        opp = list(hist_opp)
        states = [int(x) for x in stats.get("qtable_states", [])]
        entries = [int(x) for x in stats.get("qtable_entries", [])]
        eps = [float(x) for x in stats.get("epsilon_values", [])]
        loss_raw = list(stats.get("loss_values", []) or [])
        buffer_raw = list(stats.get("buffer_sizes", []) or [])
        if not train_mode:
            train_mode = "dqn" if loss_raw else "tabular"
        n = max(len(scores), len(states), len(entries), len(eps), len(loss_raw), len(buffer_raw), 0)
        # Absolute game numbers for tailed series (e.g. 45001..50000), not 1..n
        start = max(1, (games_played or n) - n + 1) if n else 1
        games = list(range(start, start + n))

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
        if loss_raw:
            loss_vals = []
            for i in range(n):
                idx = min(len(loss_raw) - 1, int(i * len(loss_raw) / max(1, n)))
                v = loss_raw[idx]
                loss_vals.append(None if v is None else float(v))
        else:
            loss_vals = []
        buffer_sizes = pad([int(x) for x in buffer_raw], 0) if buffer_raw else []

    if not hist_scores:
        hist_scores = [float(x) for x in scores if x is not None]
    if not hist_opp:
        hist_opp = [float(x) for x in opp if x is not None]

    window = max(5, min(50, n // 20 or 5))
    win_window = max(20, min(200, n // 10 or 20))

    score_wins = 0
    if hist_scores and hist_opp and len(hist_scores) == len(hist_opp):
        score_wins = sum(1 for a, b in zip(hist_scores, hist_opp) if _counts_as_win(a, b))

    series_raw = {
        "games": games,
        "scores": scores,
        "opponent_scores": opp if opp else [None] * n,
        "score_ma": _moving_average([float(x or 0) for x in scores], window),
        "opponent_ma": _moving_average([float(x or 0) for x in opp], window) if opp else [None] * n,
        "qtable_states": states,
        "qtable_entries": entries,
        "epsilon": eps,
        "rolling_win_rate": _rolling_win_rate(
            [float(x or 0) for x in scores],
            [float(x or 0) for x in opp],
            win_window,
        ) if opp else [None] * n,
        "loss": loss_vals,
        "loss_ma": [],
        "buffer_sizes": buffer_sizes,
    }
    if loss_vals and any(x is not None for x in loss_vals):
        filled = []
        last = None
        for x in loss_vals:
            if x is not None:
                last = x
            filled.append(last if last is not None else 0.0)
        series_raw["loss_ma"] = _moving_average(filled, window)
    # Full-run series is already compact; keep more points so GPU loss spans the job
    series = _downsample(series_raw, max_points=max(max_points, 800 if use_full else max_points))

    if not games_played:
        games_played = int(games[-1]) if games else n
    first = scores[: min(100, len(scores))] if scores else []
    last = scores[-min(100, len(scores)) :] if scores else []
    final_loss = next((x for x in reversed(loss_vals) if x is not None), None) if loss_vals else None
    wins_count = score_wins or int(stats.get("wins", 0))

    def _last_metric(key: str, final_key: str | None = None) -> float | None:
        if final_key and stats.get(final_key) is not None:
            try:
                return float(stats[final_key])
            except (TypeError, ValueError):
                pass
        seq = stats.get(key) or []
        if not seq:
            return None
        try:
            return float(seq[-1])
        except (TypeError, ValueError):
            return None

    completion_pct = _last_metric("completion_pct", "final_completion_pct")
    sparsity_index = _last_metric("sparsity_index", "final_sparsity_index")
    mean_visits = _last_metric("mean_visits", "final_mean_visits")

    return {
        "available": True,
        "games_ma_window": window,
        "win_rate_window": win_window,
        "bootstrap_games": bootstrap_games,
        "train_mode": train_mode,
        "train_device": train_device,
        "series": series,
        "series_span": "full" if use_full else "tail",
        "score_histogram": _score_histogram(hist_scores),
        "summary": {
            "games_played": games_played,
            "wins": wins_count,
            "losses": max(0, games_played - wins_count),
            "win_rate": (wins_count / games_played) if games_played else 0.0,
            "avg_score": float(sum(hist_scores) / len(hist_scores)) if hist_scores else None,
            "avg_opponent_score": float(sum(hist_opp) / len(hist_opp)) if hist_opp else None,
            "best_score": float(min(hist_scores)) if hist_scores else None,
            "early_avg_score": float(sum(first) / len(first)) if first else None,
            "late_avg_score": float(sum(last) / len(last)) if last else None,
            "improvement": (
                float(sum(first) / len(first) - sum(last) / len(last)) if first and last else None
            ),
            "final_states": int(states[-1]) if states else 0,
            "final_entries": int(entries[-1]) if entries else 0,
            "final_epsilon": float(eps[-1]) if eps else None,
            "final_loss": final_loss,
            "final_buffer_size": int(buffer_sizes[-1]) if buffer_sizes else None,
            "completion_pct": completion_pct,
            "sparsity_index": sparsity_index,
            "mean_visits": mean_visits,
            "train_mode": train_mode,
            "train_device": train_device,
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
        learning = _cached_file_build(
            _run_stats_path(rid),
            _build_from_stats,
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
    "epsilon_decay_factor": "Multiply ε by this every decay step (e.g. 0.995). Closer to 1 = slower decay. With 0.995, ~140 decays halves ε; ~460 decays cuts it by ~10×.",
    "epsilon_decay_interval": "How often ε is multiplied by the decay factor. Rule of thumb: set this to ~0.5–1% of total Games (e.g. 2M games → 10k–20k). Smaller % = more decays = ε drops faster. Your 2M/10k setup is ~0.5%.",
    "learning_rate": "Step size (alpha) for Q-updates. Higher learns faster from each sample but can be unstable; lower is smoother.",
    "discount_factor": "Gamma: how much future rewards count vs immediate reward. Closer to 1 = more long-term planning.",
    "bootstrap": "Imitation phase: prefer recorded human (state→action) demos when the live state matches exactly or closely; otherwise copy EV. Seeds Q / replay before the agent plays on its own.",
    "human_demos": "Opt-in human play recorded from the game UI. Used during bootstrap when the state matches (exact / close); EV fills gaps. Charts use human turn order (not raw game.round) so second-seat holes aren’t shifted into a fake R5.",
    "human_board": "Columns are the human’s Nth action on the hole (T1–T4), so first-seat and second-seat holes line up. Each cell is take/keep/flip mix for that card slot. When the opponent goes first, the game counter shows R2–R5 for those same four human turns.",
    "human_flips": "Draw-and-flip location by human turn (T1–T4). Darker = larger share of that turn’s flips. Aligns holes whether the human dealt first or second.",
    "reward_shaping": "Dense per-step bonuses/penalties (pair, high keep, etc.) to speed early learning. For a true solve, turn shaping OFF so the agent optimizes only real golf outcomes — shaped rewards can bias the final policy.",
    "soft_prior": "On first visit to a (state, action) in early rounds, seed Q₀ from visible-hand strength instead of 0: low cards (A/2/J) → positive, high (10/Q/K) → negative, clipped to ±scale (default 5). Learning overwrites it; biases early TD targets and max-Q bootstrap. Applies only for round ≤ Prior max round.",
    "action_heuristics": "Human-demo / EV gates for CPU Q. Soft discard prior biases take_discard Q₀ (good/pair +, junk −). Hard discard gate bans taking discard ≥ junk pts unless it pairs. Pair force-take: if discard matches a known rank, only take is legal. Ban junk on private: on last round / last slot, forbid placing 10/Q/K onto a known low private card. EV gap hard: if |draw_EV − discard_EV| > threshold, only the better action type stays legal. Hard gates apply after bootstrap only so EV/human teachers stay free.",
    "q_states": "Number of distinct game situations (state keys) stored in the Q-table.",
    "sa_pairs": "State-action pairs: how many (situation, move) combinations have a Q-value.",
    "q_value": "Estimated quality of taking an action in a state. Higher Q means the agent currently prefers that action.",
    "avg_score": "Mean golf score (lower is better). EV agent baseline is typically around ~12.",
    "win_rate": "Fraction of games counted as wins: strictly lower score than the opponent, or a 0–0 tie (treated as a win).",
    "games_per_hour": "Throughput: games completed per hour for that run (from games ÷ wall time). Hover Time or GPH for games/sec.",
    "duration": "Wall-clock training time for the run. Hover a cell for games/sec when available.",
    "improvement": "Early-window average score minus late-window average. Positive means the agent’s scores got lower (better) over training.",
    "rolling_win_rate": "Win rate over a sliding window of recent games — smoother than overall win rate for spotting learning trends.",
    "completion_pct": "Fraction of known (state, action) Q entries with visit count N ≥ 5. Not a finite full-space % — the table grows forever; this is how ‘filled in’ the known cells are.",
    "sparsity_index": "1 − completion_pct. Near 1 means most known cells are rarely visited; near 0 means most known cells are well sampled.",
    "mean_visits": "Average visit count N(s,a) over every Q-table entry that exists.",
    "exploration_beta": "Count-based exploration bonus β in Q + β/√(N+1). Higher β prefers rarely tried actions when exploiting (ε does not fire).",
    "ev_baseline": "Typical average score for the hand-coded expected-value agent (~12 in EV vs EV sims). Use this as a performance reference line.",
    "opponent_ma": "Moving average of the opponent’s score over games.",
    "score_ma": "Moving average of the agent’s score — dampens noise so learning trends are easier to see.",
    "dqn_loss": "Smooth L1 (Huber) TD loss from neural DQN updates. Only for GPU/DQN runs — lower and more stable usually means the network is fitting better.",
    "batch_size": "How many replay transitions are trained in one GPU step. 512 is a good throughput default; larger uses more VRAM.",
    "hidden_size": "Width of the DQN MLP. 256 is the throughput default; bigger nets cost more GPU time per update.",
    "train_steps": "GPU gradient updates after each parallel rollout round (clamped ~8–32). Keep low (8–16) for games/hour; raise only if you want more SGD per collected batch.",
    "workers": "Parallel CPU processes that simulate golf games. For GPU DQN this is the main speed lever — match your pod vCPU count (often 8).",
    "replay_buffer": "Number of transitions stored for DQN replay. Grows until the buffer cap; learning needs enough samples before loss is meaningful.",
    "network_params": "Fixed neural network weight count (not a growing Q-table). Flat line is expected for DQN.",
    "cpu_total_games": "Sum of games_played across archived CPU tabular runs (plus the current stats file if not yet archived).",
    "cpu_sa_pairs": "Total state-action pairs currently stored in qtable_train.csv (the live CPU Q-table).",
}


def _cpu_cumulative(runs: list[dict], stats: dict, qhist: dict) -> dict[str, Any]:
    """Lifetime CPU Q-learning progress across archived runs + live table."""
    total_games = 0
    cpu_runs = 0
    for r in runs or []:
        params = r.get("params") or {}
        summary = r.get("summary") or {}
        device = str(params.get("train_device") or summary.get("train_device") or "").lower()
        mode = str(params.get("train_mode") or summary.get("train_mode") or "").lower()
        is_cpu = device == "cpu" or mode in ("tabular", "tabular_parallel", "")
        is_gpu = device == "gpu" or mode in ("dqn", "dqn_parallel")
        if is_gpu and not is_cpu:
            continue
        if is_cpu or (not is_gpu and r.get("has_stats")):
            g = summary.get("games_played")
            if g is None:
                continue
            try:
                total_games += int(g)
                cpu_runs += 1
            except (TypeError, ValueError):
                pass
    # Prefer live Q CSV for SA pairs / states
    sa = qhist.get("num_entries") if qhist.get("available") else None
    states = qhist.get("num_states") if qhist.get("available") else None
    # Don't fall back to a tiny last-run state count when the live Q-table is huge
    if states is None and isinstance(stats, dict) and not qhist.get("fast_path"):
        states = (stats.get("summary") or {}).get("final_states")
    if sa is None and isinstance(stats, dict):
        sa = (stats.get("summary") or {}).get("final_entries")
    return {
        "available": True,
        "total_games": total_games or (stats.get("summary") or {}).get("games_played"),
        "cpu_runs": cpu_runs,
        "sa_pairs": sa,
        "q_states": states,
        "completion_pct": qhist.get("completion_pct") if qhist.get("has_visits") else None,
        "sparsity_index": qhist.get("sparsity_index") if qhist.get("has_visits") else None,
        "mean_visits": qhist.get("mean_visits") if qhist.get("has_visits") else None,
        "has_visits": bool(qhist.get("has_visits")),
    }


def build_training_viz_payload(compare_run_ids: list[str] | None = None) -> dict[str, Any]:
    """Build the full JSON response for GET /api/rl/training."""
    from rl_runs import list_runs

    # Human demos first — cheap Supabase call; must not wait on huge CSVs
    human_demos = _human_demo_summary_cached()

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
    stats = _cached_file_build(
        _path("training_stats.json"), _build_from_stats, bootstrap_games=bootstrap
    )
    actions = _cached_file_build(_path("trajectory_train.csv"), _build_action_series)

    train_mode = (stats.get("train_mode") if isinstance(stats, dict) else None) or params.get(
        "train_mode"
    )
    # Do NOT treat ui train_device=gpu as "this page is DQN" — that hid Q-table stats
    is_dqn = str(train_mode or "").lower() in ("dqn", "dqn_parallel")

    # Always load Q-table summary for cumulative CPU strip (fast-path on large files)
    qhist = _cached_file_build(_path("qtable_train.csv"), _build_qvalue_hist)

    live = {}
    live_path = _path("training_progress.json")
    if os.path.exists(live_path):
        try:
            with open(live_path, encoding="utf-8") as f:
                live = json.load(f)
        except (OSError, json.JSONDecodeError):
            live = {}

    if live.get("train_mode"):
        live_mode = str(live.get("train_mode")).lower()
        is_dqn = is_dqn or live_mode in ("dqn", "dqn_parallel")
        if isinstance(stats, dict) and stats.get("available"):
            stats["train_mode"] = live.get("train_mode") or stats.get("train_mode")
            stats["train_device"] = live.get("train_device") or stats.get("train_device")

    summary = dict(stats.get("summary") or {})
    if qhist.get("available"):
        if qhist.get("num_states") is not None:
            summary.setdefault("final_states", qhist["num_states"])
        if qhist.get("num_entries") is not None:
            summary.setdefault("final_entries", qhist["num_entries"])
        if not qhist.get("fast_path"):
            summary["q_mean"] = qhist.get("mean")
            summary["q_std"] = qhist.get("std")
        if qhist.get("has_visits") and qhist.get("completion_pct") is not None:
            summary.setdefault("completion_pct", qhist["completion_pct"])
            summary.setdefault("sparsity_index", qhist.get("sparsity_index"))
            summary.setdefault("mean_visits", qhist.get("mean_visits"))
            summary.setdefault("has_visits", True)
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
                "train_mode": live.get("train_mode") or ("dqn" if is_dqn else "tabular"),
                "train_device": live.get("train_device"),
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
                    "loss": s.get("losses") or [],
                    "loss_ma": s.get("losses") or [],
                    "buffer_sizes": s.get("buffer_sizes") or [],
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
                "train_mode": "tabular",
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
                    "loss": [],
                    "buffer_sizes": [],
                },
                "score_histogram": {"available": False},
                "summary": summary,
            }

    # Ensure train_mode on learning payload
    if isinstance(stats, dict) and stats.get("available") and not stats.get("train_mode"):
        stats["train_mode"] = "dqn" if is_dqn else "tabular"

    runs = list_runs(limit=40)
    compare_ids = compare_run_ids or []
    # Default compare: up to 3 most recent archived runs with stats
    if not compare_ids:
        compare_ids = [r["id"] for r in runs if r.get("has_stats")][:3]

    cpu_cumulative = _cpu_cumulative(runs, stats if isinstance(stats, dict) else {}, qhist)
    # Mirror cumulative into summary so the top strip always has SA pairs / coverage
    if cpu_cumulative.get("sa_pairs") is not None:
        summary.setdefault("final_entries", cpu_cumulative["sa_pairs"])
    if cpu_cumulative.get("q_states") is not None:
        summary.setdefault("final_states", cpu_cumulative["q_states"])
    if cpu_cumulative.get("completion_pct") is not None:
        summary.setdefault("completion_pct", cpu_cumulative["completion_pct"])
        summary.setdefault("sparsity_index", cpu_cumulative.get("sparsity_index"))
        summary.setdefault("has_visits", True)
    summary["cpu_total_games"] = cpu_cumulative.get("total_games")
    summary["cpu_runs"] = cpu_cumulative.get("cpu_runs")

    files = {
        "training_stats": os.path.exists(_path("training_stats.json")),
        "trajectory": os.path.exists(_path("trajectory_train.csv")),
        "qtable": os.path.exists(_path("qtable_train.csv")),
        "live_progress": os.path.exists(live_path),
    }

    return {
        "ok": any(files.values()) or bool(live.get("ok")) or bool(runs) or bool(human_demos.get("available")),
        "files": files,
        "summary": summary,
        "params": params,
        "learning": stats,
        "actions": actions,
        "qvalues": {"available": False} if is_dqn or qhist.get("fast_path") else qhist,
        "cpu_cumulative": cpu_cumulative,
        "human_demos": human_demos,
        "api_build": "2026-07-28-cpu-human",
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
