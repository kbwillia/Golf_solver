#!/usr/bin/env python3
"""CPU tabular throughput sweep (games/sec).

Isolates I/O under RL/output/cpu_sweep/ via RL_OUTPUT_DIR so a live training
run is not disturbed. Seeds each config from a pickle of the live Q-table so
results reflect the large-table regime (~1 gps today), not an empty warm-start.

Writes:
  RL/output/cpu_param_sweep.json
  RL/output/cpu_sweep/ (scratch)
"""
from __future__ import annotations

import json
import os
import pickle
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

_RL_DIR = Path(__file__).resolve().parent
_BACKEND = _RL_DIR.parent
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_RL_DIR))

LIVE_OUT = _RL_DIR / "output"
SWEEP_OUT = LIVE_OUT / "cpu_sweep"
RESULT_PATH = LIVE_OUT / "cpu_param_sweep.json"
SEED_PKL = SWEEP_OUT / "qtable_seed.pkl"

GAMES = int(os.environ.get("SWEEP_GAMES", "40"))

# (workers, chunk_size, replay_per_game, prefer_pool)
COMBOS: list[tuple[int, int, int, bool]] = [
    (1, 2, 4, True),   # old snapshot baseline
    (1, 16, 0, False),  # in-process
    (1, 16, 4, False),
    (1, 64, 4, False),
    (2, 4, 4, False),
    (2, 16, 4, False),
    (2, 64, 4, False),
    (2, 64, 0, False),
    (4, 8, 4, False),
    (4, 32, 4, False),
    (4, 64, 4, False),
    (4, 64, 0, False),
]


