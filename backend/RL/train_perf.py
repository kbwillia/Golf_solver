"""
Training performance / metadata telemetry for CPU (and future) trainers.

Writes:
  - train_perf.jsonl  — one sample per report (append-only, good for analysis)
  - train_perf.json   — rolling summary + last sample + config + counters

Goal: correlate GPS drops with Q size, RSS, traj/Q/stats write cost, coverage scans, etc.
"""
from __future__ import annotations

import json
import os
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator

from progress_io import get_output_path


def process_rss_mb() -> float | None:
    """Resident set size of this process in MiB (best-effort)."""
    try:
        import psutil  # type: ignore

        return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
    except Exception:
        pass
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
            GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
                wintypes.DWORD,
            ]
            GetProcessMemoryInfo.restype = wintypes.BOOL
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return float(counters.WorkingSetSize) / (1024.0 * 1024.0)
        except Exception:
            pass
    try:
        import resource  # Unix

        # ru_maxrss is KiB on Linux, bytes on macOS — treat Linux as default here
        rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if sys.platform == "darwin":
            return rss / (1024.0 * 1024.0)
        return rss / 1024.0
    except Exception:
        return None


def file_size_bytes(path: str) -> int | None:
    try:
        return int(os.path.getsize(path))
    except OSError:
        return None


def estimate_qtable_bytes(states: int, entries: int) -> int:
    """Rough in-memory footprint for nested dict Q (not exact)."""
    # ~200B/state overhead + ~48B/entry for key+float — heuristic only
    return int(states * 220 + entries * 48)


