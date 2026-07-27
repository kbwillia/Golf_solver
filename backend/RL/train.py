#!/usr/bin/env python3
"""
RL Training Module with GPU Support

This module provides comprehensive training functions for Q-learning agents,
including bootstrapping, imitation learning, and hyperparameter control.
Supports both CPU and GPU acceleration.
"""

import sys
import os
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import defaultdict
import time
import random
from tqdm import trange
import csv
import pandas as pd

# Check if running in Google Colab
try:
    from google.colab import drive
    IN_COLAB = True
    # Mount Google Drive at the beginning (only if we're actually in Colab)
    try:
        drive.mount('/content/drive')
    except Exception as e:
        print(f"Could not mount Google Drive: {e}")
        IN_COLAB = False
except ImportError:
    IN_COLAB = False
    print("Running locally - Google Drive not available")

# ============================================================================
# PATH CONFIGURATION
# ----------------------------------------------------------------------------
# Choose ONE of the following configurations for your input and output directories.
# Uncomment the Google Drive path for Colab usage.
# The local C: drive path is commented out as requested.
# ============================================================================

# --- Path Configuration (Works for both Colab and Local) ---
if IN_COLAB:
    # Google Drive Paths (for Colab)
    GOOGLE_DRIVE_PROJECT_PATH = '/content/drive/MyDrive/Data Projects/Golf'
    output_dir = os.path.join(GOOGLE_DRIVE_PROJECT_PATH, 'output')
    sys.path.append(GOOGLE_DRIVE_PROJECT_PATH)
else:
    # Local Paths (for local development)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'output')
    # Add parent directory to path for backend imports
    parent_dir = os.path.dirname(base_dir)
    sys.path.append(parent_dir)

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Import your custom modules
from agents import * # Ensure agents.py has QLearningAgent, GPUQLearningAgent, EVAgent, RandomAgent
from game import GolfGame # Ensure game.py has GolfGame

# ============================================================================
# FILE I/O UTILITIES FOR COLAB (using Google Drive paths from 'output_dir')
# ============================================================================

def get_output_path(filename):
    """Helper function to get full path for output files"""
    return os.path.join(output_dir, filename)

def load_q_table_from_drive(filepath):
    """Loads Q-table from a CSV file."""
    q_table = defaultdict(lambda: defaultdict(float))
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            for _, row in df.iterrows():
                state_key = row['state_key']
                action_key = row['action_key']
                q_value = row['q_value']
                q_table[state_key][action_key] = q_value
            print(f"Loaded Q-table from {filepath} with {len(q_table)} states.")
        except Exception as e:
            print(f"Error loading Q-table from {filepath}: {e}")
            # If there's an error, it might mean the CSV is malformed or empty,
            # so we still return an empty q_table to start fresh.
    else:
        print(f"No existing Q-table found at {filepath}. Starting fresh.")
    return q_table


def save_q_table_to_drive(q_table, filepath):
    """Saves Q-table to a CSV file."""
    data = []
    for state_key, actions in q_table.items():
        for action_key, q_value in actions.items():
            data.append({'state_key': state_key, 'action_key': action_key, 'q_value': q_value})
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    print(f"Saved Q-table to {filepath}.")

def load_trajectory_csv(filename="trajectory_train.csv"):
    output_path = get_output_path(filename)
    trajectory = []
    last_game_num = 0
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    game_num = int(row['game']) if row['game'] != '?' else 0
                except ValueError:
                    game_num = 0 # Default to 0 if '?' or other non-int value
                last_game_num = max(last_game_num, game_num)
                trajectory.append(row)
    return trajectory, last_game_num