def _build_seed_pkl() -> bool:
    SWEEP_OUT.mkdir(parents=True, exist_ok=True)
    if SEED_PKL.exists() and SEED_PKL.stat().st_size > 1000:
        print(f"Using existing seed {SEED_PKL}")
        return True

    live_snap = LIVE_OUT / "q_snapshot.pkl"
    live_csv = LIVE_OUT / "qtable_train.csv"
    if live_snap.exists() and live_snap.stat().st_size > 1000:
        print(f"Copying live snapshot -> {SEED_PKL}")
        shutil.copy2(live_snap, SEED_PKL)
        return True

    if not live_csv.exists():
        print("WARNING: no live Q-table/snapshot — empty-table sweep")
        return False

    print(f"Building seed pickle from {live_csv} (one-time, slow) ...")
    t0 = time.time()
    q: dict = {}
    visits: dict = {}
    import csv

    with open(live_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 3:
                continue
            sk, ak, qv = row[0], row[1], row[2]
            q.setdefault(sk, {})[ak] = float(qv)
            if len(row) >= 4 and row[3] != "":
                visits.setdefault(sk, {})[ak] = int(float(row[3]))
    with open(SEED_PKL, "wb") as f:
        pickle.dump({"q": q, "visits": visits}, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"  seed ready in {time.time() - t0:.1f}s ({SEED_PKL.stat().st_size / 1e6:.1f} MB)")
    return True


def _clear_run_artifacts() -> None:
    for name in (
        "q_snapshot.pkl",
        "q_snapshot.pkl.tmp",
        "training_progress.json",
        "training_stats.json",
        "trajectory_train.csv",
        "last_run_params.json",
        "local_train.pid",
        "qtable_train.csv",
    ):
        p = SWEEP_OUT / name
        if p.exists():
            p.unlink()


def _install_fast_q_loader() -> None:
    """Load seed pickle instead of CSV so each config starts warm quickly."""
    from agents import QLearningAgent

    def load_q_table_csv(self, filename="qtable_train.csv"):  # noqa: ARG001
        if not SEED_PKL.exists():
            print("No seed pickle — starting fresh")
            return
        t0 = time.time()
        with open(SEED_PKL, "rb") as f:
            raw = pickle.load(f)
        q_plain = raw.get("q") if isinstance(raw, dict) else raw
        v_plain = raw.get("visits") if isinstance(raw, dict) else {}
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.visit_counts = defaultdict(lambda: defaultdict(int))
        for sk, actions in (q_plain or {}).items():
            for ak, qv in actions.items():
                self.q_table[sk][ak] = float(qv)
        for sk, actions in (v_plain or {}).items():
            for ak, n in actions.items():
                self.visit_counts[sk][ak] = int(n)
        print(
            f"Loaded seed Q ({len(self.q_table)} states) from {SEED_PKL} "
            f"in {time.time() - t0:.1f}s"
        )

    QLearningAgent.load_q_table_csv = load_q_table_csv  # type: ignore[method-assign]


def main() -> None:
    os.environ["RL_OUTPUT_DIR"] = str(SWEEP_OUT)
    seeded = _build_seed_pkl()
    _install_fast_q_loader()

    from parallel_train import train_qlearning_agent_parallel  # noqa: E402

    results: list[dict] = []
    print("=" * 70)
    print(f"CPU THROUGHPUT SWEEP — {GAMES} games/config")
    print(f"Scratch dir: {SWEEP_OUT} | seeded={seeded}")
    print("=" * 70)

    for workers, chunk, replay, prefer_pool in COMBOS:
        _clear_run_artifacts()
        cfg = {
            "num_workers": workers,
            "chunk_size": chunk,
            "replay_per_game": replay,
            "prefer_pool": prefer_pool,
            "mode": "pool_snapshot" if (workers > 1 or prefer_pool) else "in_process",
        }
        print(f"\n>>> {cfg}")
        t0 = time.time()
        try:
            _, stats = train_qlearning_agent_parallel(
                num_games=GAMES,
                opponent_type="ev_ai",
                verbose=False,
                num_workers=workers,
                chunk_size=chunk,
                learning_rate=0.05,
                discount_factor=0.9,
                epsilon=0.2,
                epsilon_decay_factor=0.995,
                n_bootstrap_games=0,
                use_imitation_learning=False,
                epsilon_decay_interval=100,
                progress_report_interval=GAMES,
                use_reward_shaping=True,
                n_step=3,
                replay_capacity=2000,
                replay_per_game=replay,
                exploration_beta=0.5,
                skip_archive=True,
                save_trajectories=False,
                prefer_pool=prefer_pool,
                save_qtable=False,
            )
            gps = float(stats.get("games_per_sec") or 0)
            dur = float(stats.get("total_time") or (time.time() - t0))
            states = (stats.get("qtable_states") or [0])[-1] if stats.get("qtable_states") else 0
            row = {
                **cfg,
                "games_per_sec": gps,
                "duration_sec": dur,
                "wall_sec": time.time() - t0,
                "final_states": int(states or 0),
                "ok": True,
                "error": None,
            }
        except Exception as e:
            row = {
                **cfg,
                "games_per_sec": 0.0,
                "duration_sec": time.time() - t0,
                "wall_sec": time.time() - t0,
                "final_states": 0,
                "ok": False,
                "error": str(e),
            }
            print(f"    FAILED: {e}")
        results.append(row)
        if row["ok"]:
            print(
                f"    gps={row['games_per_sec']:.2f}  "
                f"wall={row['wall_sec']:.1f}s  states={row['final_states']}"
            )
        # Persist partial results so a crash still leaves a ranking
        ranked = sorted(results, key=lambda r: (-(r["games_per_sec"] or 0), r["wall_sec"]))
        RESULT_PATH.write_text(
            json.dumps(
                {
                    "games_per_config": GAMES,
                    "seeded_from_live_qtable": seeded,
                    "results": results,
                    "ranked": ranked,
                    "recommendation": ranked[0] if ranked else None,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    ranked = sorted(results, key=lambda r: (-(r["games_per_sec"] or 0), r["wall_sec"]))
    print("\n" + "=" * 70)
    print("RANKED BY games/sec")
    for i, r in enumerate(ranked, 1):
        status = "OK" if r["ok"] else f"FAIL:{r['error']}"
        print(
            f"  {i:2d}. {r['games_per_sec']:6.2f} gps | "
            f"w={r['num_workers']} chunk={r['chunk_size']} replay={r['replay_per_game']} "
            f"mode={r['mode']} | {status}"
        )
    best = ranked[0] if ranked else None
    if best and best["ok"]:
        print(
            f"\nRECOMMEND: workers={best['num_workers']} chunk_size={best['chunk_size']} "
            f"replay_per_game={best['replay_per_game']} "
            f"(~{best['games_per_sec']:.1f} gps on large Q)"
        )
    print(f"Wrote {RESULT_PATH}")


if __name__ == "__main__":
    main()
