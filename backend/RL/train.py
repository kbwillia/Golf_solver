#!/usr/bin/env python3
"""
RL Training Module with GPU Support

This module provides comprehensive training functions for Q-learning agents,
including bootstrapping, imitation learning, and hyperparameter control.
Supports both CPU and GPU acceleration.
"""

import sys
import os
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

# ============================================================================
# QLearningAgent and GPUQLearningAgent Classes
# (These should primarily come from your agents.py, but shown here for context)
# ============================================================================

# NOTE: The actual implementation of these classes with their full logic
# (e.g., choose_action, update_q_value, neural network structure for GPU agent)
# should reside in your 'agents.py' file.
# The `load_q_table_csv` and `save_q_table_csv` methods below
# are adapted to use the Colab-specific file I/O functions.

class QLearningAgent:
    def __init__(self, learning_rate, discount_factor, epsilon, n_bootstrap_games=0, device=None):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.n_bootstrap_games = n_bootstrap_games
        self.games_played = 0
        self.device = device if device else torch.device("cpu")

    def load_q_table_csv(self, filename="qtable_train.csv"):
        """Loads Q-table from a CSV file."""
        q_table_path = get_output_path(filename)
        self.q_table = load_q_table_from_drive(q_table_path)

    def save_q_table_csv(self, filename="qtable_train.csv"):
        """Saves Q-table to a CSV file."""
        q_table_path = get_output_path(filename)
        save_q_table_to_drive(self.q_table, q_table_path)

    def get_q_table_size(self):
        return len(self.q_table), sum(len(v) for v in self.q_table.values())

    def decay_epsilon(self, factor):
        self.epsilon *= factor

    def train_on_trajectory(self, trajectory, reward, score):
        # Your actual Q-learning update logic goes here.
        # This is a simplified example.  asdf
        if not trajectory:
            return

        # Simple reverse-pass update
        for i in range(len(trajectory) - 1, -1, -1):
            step = trajectory[i]
            state_key = step['state_key']
            action_key = step['action_key']

            current_q = self.q_table[state_key][action_key]

            # Calculate next state's max Q-value
            if i + 1 < len(trajectory):
                next_state_key = trajectory[i+1]['state_key']
                # Ensure the next_state_key exists in q_table before trying to get values
                max_next_q = max(self.q_table[next_state_key].values()) if self.q_table[next_state_key] else 0.0
            else:
                max_next_q = 0.0 # Terminal state has no future reward

            # Q-learning update formula
            new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
            self.q_table[state_key][action_key] = new_q

    def notify_game_end(self):
        self.games_played += 1

    def choose_action(self, state, available_actions):
        state_key = str(state)
        # Epsilon-greedy exploration
        if random.random() < self.epsilon and self.games_played >= self.n_bootstrap_games:
            return random.choice(available_actions)
        else:
            if state_key in self.q_table:
                q_values = self.q_table[state_key]
                # Filter q_values to only include available actions
                # Convert action_key to string for dictionary lookup consistency
                available_q_values = {a: q_values[str(a)] for a in available_actions if str(a) in q_values}
                if available_q_values:
                    max_q = max(available_q_values.values())
                    # Select all actions with the maximum Q-value
                    best_actions = [a for a, q_val in available_q_values.items() if q_val == max_q]
                    return random.choice(best_actions)
            # If state not seen or no available actions in Q-table, choose randomly
            return random.choice(available_actions)

class GPUQLearningAgent(QLearningAgent):
    def __init__(self, learning_rate, discount_factor, epsilon, n_bootstrap_games=0, device=None):
        if device is None:
            raise ValueError("GPUQLearningAgent requires a 'device' to be specified.")
        super().__init__(learning_rate, discount_factor, epsilon, n_bootstrap_games, device)
        # Add any GPU-specific initialization here, e.g., a neural network model
        # self.model = YourQNetwork().to(device)
        # self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        # self.loss_fn = nn.MSELoss()

    def train_on_batch_trajectories_vectorized(self, batch_trajectories, batch_rewards, batch_scores):
        """
        This method is for vectorized updates on GPU.
        You'll need to implement the actual GPU-accelerated training logic here,
        likely involving converting states/actions/rewards to tensors and
        performing batch operations.
        For now, it falls back to the individual trajectory update from the base class.
        """
        # Example:
        # states = []
        # actions = []
        # rewards = []
        # next_states = []
        # for traj, reward, score in zip(batch_trajectories, batch_rewards, batch_scores):
        #     # Collect data for batch processing
        #     # ...
        #
        # # Convert to tensors and move to self.device
        # # Perform forward pass, calculate loss, backward pass, optimizer step
        # # Update Q-table (if using a dict-based Q-table on GPU) or model weights
        for trajectory, reward, score in zip(batch_trajectories, batch_rewards, batch_scores):
            self.train_on_trajectory(trajectory, reward, score) # Fallback to single trajectory update

class EVAgent:
    """A placeholder for your EVAgent logic."""
    def choose_action(self, state, available_actions):
        # Implement your EVAgent's logic here.
        # For demonstration, it just picks a random action.
        return random.choice(available_actions)

class RandomAgent:
    """A placeholder for your RandomAgent logic."""
    def choose_action(self, state, available_actions):
        return random.choice(available_actions)


# ============================================================================
# DEDICATED TRAINING PHASE (Colab-adapted paths)
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
    progress_report_interval=100
):
    """
    Dedicated training phase for Q-learning agent with GPU support.
    Focus on training first, then return the trained agent for analysis.
    """
    print("="*70)
    print("Q-LEARNING AGENT TRAINING PHASE")
    print("="*70)

    # Setup device
    device = get_device() if use_gpu else torch.device("cpu")

    # Choose agent class based on GPU preference
    AgentClass = GPUQLearningAgent if use_gpu else QLearningAgent

    if opponent_type == "qlearning_shared":
        agent = AgentClass(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon=epsilon,
            n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0,
            device=device if use_gpu else None
        )
        agents = [agent, agent]
        agent_types = ["qlearning", "qlearning"]
    elif opponent_type == "ev_ai":
        agent = AgentClass(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon=epsilon,
            n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0,
            device=device if use_gpu else None
        )
        opponent_agent = EVAgent()
        agents = [agent, opponent_agent]
        agent_types = ["qlearning", "ev_ai"]
    elif opponent_type == "random":
        agent = AgentClass(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon=epsilon,
            n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0,
            device=device if use_gpu else None
        )
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
        for idx, (traj, score) in enumerate(zip([trajectory1, trajectory2], game_scores)):
            if traj:
                winner_idx = game_scores.index(min(game_scores))
                if idx == winner_idx:
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
                agent.notify_game_end()
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
    progress_report_interval=100
):
    """
    Batch training for better GPU utilization - plays multiple games simultaneously.
    """
    print("="*70)
    print("BATCH Q-LEARNING AGENT TRAINING PHASE")
    print("="*70)

    device = get_device() if use_gpu else torch.device("cpu")
    AgentClass = GPUQLearningAgent if use_gpu else QLearningAgent

    if opponent_type == "qlearning_shared":
        agent = AgentClass(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon=epsilon,
            n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0,
            device=device
        )
        agents = [agent, agent]
        agent_types = ["qlearning", "qlearning"]
    elif opponent_type == "ev_ai":
        agent = AgentClass(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon=epsilon,
            n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0,
            device=device
        )
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