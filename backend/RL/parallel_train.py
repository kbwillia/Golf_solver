#!/usr/bin/env python3
"""
Parallel CPU tabular Q-learning.

Rolls out games across a process pool, then applies Q / behavioral-clone updates
on the main process. This is the fast path for the existing dict Q-table agent.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

import numpy as np

# Path setup for backend imports
_RL_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_RL_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
if _RL_DIR not in sys.path:
    sys.path.insert(0, _RL_DIR)

from agents import QLearningAgent, EVAgent, RandomAgent, AdvancedEVAgent  # noqa: E402
from game import GolfGame  # noqa: E402
from progress_io import (  # noqa: E402
    append_progress_checkpoint,
    get_output_path,
    mark_progress_complete,
    save_training_stats_json,
)
from train import (  # noqa: E402
    save_trajectory_csv_batch,
)
from train_perf import TrainPerfTracker  # noqa: E402


def _peek_last_trajectory_game(filename: str = "trajectory_train.csv") -> int:
    """Read only the last few KB of the trajectory CSV to find max game number."""
    path = get_output_path(filename)
    if not os.path.exists(path):
        return 0
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 256_000))
            raw = f.read().decode("utf-8", errors="ignore")
    except OSError:
        return 0
    last = 0
    for line in raw.splitlines():
        if not line or line.startswith("game"):
            continue
        part = line.split(",", 1)[0]
        try:
            last = max(last, int(part))
        except ValueError:
            continue
    return last


def _terminal_reward(score: float, game_scores: list[float]) -> float:
    """Terminal reward for our agent (player 0).

    +10 if at the best score (includes any tie at the minimum, e.g. 0-0 or 5-5),
    or score == 0. Then score buckets: ≤5 → +5, ≤20 → −4, else −10.
    """
    if score == min(game_scores) or score == 0:
        return 10.0
    if score <= 5:
        return 5.0
    if score <= 20:
        return -4.0
    return -10.0


def _counts_as_win(our_score: float, opp_score: float) -> bool:
    """Win-rate counting: strict lower score, or 0-0 (treated as a win)."""
    return our_score < opp_score or (our_score == 0 and opp_score == 0)


def _q_table_to_plain(q_table) -> dict[str, dict[str, float]]:
    return {sk: dict(actions) for sk, actions in q_table.items()}


def _visits_to_plain(visit_counts) -> dict[str, dict[str, int]]:
    return {sk: {ak: int(n) for ak, n in actions.items()} for sk, actions in visit_counts.items()}


def _plain_to_q_table(plain: dict[str, dict[str, float]]):
    q = defaultdict(lambda: defaultdict(float))
    for sk, actions in (plain or {}).items():
        for ak, v in actions.items():
            q[sk][ak] = float(v)
    return q


def _plain_to_visits(plain: dict[str, dict[str, int]] | None):
    v = defaultdict(lambda: defaultdict(int))
    for sk, actions in (plain or {}).items():
        for ak, n in actions.items():
            v[sk][ak] = int(n)
    return v


# Per-worker cache: reload Q snapshot only when the file mtime changes (Priority 7)
_WORKER_Q_CACHE: dict[str, Any] = {"path": None, "mtime": None, "q": None, "visits": None}


def _load_q_snapshot(path: str):
    """Load frozen Q-table (+ optional visits) from disk; cache in this worker process."""
    global _WORKER_Q_CACHE
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(int))
    if (
        _WORKER_Q_CACHE["path"] == path
        and _WORKER_Q_CACHE["mtime"] == mtime
        and _WORKER_Q_CACHE["q"] is not None
    ):
        return _WORKER_Q_CACHE["q"], _WORKER_Q_CACHE["visits"]
    with open(path, "rb") as f:
        raw = pickle.load(f)
    if isinstance(raw, dict) and "q" in raw:
        q = _plain_to_q_table(raw.get("q") or {})
        visits = _plain_to_visits(raw.get("visits"))
    else:
        q = _plain_to_q_table(raw if isinstance(raw, dict) else {})
        visits = defaultdict(lambda: defaultdict(int))
    _WORKER_Q_CACHE = {"path": path, "mtime": mtime, "q": q, "visits": visits}
    return q, visits


def _write_q_snapshot(agent, path: str) -> None:
    """Write one shared snapshot per chunk — workers load by path (not N pickled copies)."""
    payload = {
        "q": _q_table_to_plain(agent.q_table),
        "visits": _visits_to_plain(agent.visit_counts),
    }
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


class TrajectoryReplayBuffer:
    """Tabular trajectory replay with loss prioritization (Priority 5)."""

    def __init__(self, capacity: int = 2000):
        self.buf: deque = deque(maxlen=max(1, int(capacity)))

    def add(self, traj: list, final_reward: float, score: float, won: bool, tied: bool) -> None:
        if not traj:
            return
        self.buf.append(
            {
                "traj": traj,
                "final_reward": float(final_reward),
                "score": float(score),
                "won": bool(won),
                "tied": bool(tied),
            }
        )

    def __len__(self) -> int:
        return len(self.buf)

    def sample(self, k: int = 4) -> list[dict]:
        if not self.buf or k <= 0:
            return []
        k = min(k, len(self.buf))
        # Prefer losses ~3x vs wins/ties
        weights = []
        for item in self.buf:
            if item["won"]:
                weights.append(1.0)
            elif item["tied"]:
                weights.append(1.5)
            else:
                weights.append(3.0)
        total = sum(weights)
        probs = [w / total for w in weights]
        idxs = np.random.choice(len(self.buf), size=k, replace=False, p=probs)
        return [self.buf[int(i)] for i in idxs]


def _make_opponent(opponent_type: str):
    if opponent_type == "ev_ai":
        return EVAgent(), "ev_ai"
    if opponent_type == "random":
        return RandomAgent(), "random"
    if opponent_type == "advanced_ev":
        return AdvancedEVAgent(), "advanced_ev"
    raise ValueError(f"Unsupported opponent_type for parallel CPU: {opponent_type}")


def _play_game_with_agent(agent: QLearningAgent, opponent_type: str, seed: int | None = None) -> dict[str, Any]:
    """Simulate one game; learning stays off until the main loop applies updates."""
    import random as _random

    if seed is not None:
        _random.seed(seed)
        np.random.seed(seed % (2**32 - 1))

    prev_online = getattr(agent, "online_updates", True)
    prev_train = getattr(agent, "training_mode", False)
    agent.online_updates = False
    agent.training_mode = True
    try:
        opponent, opp_type = _make_opponent(opponent_type)
        traj1: list[dict] = []
        traj2: list[dict] = []
        game = GolfGame(
            num_players=2,
            agent_types=["qlearning", opp_type],
            q_agents=[agent, opponent],
        )
        scores = game.play_game(verbose=False, trajectories=[traj1, traj2])
        return {
            "trajectory": traj1,
            "scores": [float(scores[0]), float(scores[1])],
            "bootstrapping": bool(agent.is_bootstrapping()),
        }
    finally:
        agent.online_updates = prev_online
        agent.training_mode = prev_train


def _play_worker_game(payload: dict[str, Any]) -> dict[str, Any]:
    """Play one game in a worker. Must be top-level for Windows spawn."""
    agent = QLearningAgent(
        learning_rate=payload["learning_rate"],
        discount_factor=payload["discount_factor"],
        epsilon=payload["epsilon"],
        n_bootstrap_games=payload["n_bootstrap_games"],
        reward_shaping=payload["reward_shaping"],
        exploration_beta=float(payload.get("exploration_beta", 0.5) or 0.0),
    )
    # Priority 7: load shared snapshot once per worker/chunk (cached by mtime)
    snap = payload.get("q_snapshot_path")
    if snap:
        q, visits = _load_q_snapshot(snap)
        agent.q_table = q
        agent.visit_counts = visits
    else:
        agent.q_table = _plain_to_q_table(payload.get("q_table") or {})
        agent.visit_counts = _plain_to_visits(payload.get("visits"))
    agent.games_played = int(payload["games_played"])
    try:
        from human_bootstrap import HumanDemoPolicy

        agent.human_demo_policy = HumanDemoPolicy.from_payload(payload.get("human_demo_policy"))
    except Exception:
        agent.human_demo_policy = None

    return _play_game_with_agent(agent, payload["opponent_type"], seed=payload.get("seed"))


def train_qlearning_agent_parallel(
    num_games: int = 5000,
    opponent_type: str = "ev_ai",
    verbose: bool = True,
    num_workers: int | None = None,
    learning_rate: float = 0.1,
    discount_factor: float = 0.9,
    epsilon: float = 0.2,
    epsilon_decay_factor: float = 0.995,
    n_bootstrap_games: int = 1000,
    use_imitation_learning: bool = True,
    epsilon_decay_interval: int = 100,
    progress_report_interval: int = 250,
    use_reward_shaping: bool = True,
    shape_step: float = 0.05,
    shape_pair: float = 1.5,
    shape_high_keep: float = -0.8,
    shape_low_keep: float = 0.3,
    shape_midhigh_keep: float = -0.4,
    shape_flip: float = 0.1,
    chunk_size: int | None = None,
    n_step: int = 3,
    replay_capacity: int = 2000,
    replay_per_game: int = 4,
    exploration_beta: float = 0.5,
    skip_archive: bool = False,
    save_trajectories: bool = True,
    prefer_pool: bool = False,
    save_qtable: bool = True,
    traj_flush_every: int = 100,
    q_checkpoint_every: int = 50_000,
    stats_stride: int = 100,
    stats_max_points: int = 5_000,
    coverage_every_n_reports: int = 5,
    offline_human_bc_every: int = 100,
    offline_human_bc_batch: int = 32,
) -> tuple[QLearningAgent, dict[str, Any]]:
    """
    Parallel CPU tabular Q-learning.

    Workers simulate from a shared Q snapshot file; main process applies n-step
    Q-learning (max over legal actions) + loss-prioritized trajectory replay.

    With num_workers=1, games run in-process (no pickle snapshot) — much faster
    once the Q-table is large. Set prefer_pool=True to force the snapshot path.

    I/O controls (speed / safety):
    - traj_flush_every: buffer trajectory CSV writes
    - q_checkpoint_every: periodic qtable_train.csv save
    - stats_stride / stats_max_points: downsampled series for UI JSON
    - coverage_every_n_reports: full coverage scan cadence
    - offline_human_bc_*: batch BC from demos (not live state match)
    """
    cpu_n = os.cpu_count() or 4
    if num_workers is None or num_workers <= 0:
        num_workers = max(2, cpu_n)
    num_workers = max(1, int(num_workers))
    if chunk_size is None or chunk_size <= 0:
        chunk_size = max(num_workers, num_workers * 2)
    chunk_size = max(1, int(chunk_size))
    n_step = max(1, int(n_step))
    replay_per_game = max(0, int(replay_per_game))
    exploration_beta = float(exploration_beta)
    in_process = num_workers == 1 and not prefer_pool
    traj_flush_every = max(1, int(traj_flush_every or 100))
    q_checkpoint_every = max(0, int(q_checkpoint_every or 0))
    stats_stride = max(1, int(stats_stride or 100))
    stats_max_points = max(100, int(stats_max_points or 5000))
    coverage_every_n_reports = max(1, int(coverage_every_n_reports or 5))
    offline_human_bc_every = max(0, int(offline_human_bc_every or 0))
    offline_human_bc_batch = max(1, int(offline_human_bc_batch or 32))

    bootstrap_n = n_bootstrap_games if use_imitation_learning else 0
    reward_shaping = {
        "enabled": bool(use_reward_shaping),
        "step": float(shape_step),
        "pair": float(shape_pair),
        "high_keep": float(shape_high_keep),
        "low_keep": float(shape_low_keep),
        "midhigh_keep": float(shape_midhigh_keep),
        "flip": float(shape_flip),
    }

    print("=" * 70)
    print("PARALLEL CPU Q-LEARNING TRAINING")
    print("=" * 70)
    print(f"Workers: {num_workers} (cpu_count={cpu_n})")
    print(f"Chunk size: {chunk_size}")
    print(f"Games: {num_games} | opponent={opponent_type}")
    print(f"Bootstrap: {bootstrap_n} | epsilon={epsilon}")
    print(f"n-step: {n_step} | replay_per_game: {replay_per_game} (cap={replay_capacity}) | visit beta={exploration_beta}")
    if in_process:
        print("Q sharing: in-process (workers=1; no snapshot I/O)")
    else:
        print("Q sharing: snapshot file (one write/chunk; workers cache by mtime)")
    if save_trajectories:
        print(f"Trajectories: buffered flush every {traj_flush_every} games")
    else:
        print("Trajectories: off")
    print(
        f"I/O: q_ckpt every {q_checkpoint_every or 'off'} | "
        f"stats stride={stats_stride} cap={stats_max_points} | "
        f"coverage every {coverage_every_n_reports} reports"
    )
    if offline_human_bc_every > 0:
        print(
            f"Offline human BC: every {offline_human_bc_every} games, "
            f"batch={offline_human_bc_batch}"
        )

    try:
        from human_bootstrap import load_human_demo_policy

        human_demo_policy = load_human_demo_policy(refresh=True)
    except Exception as e:
        print(f"Human demo policy unavailable: {e}")
        from human_bootstrap import HumanDemoPolicy

        human_demo_policy = HumanDemoPolicy()
    human_payload = human_demo_policy.to_payload() if human_demo_policy else {}
    if human_demo_policy:
        print(
            f"Human demos: {human_demo_policy.steps} weighted steps / "
            f"{human_demo_policy.holes} holes "
            f"({len(human_demo_policy.exact)} exact keys, source={human_demo_policy.source})"
        )
    else:
        print("Human demos: none — bootstrap will use EV only")

    agent = QLearningAgent(
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        n_bootstrap_games=bootstrap_n,
        reward_shaping=reward_shaping,
        exploration_beta=exploration_beta,
    )
    agent.human_demo_policy = human_demo_policy
    agent.load_q_table_csv()

    offline_bc_steps: list[tuple[str, str, float]] = []
    if offline_human_bc_every > 0:
        try:
            from human_bootstrap import load_offline_bc_steps

            offline_bc_steps = load_offline_bc_steps()
            print(f"Offline BC pool: {len(offline_bc_steps)} weighted demo steps")
        except Exception as e:
            print(f"Offline BC pool unavailable: {e}")
            offline_bc_steps = []

    # Do NOT load the full trajectory CSV into memory (can be 90MB+).
    last_game_num = _peek_last_trajectory_game()
    replay = TrajectoryReplayBuffer(capacity=replay_capacity)
    snapshot_path = get_output_path("q_snapshot.pkl")
    print(f"Trajectory resume index: last_game_num={last_game_num}")
    training_stats: dict[str, Any] = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "scores": [],
        "opponent_scores": [],
        "qtable_states": [],
        "qtable_entries": [],
        "epsilon_values": [],
        "training_times": [],
        "completion_pct": [],
        "sparsity_index": [],
        "mean_visits": [],
        "train_device": "cpu",
        "train_mode": "tabular_parallel",
        "n_step": n_step,
        "replay_per_game": replay_per_game,
        "exploration_beta": exploration_beta,
    }
    score_sum = 0.0
    score_count = 0

    # Clear live progress for this run
    progress_path = get_output_path("training_progress.json")
    with open(progress_path, "w", encoding="utf-8") as f:
        json.dump({"ok": True, "running": True, "checkpoints": [], "series": {
            "games": [], "avg_scores": [], "qtable_states": [], "epsilon": [], "win_rates": [],
            "completion_pct": [], "sparsity_index": [],
        }, "summary": {}}, f)

    games_done = 0
    t0 = time.time()
    last_cov = {
        "completion_pct": 0.0,
        "sparsity_index": 1.0,
        "mean_visits": 0.0,
    }
    report_count = 0
    traj_buffer: list[tuple[list, int]] = []
    perf = TrainPerfTracker(
        config={
            "num_games": num_games,
            "num_workers": num_workers,
            "chunk_size": chunk_size,
            "in_process": in_process,
            "replay_per_game": replay_per_game,
            "replay_capacity": replay_capacity,
            "n_step": n_step,
            "progress_report_interval": progress_report_interval,
            "traj_flush_every": traj_flush_every,
            "q_checkpoint_every": q_checkpoint_every,
            "stats_stride": stats_stride,
            "stats_max_points": stats_max_points,
            "coverage_every_n_reports": coverage_every_n_reports,
            "offline_human_bc_every": offline_human_bc_every,
            "offline_human_bc_batch": offline_human_bc_batch,
            "save_trajectories": save_trajectories,
            "save_qtable": save_qtable,
            "n_bootstrap_games": bootstrap_n,
        }
    )

    def _flush_traj_buffer(*, force: bool = False) -> None:
        if not save_trajectories:
            traj_buffer.clear()
            return
        if not traj_buffer:
            return
        if not force and len(traj_buffer) < traj_flush_every:
            return
        n_games = len(traj_buffer)
        try:
            with perf.timed("traj_flush"):
                save_trajectory_csv_batch(traj_buffer)
            perf.note_traj_games(n_games)
        except OSError as e:
            print(f"  Warning: trajectory flush failed: {e}")
        traj_buffer.clear()

    def _trim_series() -> None:
        for key in (
            "scores",
            "opponent_scores",
            "qtable_states",
            "qtable_entries",
            "epsilon_values",
            "training_times",
            "completion_pct",
            "sparsity_index",
            "mean_visits",
        ):
            arr = training_stats.get(key)
            if isinstance(arr, list) and len(arr) > stats_max_points:
                training_stats[key] = arr[-stats_max_points:]

    def _maybe_offline_bc() -> None:
        if offline_human_bc_every <= 0 or not offline_bc_steps:
            return
        if games_done % offline_human_bc_every != 0:
            return
        try:
            from human_bootstrap import sample_offline_bc_batch

            with perf.timed("offline_bc"):
                batch = sample_offline_bc_batch(offline_bc_steps, k=offline_human_bc_batch)
                for sk, ak in batch:
                    agent.behavioral_clone(sk, ak, target=1.0)
        except Exception as e:
            print(f"  Warning: offline BC failed: {e}")

    def _maybe_q_checkpoint() -> None:
        if not save_qtable or q_checkpoint_every <= 0:
            return
        if games_done % q_checkpoint_every != 0:
            return
        try:
            print(f"  Q checkpoint at game {games_done} ...")
            with perf.timed("q_checkpoint"):
                agent.save_q_table_csv()
        except OSError as e:
            print(f"  Warning: Q checkpoint failed: {e}")

    def _consume_result(result: dict[str, Any], batch_start: float, batch_n: int) -> None:
        nonlocal games_done, last_cov, score_sum, score_count
        traj = result["trajectory"]
        scores = result["scores"]
        games_done += 1
        agent.games_played = games_done  # keep bootstrap boundary in sync
        current_game_num = last_game_num + games_done

        won = _counts_as_win(scores[0], scores[1])
        tied = (scores[0] == scores[1]) and not won
        if won:
            training_stats["wins"] += 1
        elif not tied:
            training_stats["losses"] += 1

        reward = _terminal_reward(scores[0], scores)
        if traj:
            if result.get("bootstrapping") and use_imitation_learning:
                for step in traj:
                    agent.behavioral_clone(step["state_key"], step["action_key"], target=1.0)
            agent.train_on_trajectory(traj, reward, scores[0], n_step=n_step)
            replay.add(traj, reward, scores[0], won=won, tied=tied)
            for sample in replay.sample(replay_per_game):
                agent.train_on_trajectory(
                    sample["traj"],
                    sample["final_reward"],
                    sample["score"],
                    n_step=n_step,
                )
            if save_trajectories:
                traj_buffer.append((traj, current_game_num))
                _flush_traj_buffer()

        score_sum += float(scores[0])
        score_count += 1
        training_stats["games_played"] = games_done

        # Downsampled series — not every game (keeps RAM + JSON writes small)
        if games_done % stats_stride == 0 or games_done >= num_games:
            states, entries = agent.get_q_table_size()
            training_stats["scores"].append(scores[0])
            training_stats["opponent_scores"].append(scores[1])
            training_stats["qtable_states"].append(states)
            training_stats["qtable_entries"].append(entries)
            training_stats["completion_pct"].append(last_cov["completion_pct"])
            training_stats["sparsity_index"].append(last_cov["sparsity_index"])
            training_stats["mean_visits"].append(last_cov["mean_visits"])
            training_stats["epsilon_values"].append(agent.epsilon)
            training_stats["training_times"].append((time.time() - batch_start) / max(1, batch_n))
            _trim_series()

        if epsilon_decay_interval and games_done % epsilon_decay_interval == 0:
            agent.decay_epsilon(factor=epsilon_decay_factor)

        _maybe_offline_bc()
        _maybe_q_checkpoint()

    def _maybe_report(batch_n: int) -> None:
        nonlocal last_cov, report_count
        if not (
            verbose
            and (
                games_done % progress_report_interval < batch_n
                or games_done >= num_games
            )
        ):
            return
        report_count += 1
        win_rate = training_stats["wins"] / max(1, games_done)
        avg_score = float(score_sum / max(1, score_count))
        states, entries = agent.get_q_table_size()
        if (
            (report_count - 1) % coverage_every_n_reports == 0
            or games_done >= num_games
        ):
            with perf.timed("coverage_scan"):
                last_cov = agent.get_coverage_stats()
            if training_stats["completion_pct"]:
                training_stats["completion_pct"][-1] = last_cov["completion_pct"]
                training_stats["sparsity_index"][-1] = last_cov["sparsity_index"]
                training_stats["mean_visits"][-1] = last_cov["mean_visits"]
        phase = "BOOTSTRAP" if games_done < bootstrap_n else "Q-LEARNING"
        elapsed = time.time() - t0
        gps = games_done / max(1e-6, elapsed)
        training_stats["total_time"] = float(elapsed)
        training_stats["games_per_sec"] = float(gps)
        training_stats["final_completion_pct"] = last_cov["completion_pct"]
        training_stats["final_sparsity_index"] = last_cov["sparsity_index"]
        training_stats["final_mean_visits"] = last_cov["mean_visits"]
        print(
            f"  Game {games_done}: {phase} | Win rate={win_rate:.2%}, "
            f"Avg score={avg_score:.2f}, States={states}, "
            f"Coverage={last_cov['completion_pct']:.2%} sparse={last_cov['sparsity_index']:.2f}, "
            f"Epsilon={agent.epsilon:.3f}, {gps:.1f} games/s | replay={len(replay)}"
        )
        try:
            with perf.timed("stats_write"):
                save_training_stats_json(training_stats)
            with perf.timed("progress_write"):
                append_progress_checkpoint(
                    game=games_done,
                    games_total=num_games,
                    phase=phase,
                    win_rate=win_rate,
                    avg_score=avg_score,
                    states=states,
                    epsilon=agent.epsilon,
                    completion_pct=last_cov["completion_pct"],
                    sparsity_index=last_cov["sparsity_index"],
                    mean_visits=last_cov["mean_visits"],
                )
        except OSError as e:
            print(f"  Warning: progress write failed (training continues): {e}")
        try:
            sample = perf.sample(
                game=games_done,
                games_total=num_games,
                phase=phase,
                states=states,
                entries=entries,
                replay_len=len(replay),
                traj_buffer_len=len(traj_buffer),
            )
            # Log perf every report early, then every 5th (keeps console readable)
            if report_count <= 3 or report_count % 5 == 0 or games_done >= num_games:
                print(perf.format_log_line(sample))
        except Exception as e:
            print(f"  Warning: perf sample failed: {e}")

    if in_process:
        while games_done < num_games:
            batch_n = min(chunk_size, num_games - games_done)
            batch_start = time.time()
            for i in range(batch_n):
                seed = int(time.time() * 1000) % 1_000_000_007 + games_done + i
                result = _play_game_with_agent(agent, opponent_type, seed=seed)
                _consume_result(result, batch_start, batch_n)
            _maybe_report(batch_n)
    else:
        with ProcessPoolExecutor(max_workers=num_workers) as pool:
            while games_done < num_games:
                batch_n = min(chunk_size, num_games - games_done)
                with perf.timed("snapshot_write"):
                    _write_q_snapshot(agent, snapshot_path)
                payloads = []
                for i in range(batch_n):
                    payloads.append({
                        "q_snapshot_path": snapshot_path,
                        "learning_rate": learning_rate,
                        "discount_factor": discount_factor,
                        "epsilon": agent.epsilon,
                        "n_bootstrap_games": bootstrap_n,
                        "games_played": agent.games_played,
                        "opponent_type": opponent_type,
                        "reward_shaping": reward_shaping,
                        "human_demo_policy": human_payload,
                        "exploration_beta": exploration_beta,
                        "seed": int(time.time() * 1000) % 1_000_000_007 + games_done + i,
                    })

                batch_start = time.time()
                futures = [pool.submit(_play_worker_game, p) for p in payloads]
                results = [fut.result() for fut in as_completed(futures)]
                for result in results:
                    _consume_result(result, batch_start, batch_n)
                _maybe_report(batch_n)

    _flush_traj_buffer(force=True)

    final_states, final_entries = agent.get_q_table_size()
    with perf.timed("coverage_scan"):
        cov = agent.get_coverage_stats()
    win_rate = training_stats["wins"] / max(1, num_games)
    avg_score = float(score_sum / max(1, score_count))
    total_time = time.time() - t0
    training_stats["total_time"] = float(total_time)
    training_stats["games_per_sec"] = float(num_games / max(1e-6, total_time))
    training_stats["final_completion_pct"] = cov["completion_pct"]
    training_stats["final_sparsity_index"] = cov["sparsity_index"]
    training_stats["final_mean_visits"] = cov["mean_visits"]
    print("\nPARALLEL CPU TRAINING COMPLETE")
    print(f"  Games: {num_games} | workers={num_workers}")
    print(f"  Win rate: {win_rate:.2%}")
    print(f"  Avg score: {avg_score:.2f}")
    print(f"  Q-table: {final_states} states, {final_entries} entries")
    print(
        f"  Coverage: {cov['completion_pct']:.2%} well-visited "
        f"(sparsity={cov['sparsity_index']:.3f}, mean N={cov['mean_visits']:.1f})"
    )
    print(f"  Time: {total_time:.1f}s ({num_games / max(1e-6, total_time):.1f} games/s)")

    if save_qtable:
        with perf.timed("q_checkpoint"):
            agent.save_q_table_csv()
    try:
        final_sample = perf.sample(
            game=num_games,
            games_total=num_games,
            phase="DONE",
            states=final_states,
            entries=final_entries,
            replay_len=len(replay),
            traj_buffer_len=0,
        )
        print(perf.format_log_line(final_sample))
        perf_summary = perf.finalize()
        training_stats["perf"] = {
            "counters": perf_summary.get("counters"),
            "last": perf_summary.get("last"),
        }
        with open(get_output_path("last_run_perf.json"), "w", encoding="utf-8") as f:
            json.dump(perf_summary, f, indent=2)
    except Exception as e:
        print(f"  Warning: perf finalize failed: {e}")
    with perf.timed("stats_write"):
        save_training_stats_json(training_stats)
    with perf.timed("progress_write"):
        append_progress_checkpoint(
            game=num_games,
            games_total=num_games,
            phase="DONE",
            win_rate=win_rate,
            avg_score=avg_score,
            states=final_states,
            epsilon=agent.epsilon,
            completion_pct=cov["completion_pct"],
            sparsity_index=cov["sparsity_index"],
            mean_visits=cov["mean_visits"],
        )
    mark_progress_complete()

    params_path = get_output_path("last_run_params.json")
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump({
            "num_games": num_games,
            "num_workers": num_workers,
            "train_device": "cpu",
            "train_mode": "tabular_parallel",
            "opponent_type": opponent_type,
            "learning_rate": learning_rate,
            "discount_factor": discount_factor,
            "epsilon": epsilon,
            "epsilon_decay_factor": epsilon_decay_factor,
            "n_bootstrap_games": bootstrap_n,
            "use_imitation_learning": use_imitation_learning,
            "epsilon_decay_interval": epsilon_decay_interval,
            "progress_report_interval": progress_report_interval,
            "use_reward_shaping": use_reward_shaping,
            "shape_step": shape_step,
            "shape_pair": shape_pair,
            "shape_high_keep": shape_high_keep,
            "shape_low_keep": shape_low_keep,
            "shape_midhigh_keep": shape_midhigh_keep,
            "shape_flip": shape_flip,
            "n_step": n_step,
            "replay_capacity": replay_capacity,
            "replay_per_game": replay_per_game,
            "exploration_beta": exploration_beta,
            "chunk_size": chunk_size,
            "traj_flush_every": traj_flush_every,
            "q_checkpoint_every": q_checkpoint_every,
            "stats_stride": stats_stride,
            "offline_human_bc_every": offline_human_bc_every,
            "offline_human_bc_batch": offline_human_bc_batch,
        }, f, indent=2)

    # Archive locally + upload summary to Supabase (this machine is the DB gateway)
    if not skip_archive:
        try:
            backend = os.path.dirname(_RL_DIR)
            if backend not in sys.path:
                sys.path.insert(0, backend)
            from rl_runs import archive_current_run
            meta = archive_current_run(source="local_cpu", force=True)
            if meta:
                print(f"Archived + DB upload: {meta.get('id')} (supabase={meta.get('supabase_uploaded')})")
        except Exception as e:
            print(f"Archive/DB upload skipped: {e}")

    return agent, training_stats


def _params_from_env_or_args() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Parallel CPU Q-learning trainer")
    parser.add_argument("--games", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--params-json", type=str, default=None)
    args = parser.parse_args()

    params: dict[str, Any] = {}
    ui_path = get_output_path("ui_train_params.json")
    src = args.params_json or (ui_path if os.path.exists(ui_path) else None)
    if src and os.path.exists(src):
        with open(src, encoding="utf-8") as f:
            params.update(json.load(f))
    if args.games is not None:
        params["num_games"] = args.games
    if args.workers is not None:
        params["num_workers"] = args.workers
    # Env overrides (used by local launcher)
    if os.environ.get("NUM_GAMES"):
        params["num_games"] = int(os.environ["NUM_GAMES"])
    if os.environ.get("NUM_WORKERS"):
        params["num_workers"] = int(os.environ["NUM_WORKERS"])
    return params


def _clear_local_pid_file() -> None:
    try:
        pid_path = get_output_path("local_train.pid")
        if os.path.exists(pid_path):
            os.remove(pid_path)
    except OSError:
        pass


if __name__ == "__main__":
    try:
        p = _params_from_env_or_args()
        train_qlearning_agent_parallel(
            num_games=int(p.get("num_games", 5000)),
            opponent_type=str(p.get("opponent_type", "ev_ai")),
            verbose=True,
            num_workers=int(p.get("num_workers") or 0) or None,
            learning_rate=float(p.get("learning_rate", 0.1)),
            discount_factor=float(p.get("discount_factor", 0.9)),
            epsilon=float(p.get("epsilon", 0.2)),
            epsilon_decay_factor=float(p.get("epsilon_decay_factor", 0.995)),
            n_bootstrap_games=int(p.get("n_bootstrap_games", 1000)),
            use_imitation_learning=bool(p.get("use_imitation_learning", True)),
            epsilon_decay_interval=int(p.get("epsilon_decay_interval", 100)),
            progress_report_interval=int(p.get("progress_report_interval", 250)),
            use_reward_shaping=bool(p.get("use_reward_shaping", True)),
            shape_step=float(p.get("shape_step", 0.05)),
            shape_pair=float(p.get("shape_pair", 1.5)),
            shape_high_keep=float(p.get("shape_high_keep", -0.8)),
            shape_low_keep=float(p.get("shape_low_keep", 0.3)),
            shape_midhigh_keep=float(p.get("shape_midhigh_keep", -0.4)),
            shape_flip=float(p.get("shape_flip", 0.1)),
            n_step=int(p.get("n_step", 3)),
            replay_capacity=int(p.get("replay_capacity", 2000)),
            replay_per_game=int(p.get("replay_per_game", 4)),
            exploration_beta=float(p.get("exploration_beta", 0.5)),
            chunk_size=int(p["chunk_size"]) if p.get("chunk_size") not in (None, "", 0, "0") else None,
            save_trajectories=bool(p.get("save_trajectories", True)),
            traj_flush_every=int(p.get("traj_flush_every", 100)),
            q_checkpoint_every=int(p.get("q_checkpoint_every", 50_000)),
            stats_stride=int(p.get("stats_stride", 100)),
            stats_max_points=int(p.get("stats_max_points", 5_000)),
            coverage_every_n_reports=int(p.get("coverage_every_n_reports", 5)),
            offline_human_bc_every=int(p.get("offline_human_bc_every", 100)),
            offline_human_bc_batch=int(p.get("offline_human_bc_batch", 32)),
        )
    finally:
        _clear_local_pid_file()
