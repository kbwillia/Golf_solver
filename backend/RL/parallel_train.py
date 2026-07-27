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
import sys
import time
from collections import defaultdict
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
    load_trajectory_csv,
    save_trajectory_csv,
    save_trajectory_csv_full,
)


def _terminal_reward(score: float, game_scores: list[float]) -> float:
    is_winner = score == min(game_scores)
    if is_winner:
        return 10.0
    if score == 0:
        return 10.0
    if score <= 5:
        return 5.0
    if score <= 20:
        return -4.0
    return -10.0


def _q_table_to_plain(q_table) -> dict[str, dict[str, float]]:
    return {sk: dict(actions) for sk, actions in q_table.items()}


def _plain_to_q_table(plain: dict[str, dict[str, float]]):
    q = defaultdict(lambda: defaultdict(float))
    for sk, actions in (plain or {}).items():
        for ak, v in actions.items():
            q[sk][ak] = float(v)
    return q


def _make_opponent(opponent_type: str):
    if opponent_type == "ev_ai":
        return EVAgent(), "ev_ai"
    if opponent_type == "random":
        return RandomAgent(), "random"
    if opponent_type == "advanced_ev":
        return AdvancedEVAgent(), "advanced_ev"
    raise ValueError(f"Unsupported opponent_type for parallel CPU: {opponent_type}")


