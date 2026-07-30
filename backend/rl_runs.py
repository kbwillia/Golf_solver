"""Multi-run archival and indexing for RL training visualizations."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
    EST = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    EST = timezone(timedelta(hours=-4))

RL_OUTPUT = Path(__file__).resolve().parent / "RL" / "output"
RUNS_DIR = RL_OUTPUT / "runs"
INDEX_PATH = RL_OUTPUT / "runs_index.json"

# Files worth copying into a run archive (stats are required for charts)
ARCHIVE_FILES = (
    "training_stats.json",
    "last_run_params.json",
    "ui_train_params.json",
    "training_progress.json",
    "train_perf.json",
    "train_perf.jsonl",
    "last_run_perf.json",
)


def _now_est() -> datetime:
    return datetime.now(EST)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now_est()).isoformat()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_index() -> list[dict[str, Any]]:
    data = _load_json(INDEX_PATH)
    if isinstance(data, dict) and isinstance(data.get("runs"), list):
        return data["runs"]
    if isinstance(data, list):
        return data
    return []


def save_index(runs: list[dict[str, Any]]) -> None:
    # newest first
    runs_sorted = sorted(runs, key=lambda r: r.get("created_at") or "", reverse=True)
    _write_json(INDEX_PATH, {"runs": runs_sorted, "updated_at": _iso()})


def _duration_from_stats(stats: dict[str, Any] | None) -> tuple[float | None, float | None]:
    """Return (duration_sec, games_per_sec) from training_stats.

    Prefer wall-clock total_time. training_times are per-game samples and may be
    tailed to the last N games in live saves — never sum them when truncated.
    """
    stats = stats or {}
    games = int(stats.get("games_played") or 0)

    total = stats.get("total_time")
    try:
        total_f = float(total) if total is not None else None
    except (TypeError, ValueError):
        total_f = None

    if total_f is not None and total_f > 0:
        gps = (games / total_f) if games else stats.get("games_per_sec")
        try:
            gps_f = float(gps) if gps is not None else None
        except (TypeError, ValueError):
            gps_f = None
        return total_f, gps_f

    # Explicit throughput from trainer
    try:
        gps_direct = float(stats["games_per_sec"]) if stats.get("games_per_sec") is not None else None
    except (TypeError, ValueError):
        gps_direct = None
    if gps_direct and gps_direct > 0 and games > 0:
        return games / gps_direct, gps_direct

    times = stats.get("training_times") or []
    if not times:
        return None, None
    try:
        floats = [float(x) for x in times]
    except (TypeError, ValueError):
        return None, None
    if not floats:
        return None, None

    mean_t = sum(floats) / len(floats)
    if mean_t <= 0:
        return None, None

    # Per-game samples: if series was tailed, extrapolate to full run
    if games > 0 and len(floats) < games:
        total_f = mean_t * games
    else:
        total_f = sum(floats)

    if total_f <= 0:
        return None, None
    gps_f = (games / total_f) if games else (1.0 / mean_t)
    return total_f, gps_f


def _summarize_stats(stats: dict[str, Any] | None, params: dict[str, Any] | None) -> dict[str, Any]:
    stats = stats or {}
    params = params or {}
    scores = [float(x) for x in stats.get("scores") or []]
    opp = [float(x) for x in stats.get("opponent_scores") or []]
    games = int(stats.get("games_played") or len(scores) or params.get("num_games") or 0)

    wins = int(stats.get("wins") or 0)
    # Prefer score-based wins when available (more reliable than buggy counter)
    if scores and opp and len(scores) == len(opp):
        wins = sum(1 for a, b in zip(scores, opp) if a < b or (a == 0 and b == 0))
        ties = sum(1 for a, b in zip(scores, opp) if a == b and not (a == 0 and b == 0))
    else:
        ties = 0

    first_n = scores[: max(1, min(100, len(scores)))] if scores else []
    last_n = scores[-max(1, min(100, len(scores))) :] if scores else []
    duration_sec, games_per_sec = _duration_from_stats(stats)

    return {
        "games_played": games,
        "wins": wins,
        "ties": ties,
        "win_rate": (wins / games) if games else None,
        "avg_score": (sum(scores) / len(scores)) if scores else None,
        "avg_opponent_score": (sum(opp) / len(opp)) if opp else None,
        "best_score": min(scores) if scores else None,
        "worst_score": max(scores) if scores else None,
        "early_avg_score": (sum(first_n) / len(first_n)) if first_n else None,
        "late_avg_score": (sum(last_n) / len(last_n)) if last_n else None,
        "improvement": (
            (sum(first_n) / len(first_n)) - (sum(last_n) / len(last_n))
            if first_n and last_n
            else None
        ),  # positive = better (lower golf score)
        "final_states": int((stats.get("qtable_states") or [0])[-1] or 0)
        if stats.get("qtable_states")
        else None,
        "final_entries": int((stats.get("qtable_entries") or [0])[-1] or 0)
        if stats.get("qtable_entries")
        else None,
        "completion_pct": (
            float(stats["final_completion_pct"])
            if stats.get("final_completion_pct") is not None
            else (
                float((stats.get("completion_pct") or [None])[-1])
                if stats.get("completion_pct")
                else None
            )
        ),
        "sparsity_index": (
            float(stats["final_sparsity_index"])
            if stats.get("final_sparsity_index") is not None
            else (
                float((stats.get("sparsity_index") or [None])[-1])
                if stats.get("sparsity_index")
                else None
            )
        ),
        "mean_visits": (
            float(stats["final_mean_visits"])
            if stats.get("final_mean_visits") is not None
            else (
                float((stats.get("mean_visits") or [None])[-1])
                if stats.get("mean_visits")
                else None
            )
        ),
        "final_epsilon": float((stats.get("epsilon_values") or [None])[-1])
        if stats.get("epsilon_values")
        else None,
        "duration_sec": duration_sec,
        "games_per_sec": games_per_sec,
        "games_per_hour": (games_per_sec * 3600.0) if games_per_sec is not None else None,
        "num_games_planned": params.get("num_games"),
        "learning_rate": params.get("learning_rate"),
        "epsilon": params.get("epsilon"),
        "n_bootstrap_games": params.get("n_bootstrap_games"),
        "opponent_type": params.get("opponent_type"),
        "train_device": params.get("train_device"),
        "train_mode": params.get("train_mode") or stats.get("train_mode"),
    }


def archive_current_run(
    *,
    label: str | None = None,
    source: str = "local",
    force: bool = False,
    partial: bool | None = None,
) -> dict[str, Any] | None:
    """
    Snapshot current output/ artifacts into runs/<run_id>/ and update the index.
    Returns the run meta dict, or None if nothing useful to archive.

    partial=True marks a stopped/incomplete job. If None, inferred when
    games_played < planned num_games.
    """
    stats = _load_json(RL_OUTPUT / "training_stats.json")
    perf = _load_json(RL_OUTPUT / "train_perf.json") or {}
    params = (
        _load_json(RL_OUTPUT / "last_run_params.json")
        or _load_json(RL_OUTPUT / "ui_train_params.json")
        or {}
    )
    # Prefer live train_perf config when last_run_params is stale (Stop mid-run)
    perf_cfg = perf.get("config") if isinstance(perf.get("config"), dict) else {}
    if perf_cfg:
        params = {**params, **{k: v for k, v in perf_cfg.items() if v is not None}}
    if not stats and not (RL_OUTPUT / "qtable_train.csv").exists():
        return None

    scores = (stats or {}).get("scores") or []
    games = int((stats or {}).get("games_played") or len(scores) or 0)
    # train_perf may be ahead of a crashed stats write
    perf_last = perf.get("last") if isinstance(perf.get("last"), dict) else {}
    try:
        perf_games = int(perf_last.get("game") or 0)
    except (TypeError, ValueError):
        perf_games = 0
    if perf_games > games:
        games = perf_games
        if stats is not None:
            stats = {**stats, "games_played": games}

    if games <= 0 and not force:
        return None

    planned = int(params.get("num_games") or perf_cfg.get("num_games") or 0)
    if partial is None:
        partial = bool(planned and games < planned)

    # Fill wall-clock from perf when stats.total_time missing (killed process)
    if stats is not None and not stats.get("total_time"):
        try:
            elapsed = float(perf_last.get("elapsed_sec") or 0)
        except (TypeError, ValueError):
            elapsed = 0.0
        if elapsed > 0:
            stats = {
                **stats,
                "total_time": elapsed,
                "games_per_sec": games / elapsed if games else None,
            }

    now = _now_est()
    stamp = now.strftime("%Y%m%d_%I%M%S%p").lower()
    g_tag = f"{games}g" if games else "run"
    if partial:
        g_tag = f"{g_tag}_partial"
    run_id = f"{stamp}_{g_tag}"
    if label:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:40]
        run_id = f"{run_id}_{safe}"

    # Deduplicate: skip if same games_played + avg score already archived recently
    index = load_index()
    summary = _summarize_stats(stats, params)
    summary["partial"] = bool(partial)
    summary["status"] = "stopped" if partial else "completed"
    if planned:
        summary["num_games_planned"] = planned
        summary["pct_of_planned"] = round(100.0 * games / planned, 1) if planned else None

    for existing in index[:5]:
        if (
            existing.get("summary", {}).get("games_played") == summary.get("games_played")
            and existing.get("summary", {}).get("avg_score") == summary.get("avg_score")
            and existing.get("summary", {}).get("final_states") == summary.get("final_states")
            and bool(existing.get("summary", {}).get("partial")) == bool(partial)
            and not force
        ):
            return existing

    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for name in ARCHIVE_FILES:
        src = RL_OUTPUT / name
        if src.exists():
            shutil.copy2(src, run_dir / name)
            copied.append(name)

    # Copy heavy artifacts when present (optional but useful)
    for name in ("qtable_train.csv", "trajectory_train.csv"):
        src = RL_OUTPUT / name
        if src.exists() and src.stat().st_size < 80_000_000:  # skip absurdly large
            shutil.copy2(src, run_dir / name)
            copied.append(name)

    display = now.strftime("%m/%d/%Y %I:%M %p EST")
    if partial:
        display = f"{display} (partial)"

    meta = {
        "id": run_id,
        "label": label or run_id,
        "created_at": _iso(now),
        "created_at_display": display,
        "source": source,
        "partial": bool(partial),
        "params": params,
        "summary": summary,
        "files": copied,
        "has_stats": "training_stats.json" in copied,
        "has_qtable": "qtable_train.csv" in copied,
        "has_trajectory": "trajectory_train.csv" in copied,
    }
    _write_json(run_dir / "meta.json", meta)

    index = [r for r in index if r.get("id") != run_id]
    index.insert(0, meta)
    save_index(index)

    # Local machine is the DB gateway: CPU runs upload here; GPU/RunPod after pull+archive
    try:
        from data_upset import upload_rl_training_run
        db = upload_rl_training_run(meta)
        meta["supabase_uploaded"] = bool(db is not None)
    except Exception as e:
        meta["supabase_uploaded"] = False
        meta["supabase_error"] = str(e)
        print(f"Supabase RL upload skipped: {e}")

    return meta


def maybe_archive_orphaned_partial(*, source: str = "orphan") -> dict[str, Any] | None:
    """If live stats look like an unfinished run not yet indexed, archive as partial."""
    stats = _load_json(RL_OUTPUT / "training_stats.json")
    if not stats:
        return None
    games = int(stats.get("games_played") or 0)
    if games <= 0:
        return None
    perf = _load_json(RL_OUTPUT / "train_perf.json") or {}
    planned = int((perf.get("config") or {}).get("num_games") or 0)
    if not planned:
        params = _load_json(RL_OUTPUT / "ui_train_params.json") or {}
        planned = int(params.get("num_games") or 0)
    if planned and games >= planned:
        return None  # looks complete — leave for normal archive path
    # Already archived this games_played recently?
    for existing in load_index()[:8]:
        if existing.get("summary", {}).get("games_played") == games and existing.get("partial"):
            return existing
    return archive_current_run(source=source, partial=True, force=False)


def get_run(run_id: str) -> dict[str, Any] | None:
    run_dir = RUNS_DIR / run_id
    meta = _load_json(run_dir / "meta.json")
    if meta:
        return meta
    for r in load_index():
        if r.get("id") == run_id:
            return r
    return None


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    index = load_index()
    # Refresh summaries from disk metas when available
    refreshed = []
    for entry in index[:limit]:
        rid = entry.get("id")
        if not rid:
            continue
        meta = _load_json(RUNS_DIR / rid / "meta.json") or entry
        summary = dict(meta.get("summary") or {})
        stats = _load_json(RUNS_DIR / rid / "training_stats.json")
        # Recompute duration — older archives summed tailed training_times (~25s for 50k)
        dur, gps = _duration_from_stats(stats)
        if dur is not None:
            old = summary.get("duration_sec")
            summary["duration_sec"] = dur
            summary["games_per_sec"] = gps
            meta = {**meta, "summary": summary}
            # Persist corrected duration so the index stays honest
            if old is None or (isinstance(old, (int, float)) and abs(float(old) - dur) > 1.0):
                try:
                    _write_json(RUNS_DIR / rid / "meta.json", meta)
                except OSError:
                    pass
        refreshed.append(meta)
    return refreshed


def delete_run(run_id: str) -> bool:
    run_dir = RUNS_DIR / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir, ignore_errors=True)
    index = [r for r in load_index() if r.get("id") != run_id]
    save_index(index)
    return True