def save_trajectory_csv_full(trajectory, filename="trajectory_train.csv"):
    output_path = get_output_path(filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['game', 'round', 'state_key', 'action_key', 'action']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for step in trajectory:
            writer.writerow(step)

def save_training_stats_json(training_stats, filename="training_stats.json"):
    """Persist per-game training series for the frontend RL viz page."""
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
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    print(f"Saved training stats to {output_path}.")


def save_trajectory_csv(trajectory, game_num, filename="trajectory_train.csv"):
    output_path = get_output_path(filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    file_exists = os.path.isfile(output_path)
    with open(output_path, 'a', newline='') as csvfile:
        fieldnames = ['game', 'round', 'state_key', 'action_key', 'action']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for step in trajectory:
            row = {
                'game': game_num,
                'round': step.get('round', ''),
                'state_key': step.get('state_key', ''),
                'action_key': step.get('action_key', ''),
                'action': str(step.get('action', '')),
            }
            writer.writerow(row)

# ============================================================================
# GPU UTILITIES
# ============================================================================

def get_device():
    """Determines and returns the appropriate device (GPU or CPU)."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available(): # For Apple Silicon Macs
        return torch.device("mps")
    return torch.device("cpu")

def state_to_tensor(state, device):
    """Convert game state to tensor representation for GPU processing"""
    if isinstance(state, tuple):
        state_list = []
        for item in state:
            if isinstance(item, (int, float)):
                state_list.append(float(item))
            elif isinstance(item, list):
                state_list.extend([float(x) for x in item])
            else:
                state_list.append(0.0)  # Default for unknown types
        return torch.tensor(state_list, dtype=torch.float32, device=device)
    else:
        return torch.tensor([float(state)], dtype=torch.float32, device=device)

# Use QLearningAgent / GPUQLearningAgent / EVAgent / RandomAgent from agents.py
# (imported above). Do not redefine stub classes here — they shadow the real ones
# and break GolfGame.play_turn(choose_action(player, game, trajectory)).

# ============================================================================
# DEDICATED TRAINING PHASE
# ============================================================================

def train_qlearning_agent(
    num_games=1000,
    opponent_type="ev_ai",
    verbose=True,
    use_gpu=True,
    # Q-learning hyperparameters
    learning_rate=0.1,
    discount_factor=0.9,
    epsilon=0.2,
    epsilon_decay_factor=1.0,
    # Bootstrapping and imitation learning
    n_bootstrap_games=250,
    use_imitation_learning=True,
    # Training configuration
    epsilon_decay_interval=100,
    progress_report_interval=100,
    # Reward shaping (UI-editable; disable for solve-mode)
    use_reward_shaping=True,
    shape_step=0.05,
    shape_pair=1.5,
    shape_high_keep=-0.8,
    shape_low_keep=0.3,
    shape_midhigh_keep=-0.4,
    shape_flip=0.1,
):
    """
    Dedicated training phase for Q-learning agent with GPU support.
    Focus on training first, then return the trained agent for analysis.
    """
    print("="*70)
    print("Q-LEARNING AGENT TRAINING PHASE")
    print("="*70)

    reward_shaping = {
        "enabled": bool(use_reward_shaping),
        "step": float(shape_step),
        "pair": float(shape_pair),
        "high_keep": float(shape_high_keep),
        "low_keep": float(shape_low_keep),
        "midhigh_keep": float(shape_midhigh_keep),
        "flip": float(shape_flip),
    }

    # Setup device
    device = get_device() if use_gpu else torch.device("cpu")

    # Choose agent class based on GPU preference
    AgentClass = GPUQLearningAgent if use_gpu else QLearningAgent

    agent_kwargs = dict(
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0,
        reward_shaping=reward_shaping,
    )
    if use_gpu:
        agent_kwargs["device"] = device

    if opponent_type == "qlearning_shared":
        agent = AgentClass(**agent_kwargs)
        agents = [agent, agent]
        agent_types = ["qlearning", "qlearning"]
    elif opponent_type == "ev_ai":
        agent = AgentClass(**agent_kwargs)
        opponent_agent = EVAgent()
        agents = [agent, opponent_agent]
        agent_types = ["qlearning", "ev_ai"]
    elif opponent_type == "random":
        agent = AgentClass(**agent_kwargs)
        opponent_agent = RandomAgent()
        agents = [agent, opponent_agent]
        agent_types = ["qlearning", "random"]
    else:
        raise ValueError(f"Unknown opponent type: {opponent_type}")

    # Load Q-table from previous run if available (now from Google Drive)
    agent.load_q_table_csv()

    # Load trajectory from previous run if available (now from Google Drive)
    trajectory, last_game_num = load_trajectory_csv()
    new_trajectory_steps = []

    # Training statistics
    training_stats = {
        'games_played': 0,
        'wins': 0,
        'losses': 0,
        'scores': [],
        'opponent_scores': [],
        'qtable_states': [],
        'qtable_entries': [],
        'epsilon_values': [],
        'training_times': []
    }

    print(f"Training against {opponent_type} for {num_games} games...")
    print(f"Acceleration: {'GPU' if use_gpu else 'CPU'}")
    print(f"Q-learning parameters:")
    print(f"  • Learning rate: {learning_rate}")
    print(f"  • Discount factor: {discount_factor}")
    print(f"  • Initial epsilon: {epsilon}")
    print(f"  • Epsilon decay factor: {epsilon_decay_factor}")
    print(f"  • Epsilon decay interval: {epsilon_decay_interval} games")
    if use_imitation_learning:
        print(f"  • Bootstrapping: {n_bootstrap_games} games with EVAgent")
    else:
        print(f"  • Bootstrapping: Disabled")
    print(f"  • Reward shaping: {'ON' if use_reward_shaping else 'OFF'} {reward_shaping}")
    print(f"  • Progress reports: Every {progress_report_interval} games")

    game_iter = trange(num_games, desc="Training Q-learning agent")
    total_sim_time = 0.0
    total_q_time = 0.0
    for game_num_abs in game_iter:
        current_game_num = last_game_num + game_num_abs + 1
        start_time = time.time()

        trajectory1 = []
        trajectory2 = []

        start_sim = time.perf_counter()
        game = GolfGame(num_players=2, agent_types=agent_types, q_agents=agents)
        game_scores = game.play_game(verbose=False, trajectories=[trajectory1, trajectory2])
        end_sim = time.perf_counter()
        sim_time = end_sim - start_sim
        total_sim_time += sim_time

        start_q = time.perf_counter()
        # Only train on the Q-agent's own trajectories.
        # Self-play (shared agent): both seats are the same agent → train both.
        # vs EV/random: only player-0 traj is ours (player-1 traj stays empty).
        # Always notify_game_end() once per game — calling it per traj used to
        # advance games_played 2× in self-play and end bootstrap ~halfway early.
        agent_trajs = [(trajectory1, game_scores[0])]
        if agents[0] is agents[1] and trajectory2:
            agent_trajs.append((trajectory2, game_scores[1]))

        won = game_scores[0] < game_scores[1]
        tied = game_scores[0] == game_scores[1]
        if won:
            training_stats['wins'] += 1
        elif not tied:
            training_stats['losses'] += 1

        for idx, (traj, score) in enumerate(agent_trajs):
            if not traj:
                continue
            is_winner = score == min(game_scores)
            if is_winner:
                reward = 10.0
            else:
                if score == 0:
                    reward = 10.0
                elif score <= 5:
                    reward = 5.0
                elif score <= 20:
                    reward = -4.0
                else:
                    reward = -10.0
            agent.train_on_trajectory(traj, reward, score)
            if idx == 0:
                save_trajectory_csv(traj, current_game_num)
                for step in traj:
                    step_to_save = {
                        'game': current_game_num,
                        'round': step.get('round', ''),
                        'state_key': step.get('state_key', ''),
                        'action_key': step.get('action_key', ''),
                        'action': str(step.get('action', '')),
                    }
                    new_trajectory_steps.append(step_to_save)

        agent.notify_game_end()  # once per game
        end_q = time.perf_counter()
        q_time = end_q - start_q
        total_q_time += q_time

        training_stats['games_played'] += 1
        training_stats['scores'].append(game_scores[0])
        training_stats['opponent_scores'].append(game_scores[1])
        training_stats['training_times'].append(time.time() - start_time)

        states, entries = agent.get_q_table_size()
        training_stats['qtable_states'].append(states)
        training_stats['qtable_entries'].append(entries)
        training_stats['epsilon_values'].append(agent.epsilon)

        if epsilon_decay_interval and (game_num_abs + 1) % epsilon_decay_interval == 0:
            agent.decay_epsilon(factor=epsilon_decay_factor)

        if verbose and (game_num_abs + 1) % progress_report_interval == 0:
            win_rate = training_stats['wins'] / (game_num_abs + 1)
            avg_score = np.mean(training_stats['scores'])
            avg_time = np.mean(training_stats['training_times'])
            bootstrap_status = "BOOTSTRAP" if game_num_abs < n_bootstrap_games else "Q-LEARNING"
            print(f"  Game {game_num_abs + 1}: {bootstrap_status} | Win rate={win_rate:.2%}, "
                  f"Avg score={avg_score:.2f}, States={states}, Epsilon={agent.epsilon:.3f}, "
                  f"Avg time={avg_time:.3f}s")
            # Checkpoint for live frontend viz during long runs
            save_training_stats_json(training_stats)

    final_win_rate = training_stats['wins'] / num_games
    final_avg_score = np.mean(training_stats['scores'])
    final_states, final_entries = agent.get_q_table_size()
    total_time = sum(training_stats['training_times'])

    print(f"\n🎯 TRAINING COMPLETE!")
    print(f"   • Games played: {num_games}")
    print(f"   • Win rate: {final_win_rate:.2%} ({training_stats['wins']}/{num_games})")
    print(f"   • Average score: {final_avg_score:.2f}")
    print(f"   • Final Q-table: {final_states} states, {final_entries} entries")
    print(f"   • Final epsilon: {agent.epsilon:.3f}")
    print(f"   • Total training time: {total_time:.2f}s")
    print(f"   • Average time per game: {total_time/num_games:.3f}s")
    print(f"   • Total simulation time: {total_sim_time:.2f}s")
    print(f"   • Total Q-table update time: {total_q_time:.2f}s")
    if use_imitation_learning:
        bootstrap_games = min(n_bootstrap_games, num_games)
        qlearning_games = max(0, num_games - n_bootstrap_games)
        print(f"   • Bootstrapping phase: {bootstrap_games} games")
        print(f"   • Q-learning phase: {qlearning_games} games")

    full_trajectory = trajectory + new_trajectory_steps
    save_trajectory_csv_full(full_trajectory)

    agent.save_q_table_csv() # Save the final Q-table to Google Drive
    save_training_stats_json(training_stats)

    return agent, training_stats


def train_qlearning_agent_batch(
    num_games=1000,
    batch_size=100,
    opponent_type="ev_ai",
    verbose=True,
    use_gpu=True,
    learning_rate=0.1,
    discount_factor=0.9,
    epsilon=0.2,
    epsilon_decay_factor=0.995,
    n_bootstrap_games=250,
    use_imitation_learning=True,
    epsilon_decay_interval=100,
    progress_report_interval=100,
    use_reward_shaping=True,
    shape_step=0.05,
    shape_pair=1.5,
    shape_high_keep=-0.8,
    shape_low_keep=0.3,
    shape_midhigh_keep=-0.4,
    shape_flip=0.1,
):
    """
    Batch training for better GPU utilization - plays multiple games simultaneously.
    """
    print("="*70)
    print("BATCH Q-LEARNING AGENT TRAINING PHASE")
    print("="*70)

    reward_shaping = {
        "enabled": bool(use_reward_shaping),
        "step": float(shape_step),
        "pair": float(shape_pair),
        "high_keep": float(shape_high_keep),
        "low_keep": float(shape_low_keep),
        "midhigh_keep": float(shape_midhigh_keep),
        "flip": float(shape_flip),
    }

    device = get_device() if use_gpu else torch.device("cpu")
    AgentClass = GPUQLearningAgent if use_gpu else QLearningAgent

    agent_kwargs = dict(
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0,
        reward_shaping=reward_shaping,
    )
    if use_gpu:
        agent_kwargs["device"] = device

    if opponent_type == "qlearning_shared":
        agent = AgentClass(**agent_kwargs)
        agents = [agent, agent]
        agent_types = ["qlearning", "qlearning"]
    elif opponent_type == "ev_ai":
        agent = AgentClass(**agent_kwargs)
        agent_types = ["qlearning", "ev_ai"]
    else:
        raise ValueError(f"Unknown opponent type: {opponent_type}")

    agent.load_q_table_csv()
    trajectory, last_game_num = load_trajectory_csv()
    new_trajectory_steps = []

    training_stats = {
        'games_played': 0,
        'wins': 0,
        'losses': 0,
        'scores': [],
        'opponent_scores': [],
        'qtable_states': [],
        'qtable_entries': [],
        'epsilon_values': [],
        'training_times': []
    }

    print(f"Batch training against {opponent_type} for {num_games} games...")
    print(f"Batch size: {batch_size} games per batch")
    print(f"Acceleration: {'GPU' if use_gpu else 'CPU'}")

    num_batches = (num_games + batch_size - 1) // batch_size
    if batch_size > num_games:
        print(f"Warning: batch_size ({batch_size}) > num_games ({num_games}). Using batch_size = {num_games}")
        batch_size = num_games
        num_batches = 1

    total_sim_time = 0.0
    total_q_time = 0.0
    for batch_idx in trange(num_batches, desc="Training batches"):
        batch_start_time = time.time()

        games_in_batch = min(batch_size, num_games - batch_idx * batch_size)

        start_sim = time.perf_counter()
        batch_trajectories = []
        batch_rewards = []
        batch_scores = []
        for game_idx_in_batch in range(games_in_batch):
            current_game_num = last_game_num + batch_idx * batch_size + game_idx_in_batch + 1
            trajectory = []
            if opponent_type == "ev_ai":
                opponent_agent = EVAgent()
                agents = [agent, opponent_agent]
            game = GolfGame(num_players=2, agent_types=agent_types, q_agents=agents)
            game_scores = game.play_game(verbose=False, trajectories=[trajectory, None])
            winner_idx = game_scores.index(min(game_scores))
            if winner_idx == 0:
                reward = 10.0
                training_stats['wins'] += 1
            else:
                if game_scores[0] <= 5:
                    reward = 2.0
                elif game_scores[0] <= 10:
                    reward = 0.0
                elif game_scores[0] <= 15:
                    reward = -2.0
                else:
                    reward = -5.0
                training_stats['losses'] += 1
            batch_trajectories.append(trajectory)
            batch_rewards.append(reward)
            batch_scores.append(game_scores[0])
            training_stats['games_played'] += 1
            training_stats['scores'].append(game_scores[0])
            training_stats['opponent_scores'].append(game_scores[1])
            save_trajectory_csv(trajectory, current_game_num)
            for step in trajectory:
                step_to_save = {
                    'game': current_game_num,
                    'round': step.get('round', ''),
                    'state_key': step.get('state_key', ''),
                    'action_key': step.get('action_key', ''),
                    'action': str(step.get('action', '')),
                }
                new_trajectory_steps.append(step_to_save)
        end_sim = time.perf_counter()
        sim_time = end_sim - start_sim
        total_sim_time += sim_time

        start_q = time.perf_counter()
        if use_gpu and hasattr(agent, 'train_on_batch_trajectories_vectorized'):
            agent.train_on_batch_trajectories_vectorized(batch_trajectories, batch_rewards, batch_scores)
        else:
            for trajectory, reward, score in zip(batch_trajectories, batch_rewards, batch_scores):
                agent.train_on_trajectory(trajectory, reward, score)
        end_q = time.perf_counter()
        q_time = end_q - start_q
        total_q_time += q_time

        for _ in range(games_in_batch):
            agent.notify_game_end()

        batch_time = time.time() - batch_start_time
        training_stats['training_times'].extend([batch_time / games_in_batch] * games_in_batch)

        states, entries = agent.get_q_table_size()
        for _ in range(games_in_batch):
            training_stats['qtable_states'].append(states)
            training_stats['qtable_entries'].append(entries)
            training_stats['epsilon_values'].append(agent.epsilon)

        if epsilon_decay_interval and (training_stats['games_played']) % epsilon_decay_interval == 0:
            agent.decay_epsilon(factor=epsilon_decay_factor)

        report_every_batches = max(1, progress_report_interval // batch_size)
        if verbose and (batch_idx + 1) % report_every_batches == 0:
            games_so_far = training_stats['games_played']
            win_rate = training_stats['wins'] / games_so_far
            avg_score = np.mean(training_stats['scores'])
            avg_time = np.mean(training_stats['training_times'])
            bootstrap_status = "BOOTSTRAP" if games_so_far < n_bootstrap_games else "Q-LEARNING"
            print(f"  Batch {batch_idx + 1}: {bootstrap_status} | Games={games_so_far}, Win rate={win_rate:.2%}, "
                  f"Avg score={avg_score:.2f}, States={states}, Epsilon={agent.epsilon:.3f}, "
                  f"Avg time={avg_time:.3f}s")
            save_training_stats_json(training_stats)

    if verbose and training_stats['games_played'] > 0:
        games_so_far = training_stats['games_played']
        win_rate = training_stats['wins'] / games_so_far
        avg_score = np.mean(training_stats['scores'])
        avg_time = np.mean(training_stats['training_times'])
        final_states, final_entries = agent.get_q_table_size()
        bootstrap_status = "BOOTSTRAP" if games_so_far < n_bootstrap_games else "Q-LEARNING"
        print(f"  Final: {bootstrap_status} | Games={games_so_far}, Win rate={win_rate:.2%}, "
              f"Avg score={avg_score:.2f}, States={final_states}, Epsilon={agent.epsilon:.3f}, "
              f"Avg time={avg_time:.3f}s")

    final_win_rate = training_stats['wins'] / num_games
    final_avg_score = np.mean(training_stats['scores'])
    final_states, final_entries = agent.get_q_table_size()
    total_time = sum(training_stats['training_times'])

    print(f"\n🎯 BATCH TRAINING COMPLETE!")
    print(f"   • Games played: {num_games}")
    print(f"   • Batch size: {batch_size}")
    print(f"   • Win rate: {final_win_rate:.2%} ({training_stats['wins']}/{num_games})")
    print(f"   • Average score: {final_avg_score:.2f}")
    print(f"   • Final Q-table: {final_states} states, {final_entries} entries")
    print(f"   • Final epsilon: {agent.epsilon:.3f}")
    print(f"   • Total training time: {total_time:.2f}s")
    print(f"   • Average time per game: {total_time/num_games:.3f}s")
    print(f"   • Total simulation time: {total_sim_time:.2f}s")
    print(f"   • Total Q-table update time: {total_q_time:.2f}s")

    full_trajectory = trajectory + new_trajectory_steps
    save_trajectory_csv_full(full_trajectory)

    agent.save_q_table_csv() # Save the final Q-table to Google Drive
    save_training_stats_json(training_stats)

    return agent, training_stats


if __name__ == "__main__":
    print("Starting Q-learning agent training with GPU acceleration...")
    agent, training_stats = train_qlearning_agent(
        num_games=2000,
        opponent_type="ev_ai",
        verbose=True,
        use_gpu=True,
        learning_rate=0.1,
        discount_factor=0.9,
        epsilon=0.2,
        epsilon_decay_factor=0.995,
        n_bootstrap_games=250,
        use_imitation_learning=True,
        epsilon_decay_interval=100,
        progress_report_interval=100
    )

    print("\n" + "="*70)
    print("TRAINING COMPLETE!")
    print("="*70)
    print(f"Trained agent has {len(agent.q_table)} states in Q-table")
    print(f"Win rate: {training_stats['wins']/training_stats['games_played']:.2%}")
    print(f"Average score: {np.mean(training_stats['scores']):.2f}")
    print("Check your Google Drive 'Data Projects/Golf/output' folder for saved Q-tables and trajectories.")
    print("Use RL_analytics.py for full analysis and visualizations")