def _play_worker_game(payload: dict[str, Any]) -> dict[str, Any]:
    """Play one game in a worker. Must be top-level for Windows spawn."""
    import random as _random

    seed = payload.get("seed")
    if seed is not None:
        _random.seed(seed)
        np.random.seed(seed % (2**32 - 1))

    agent = QLearningAgent(
        learning_rate=payload["learning_rate"],
        discount_factor=payload["discount_factor"],
        epsilon=payload["epsilon"],
        n_bootstrap_games=payload["n_bootstrap_games"],
        reward_shaping=payload["reward_shaping"],
    )
    agent.q_table = _plain_to_q_table(payload.get("q_table") or {})
    agent.games_played = int(payload["games_played"])
    agent.online_updates = False  # main process owns learning updates
    agent.training_mode = True

    opponent, opp_type = _make_opponent(payload["opponent_type"])
    agents = [agent, opponent]
    agent_types = ["qlearning", opp_type]

    traj1: list[dict] = []
    traj2: list[dict] = []
    game = GolfGame(num_players=2, agent_types=agent_types, q_agents=agents)
    scores = game.play_game(verbose=False, trajectories=[traj1, traj2])
    return {
        "trajectory": traj1,
        "scores": [float(scores[0]), float(scores[1])],
        "bootstrapping": bool(agent.is_bootstrapping()),
    }


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
) -> tuple[QLearningAgent, dict[str, Any]]:
    """
    Parallel CPU tabular Q-learning.

    Workers simulate games with a frozen Q snapshot; the main process merges
    trajectory updates (BC during bootstrap, Q-learning after).
    """
    cpu_n = os.cpu_count() or 4
    if num_workers is None or num_workers <= 0:
        num_workers = max(2, cpu_n)
    num_workers = max(1, int(num_workers))
    if chunk_size is None or chunk_size <= 0:
        chunk_size = max(num_workers, num_workers * 2)

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

    agent = QLearningAgent(
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        n_bootstrap_games=bootstrap_n,
        reward_shaping=reward_shaping,
    )
    agent.load_q_table_csv()

    trajectory, last_game_num = load_trajectory_csv()
    new_trajectory_steps: list[dict] = []

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
        "train_device": "cpu",
        "train_mode": "tabular_parallel",
    }

    # Clear live progress for this run
    progress_path = get_output_path("training_progress.json")
    with open(progress_path, "w", encoding="utf-8") as f:
        json.dump({"ok": True, "running": True, "checkpoints": [], "series": {
            "games": [], "avg_scores": [], "qtable_states": [], "epsilon": [], "win_rates": []
        }, "summary": {}}, f)

    games_done = 0
    t0 = time.time()
    # Windows-friendly spawn pool
    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        while games_done < num_games:
            batch_n = min(chunk_size, num_games - games_done)
            q_plain = _q_table_to_plain(agent.q_table)
            payloads = []
            for i in range(batch_n):
                payloads.append({
                    "q_table": q_plain,
                    "learning_rate": learning_rate,
                    "discount_factor": discount_factor,
                    "epsilon": agent.epsilon,
                    "n_bootstrap_games": bootstrap_n,
                    "games_played": agent.games_played,
                    "opponent_type": opponent_type,
                    "reward_shaping": reward_shaping,
                    "seed": int(time.time() * 1000) % 1_000_000_007 + games_done + i,
                })

            batch_start = time.time()
            futures = [pool.submit(_play_worker_game, p) for p in payloads]
            results = [fut.result() for fut in as_completed(futures)]
            # Preserve roughly submission order for reproducibility of stats length
            # (as_completed is unordered — fine for learning)
            for result in results:
                traj = result["trajectory"]
                scores = result["scores"]
                games_done += 1
                agent.games_played = games_done  # keep bootstrap boundary in sync
                current_game_num = last_game_num + games_done

                won = scores[0] < scores[1]
                tied = scores[0] == scores[1]
                if won:
                    training_stats["wins"] += 1
                elif not tied:
                    training_stats["losses"] += 1

                reward = _terminal_reward(scores[0], scores)
                if traj:
                    if result.get("bootstrapping") and use_imitation_learning:
                        for step in traj:
                            agent.behavioral_clone(step["state_key"], step["action_key"], target=1.0)
                    agent.train_on_trajectory(traj, reward, scores[0])
                    save_trajectory_csv(traj, current_game_num)
                    for step in traj:
                        new_trajectory_steps.append({
                            "game": current_game_num,
                            "round": step.get("round", ""),
                            "state_key": step.get("state_key", ""),
                            "action_key": step.get("action_key", ""),
                            "action": str(step.get("action", "")),
                        })

                training_stats["games_played"] = games_done
                training_stats["scores"].append(scores[0])
                training_stats["opponent_scores"].append(scores[1])
                states, entries = agent.get_q_table_size()
                training_stats["qtable_states"].append(states)
                training_stats["qtable_entries"].append(entries)
                training_stats["epsilon_values"].append(agent.epsilon)
                training_stats["training_times"].append((time.time() - batch_start) / max(1, batch_n))

                if epsilon_decay_interval and games_done % epsilon_decay_interval == 0:
                    agent.decay_epsilon(factor=epsilon_decay_factor)

            # Progress after each chunk
            if verbose and (
                games_done % progress_report_interval < batch_n
                or games_done >= num_games
            ):
                win_rate = training_stats["wins"] / max(1, games_done)
                avg_score = float(np.mean(training_stats["scores"]))
                states, _ = agent.get_q_table_size()
                phase = "BOOTSTRAP" if games_done < bootstrap_n else "Q-LEARNING"
                elapsed = time.time() - t0
                gps = games_done / max(1e-6, elapsed)
                print(
                    f"  Game {games_done}: {phase} | Win rate={win_rate:.2%}, "
                    f"Avg score={avg_score:.2f}, States={states}, Epsilon={agent.epsilon:.3f}, "
                    f"{gps:.1f} games/s"
                )
                save_training_stats_json(training_stats)
                append_progress_checkpoint(
                    game=games_done,
                    games_total=num_games,
                    phase=phase,
                    win_rate=win_rate,
                    avg_score=avg_score,
                    states=states,
                    epsilon=agent.epsilon,
                )

    final_states, final_entries = agent.get_q_table_size()
    win_rate = training_stats["wins"] / max(1, num_games)
    avg_score = float(np.mean(training_stats["scores"])) if training_stats["scores"] else 0.0
    total_time = time.time() - t0
    print("\nPARALLEL CPU TRAINING COMPLETE")
    print(f"  Games: {num_games} | workers={num_workers}")
    print(f"  Win rate: {win_rate:.2%}")
    print(f"  Avg score: {avg_score:.2f}")
    print(f"  Q-table: {final_states} states, {final_entries} entries")
    print(f"  Time: {total_time:.1f}s ({num_games / max(1e-6, total_time):.1f} games/s)")

    full_trajectory = trajectory + new_trajectory_steps
    save_trajectory_csv_full(full_trajectory)
    agent.save_q_table_csv()
    save_training_stats_json(training_stats)
    append_progress_checkpoint(
        game=num_games,
        games_total=num_games,
        phase="DONE",
        win_rate=win_rate,
        avg_score=avg_score,
        states=final_states,
        epsilon=agent.epsilon,
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
        }, f, indent=2)

    # Archive locally + upload summary to Supabase (this machine is the DB gateway)
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
        )
    finally:
        _clear_local_pid_file()