class TrainPerfTracker:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.t0 = time.time()
        self.config = dict(config or {})
        self.counters: dict[str, Any] = {
            "traj_flushes": 0,
            "traj_games_flushed": 0,
            "traj_flush_sec_total": 0.0,
            "q_checkpoints": 0,
            "q_checkpoint_sec_total": 0.0,
            "stats_writes": 0,
            "stats_write_sec_total": 0.0,
            "progress_writes": 0,
            "progress_write_sec_total": 0.0,
            "coverage_scans": 0,
            "coverage_scan_sec_total": 0.0,
            "offline_bc_batches": 0,
            "offline_bc_sec_total": 0.0,
            "snapshot_writes": 0,
            "snapshot_write_sec_total": 0.0,
            "samples": 0,
        }
        self._last_sample_game = 0
        self._last_sample_t = self.t0
        self.last_sample: dict[str, Any] | None = None
        self._jsonl_path = get_output_path("train_perf.jsonl")
        self._json_path = get_output_path("train_perf.json")
        # Fresh run: truncate jsonl
        try:
            with open(self._jsonl_path, "w", encoding="utf-8"):
                pass
        except OSError:
            pass
        self._write_summary(running=True)

    @contextmanager
    def timed(self, counter_prefix: str) -> Iterator[dict[str, float]]:
        """Time a block; accumulates into counters[f'{prefix}_sec_total'] and +1 count."""
        box: dict[str, float] = {"sec": 0.0}
        t1 = time.perf_counter()
        try:
            yield box
        finally:
            sec = time.perf_counter() - t1
            box["sec"] = sec
            key_n = f"{counter_prefix}s" if not counter_prefix.endswith("s") else counter_prefix
            # Prefer explicit names we already defined
            count_key = {
                "traj_flush": "traj_flushes",
                "q_checkpoint": "q_checkpoints",
                "stats_write": "stats_writes",
                "progress_write": "progress_writes",
                "coverage_scan": "coverage_scans",
                "offline_bc": "offline_bc_batches",
                "snapshot_write": "snapshot_writes",
            }.get(counter_prefix, key_n)
            sec_key = {
                "traj_flush": "traj_flush_sec_total",
                "q_checkpoint": "q_checkpoint_sec_total",
                "stats_write": "stats_write_sec_total",
                "progress_write": "progress_write_sec_total",
                "coverage_scan": "coverage_scan_sec_total",
                "offline_bc": "offline_bc_sec_total",
                "snapshot_write": "snapshot_write_sec_total",
            }.get(counter_prefix, f"{counter_prefix}_sec_total")
            self.counters[count_key] = int(self.counters.get(count_key, 0)) + 1
            self.counters[sec_key] = float(self.counters.get(sec_key, 0.0)) + sec

    def note_traj_games(self, n_games: int) -> None:
        self.counters["traj_games_flushed"] = int(self.counters.get("traj_games_flushed", 0)) + int(
            n_games
        )

    def sample(
        self,
        *,
        game: int,
        games_total: int,
        phase: str,
        states: int,
        entries: int,
        replay_len: int,
        traj_buffer_len: int = 0,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        elapsed = max(1e-6, now - self.t0)
        cum_gps = game / elapsed
        dg = max(0, game - self._last_sample_game)
        dt = max(1e-6, now - self._last_sample_t)
        inst_gps = dg / dt if self._last_sample_game > 0 else cum_gps
        self._last_sample_game = game
        self._last_sample_t = now

        rss = process_rss_mb()
        q_est = estimate_qtable_bytes(states, entries)

        paths = {
            "qtable": get_output_path("qtable_train.csv"),
            "trajectory": get_output_path("trajectory_train.csv"),
            "stats": get_output_path("training_stats.json"),
            "progress": get_output_path("training_progress.json"),
            "snapshot": get_output_path("q_snapshot.pkl"),
        }
        sizes = {k: file_size_bytes(p) for k, p in paths.items()}

        c = self.counters
        sample: dict[str, Any] = {
            "ts": now,
            "elapsed_sec": round(elapsed, 3),
            "game": int(game),
            "games_total": int(games_total),
            "pct": round(100.0 * game / games_total, 2) if games_total else 0.0,
            "phase": phase,
            "cum_gps": round(cum_gps, 3),
            "inst_gps": round(inst_gps, 3),
            "q_states": int(states),
            "q_entries": int(entries),
            "q_est_mb": round(q_est / (1024.0 * 1024.0), 2),
            "rss_mb": None if rss is None else round(rss, 1),
            "replay_len": int(replay_len),
            "traj_buffer_games": int(traj_buffer_len),
            "file_bytes": sizes,
            "io": {
                "traj_flushes": c["traj_flushes"],
                "traj_games_flushed": c["traj_games_flushed"],
                "traj_flush_sec_total": round(c["traj_flush_sec_total"], 3),
                "traj_flush_sec_avg": round(
                    c["traj_flush_sec_total"] / max(1, c["traj_flushes"]), 4
                ),
                "q_checkpoints": c["q_checkpoints"],
                "q_checkpoint_sec_total": round(c["q_checkpoint_sec_total"], 3),
                "q_checkpoint_sec_avg": round(
                    c["q_checkpoint_sec_total"] / max(1, c["q_checkpoints"]), 4
                ),
                "stats_writes": c["stats_writes"],
                "stats_write_sec_total": round(c["stats_write_sec_total"], 3),
                "progress_writes": c["progress_writes"],
                "progress_write_sec_total": round(c["progress_write_sec_total"], 3),
                "coverage_scans": c["coverage_scans"],
                "coverage_scan_sec_total": round(c["coverage_scan_sec_total"], 3),
                "coverage_scan_sec_avg": round(
                    c["coverage_scan_sec_total"] / max(1, c["coverage_scans"]), 4
                ),
                "offline_bc_batches": c["offline_bc_batches"],
                "offline_bc_sec_total": round(c["offline_bc_sec_total"], 3),
                "snapshot_writes": c["snapshot_writes"],
                "snapshot_write_sec_total": round(c["snapshot_write_sec_total"], 3),
            },
        }
        if extra:
            sample["extra"] = extra

        self.counters["samples"] = int(self.counters.get("samples", 0)) + 1
        self.last_sample = sample
        self._append_jsonl(sample)
        self._write_summary(running=game < games_total)
        return sample

    def _append_jsonl(self, sample: dict[str, Any]) -> None:
        try:
            with open(self._jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample, separators=(",", ":")) + "\n")
        except OSError as e:
            print(f"  Warning: train_perf.jsonl write failed: {e}")

    def _write_summary(self, *, running: bool) -> None:
        payload = {
            "ok": True,
            "running": running,
            "started_at": self.t0,
            "config": self.config,
            "counters": self.counters,
            "last": self.last_sample,
            "files": {
                "jsonl": self._jsonl_path,
                "json": self._json_path,
            },
        }
        try:
            with open(self._json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError as e:
            print(f"  Warning: train_perf.json write failed: {e}")

    def finalize(self) -> dict[str, Any]:
        self._write_summary(running=False)
        return {
            "config": self.config,
            "counters": dict(self.counters),
            "last": self.last_sample,
        }

    def format_log_line(self, sample: dict[str, Any] | None = None) -> str:
        s = sample or self.last_sample or {}
        rss = s.get("rss_mb")
        rss_s = f"{rss:.0f}MB" if isinstance(rss, (int, float)) else "?"
        fb = s.get("file_bytes") or {}
        q_b = fb.get("qtable")
        tr_b = fb.get("trajectory")
        q_mb = f"{q_b / (1024 * 1024):.1f}MB" if q_b is not None else "?"
        tr_mb = f"{tr_b / (1024 * 1024):.1f}MB" if tr_b is not None else "?"
        io = s.get("io") or {}
        return (
            f"  perf: inst={s.get('inst_gps', 0):.1f}gps cum={s.get('cum_gps', 0):.1f}gps "
            f"rss={rss_s} q_est={s.get('q_est_mb', 0)}MB "
            f"disk_q={q_mb} traj={tr_mb} "
            f"flush={io.get('traj_flushes', 0)} qckpt={io.get('q_checkpoints', 0)} "
            f"cov={io.get('coverage_scans', 0)} "
            f"io_sec={io.get('traj_flush_sec_total', 0) + io.get('q_checkpoint_sec_total', 0) + io.get('stats_write_sec_total', 0) + io.get('progress_write_sec_total', 0) + io.get('coverage_scan_sec_total', 0):.1f}"
        )
