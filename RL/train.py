#!/usr/bin/env python3
"""
RL Training Module with GPU Support

This module provides comprehensive training functions for Q-learning agents,
including bootstrapping, imitation learning, and hyperparameter control.
Supports both CPU and GPU acceleration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import *
from game import GolfGame
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import defaultdict
import time
import random # Added for random.choice
from tqdm import trange

# Create output directory if it doesn't exist
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(output_dir, exist_ok=True)

def get_output_path(filename):
    """Helper function to get full path for output files"""
    return os.path.join(output_dir, filename)

# ============================================================================
# GPU UTILITIES
# ============================================================================

def get_device():
    """Get the best available device (GPU if available, else CPU)"""
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"🚀 Using GPU: {torch.cuda.get_device_name(0)}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        device = torch.device("cpu")
        print("💻 Using CPU")
    return device

def state_to_tensor(state, device):
    """Convert game state to tensor representation for GPU processing"""
    # Convert state to a numerical representation
    # This is a simplified version - you might want to expand this
    if isinstance(state, tuple):
        # Convert tuple state to tensor
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
        # Fallback for non-tuple states
        return torch.tensor([float(state)], dtype=torch.float32, device=device)

# ============================================================================
# GPU-ACCELERATED Q-LEARNING AGENT
# ============================================================================

class GPUQLearningAgent(QLearningAgent):
    """GPU-accelerated version of QLearningAgent using PyTorch tensors"""

    def __init__(self, learning_rate=0.1, discount_factor=0.9, epsilon=0.2,
                 n_bootstrap_games=0, device=None):
        super().__init__(learning_rate, discount_factor, epsilon, n_bootstrap_games)
        self.device = device if device else get_device()
        self.q_table = {}  # Keep as dict for state keys, but values as tensors
        self.optimizer = None
        self.criterion = nn.MSELoss()

    def get_action_key(self, action):
        """Convert action to a string key (inherited from parent)"""
        return super().get_action_key(action)

    def get_state_key(self, player, game_state):
        """Get state key (inherited from parent)"""
        return super().get_state_key(player, game_state)

    def get_legal_actions(self, player, game_state):
        """Get legal actions (inherited from parent)"""
        return super().get_legal_actions(player, game_state)

    def choose_action(self, player, game_state, trajectory=None):
        """Override choose_action to use GPU tensor-based Q-table"""
        legal_actions = self.get_legal_actions(player, game_state)
        if not legal_actions:
            return None

        # Bootstrapping phase: use EVAgent for first n_bootstrap_games
        if self.games_played < self.n_bootstrap_games:
            ev_agent = EVAgent()
            action = ev_agent.choose_action(player, game_state)
            if action not in legal_actions:
                action = random.choice(legal_actions)
        else:
            # Custom epsilon-greedy: 1/3 take_discard, 1/3 draw_deck_keep, 1/3 draw_deck_discard_flip
            if self.training_mode and random.random() < self.epsilon:
                # Group legal actions by type
                type_groups = {
                    'take_discard': [],
                    'draw_deck_keep': [],
                    'draw_deck_discard_flip': []
                }
                for a in legal_actions:
                    if a['type'] == 'take_discard':
                        type_groups['take_discard'].append(a)
                    elif a['type'] == 'draw_deck' and a.get('keep', True):
                        type_groups['draw_deck_keep'].append(a)
                    elif a['type'] == 'draw_deck' and not a.get('keep', True):
                        type_groups['draw_deck_discard_flip'].append(a)
                # Pick a type at random (only among those with available actions)
                available_types = [k for k, v in type_groups.items() if v]
                chosen_type = random.choice(available_types)
                action = random.choice(type_groups[chosen_type])
            else:
                state_key = self.get_state_key(player, game_state)
                best_action = None
                best_value = float('-inf')
                for action_candidate in legal_actions:
                    action_key = self.get_action_key(action_candidate)
                    q_value = self.get_q_value(state_key, action_key)
                    if q_value > best_value:
                        best_value = q_value
                        best_action = action_candidate
                action = best_action

        # Record trajectory if provided
        if action is not None and trajectory is not None:
            state_key = self.get_state_key(player, game_state)
            action_key = self.get_action_key(action)
            trajectory.append({
                'state_key': state_key,
                'action_key': action_key,
                'action': action,
                'round': getattr(game_state, 'round', None)
            })
        return action

    def get_q_value(self, state_key, action_key):
        """Get Q-value using GPU tensors"""
        if state_key not in self.q_table:
            self.q_table[state_key] = torch.full((12,), float('nan'), dtype=torch.float32, device=self.device)

        action_idx = self._action_key_to_index(action_key)
        return self.q_table[state_key][action_idx].item()

    def update_q_value(self, state_key, action_key, new_value):
        """Update Q-value using GPU tensors"""
        if state_key not in self.q_table:
            self.q_table[state_key] = torch.full((12,), float('nan'), dtype=torch.float32, device=self.device)

        # Update the tensor value
        action_idx = self._action_key_to_index(action_key)
        self.q_table[state_key][action_idx] = new_value

    def train_on_trajectory(self, trajectory, reward, final_score):
        """Train on trajectory using GPU acceleration"""
        if not trajectory:
            return

        # Update Q-values for each step in the trajectory
        for i, step in enumerate(trajectory):
            state_key = step['state_key']
            action_key = step['action_key']

            # Calculate immediate reward for this action
            # Give small positive reward for taking actions (encourages exploration)
            # The main learning comes from the final reward
            immediate_reward = 0.1  # Small positive reward for taking action

            # Get next state and actions (if not the last step)
            if i < len(trajectory) - 1:
                next_step = trajectory[i + 1]
                next_state_key = next_step['state_key']
                next_actions = [next_step['action']]
            else:
                next_state_key = state_key  # Terminal state
                next_actions = []
                # Add final reward to the last action
                immediate_reward += reward

            # Update Q-value using GPU tensors
            self._update_q_value_gpu(state_key, action_key, immediate_reward, next_state_key, next_actions)

    def _update_q_value_gpu(self, state_key, action_key, reward, next_state_key, next_actions):
        """Update Q-values using GPU tensors"""
        # Initialize state if not exists
        if state_key not in self.q_table:
            self.q_table[state_key] = torch.full((12,), float('nan'), dtype=torch.float32, device=self.device)
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = torch.full((12,), float('nan'), dtype=torch.float32, device=self.device)

        # Get current Q-value
        action_idx = self._action_key_to_index(action_key)
        current_q = self.q_table[state_key][action_idx].item()

        # If this action hasn't been explored yet, treat as 0.0 for computation
        if np.isnan(current_q):
            current_q = 0.0

        # Calculate max next Q-value
        max_next_q = 0.0
        if next_actions:
            next_q_values = []
            for action in next_actions:
                next_action_idx = self._action_key_to_index(self.get_action_key(action))
                next_q_val = self.q_table[next_state_key][next_action_idx].item()
                # If next action hasn't been explored, treat as 0.0
                if not np.isnan(next_q_val):
                    next_q_values.append(next_q_val)
            max_next_q = max(next_q_values) if next_q_values else 0.0

        # Update Q-value
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        self.q_table[state_key][action_idx] = new_q

    def _action_key_to_index(self, action_key):
        """Convert action key to tensor index"""
        # Parse action key format: "type_position" or "type_flip_position"
        if isinstance(action_key, str):
            parts = action_key.split('_')
            if len(parts) >= 2:
                action_type = parts[0]
                if action_type == 'take_discard':
                    # take_discard_0, take_discard_1, etc. -> indices 0-3
                    try:
                        pos = int(parts[1])
                        return pos
                    except ValueError:
                        pass
                elif action_type == 'draw_deck':
                    if len(parts) >= 3 and parts[1] == 'flip':
                        # draw_deck_flip_0, draw_deck_flip_1, etc. -> indices 8-11
                        try:
                            pos = int(parts[2])
                            return pos + 8
                        except ValueError:
                            pass
                    else:
                        # draw_deck_0, draw_deck_1, etc. -> indices 4-7
                        try:
                            pos = int(parts[1])
                            return pos + 4
                        except ValueError:
                            pass
        # Fallback: hash the action key to get an index
        return hash(action_key) % 12

    def get_q_table_size(self):
        """Get Q-table size information (only count states with explored actions)"""
        total_entries = 0
        states_with_actions = 0

        for q_tensor in self.q_table.values():
            if isinstance(q_tensor, torch.Tensor):
                # Count only non-NaN values (explored actions)
                explored_actions = sum(1 for v in q_tensor if not torch.isnan(v))
                if explored_actions > 0:
                    states_with_actions += 1
                    total_entries += explored_actions
            else:
                # Fallback for dict-based Q-tables
                if len(q_tensor) > 0:
                    states_with_actions += 1
                    total_entries += len(q_tensor)

        return states_with_actions, total_entries

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
    epsilon_decay_factor=0.995,
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

    Args:
        num_games: Number of games to train on
        opponent_type: Type of opponent ("evagent", "random", etc.)
        verbose: Whether to print progress
        use_gpu: Whether to use GPU acceleration

        # Q-learning hyperparameters
        learning_rate: Learning rate for Q-value updates (default: 0.1)
        discount_factor: Discount factor for future rewards (default: 0.9)
        epsilon: Initial exploration rate (default: 0.2)
        epsilon_decay_factor: Factor to decay epsilon (default: 0.995)

        # Bootstrapping and imitation learning
        n_bootstrap_games: Number of games to use EVAgent for bootstrapping (default: 250)
        use_imitation_learning: Whether to use EVAgent for initial imitation (default: True)

        # Training configuration
        epsilon_decay_interval: How often to decay epsilon (default: 100 games)
        progress_report_interval: How often to report progress (default: 100 games)

    Returns:
        trained_agent: The trained QLearningAgent (GPU or CPU version)
        training_stats: Dictionary with training statistics
    """
    print("="*70)
    print("Q-LEARNING AGENT TRAINING PHASE")
    print("="*70)

    # Setup device
    device = get_device() if use_gpu else torch.device("cpu")

    # Choose agent class based on GPU preference
    AgentClass = GPUQLearningAgent if use_gpu else QLearningAgent

    if opponent_type == "qlearning_shared":
        # Create one shared agent
        agent = AgentClass(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon=epsilon,
            n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0,
            device=device if use_gpu else None
        )
        agents = [agent, agent]  # Both players use the same agent
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
    print(f"  • Learning rate: {learning_rate}")
    print(f"  • Discount factor: {discount_factor}")
    print(f"  • Initial epsilon: {epsilon}")
    print(f"  • Epsilon decay factor: {epsilon_decay_factor}")
    print(f"  • Epsilon decay interval: {epsilon_decay_interval} games")
    if use_imitation_learning:
        print(f"  • Bootstrapping: {n_bootstrap_games} games with EVAgent")
    else:
        print(f"  • Bootstrapping: Disabled")
    print(f"  • Progress reports: Every {progress_report_interval} games")

    # Use tqdm progress bar
    game_iter = trange(num_games, desc="Training Q-learning agent")
    for game_num in game_iter:
        start_time = time.time()

        # Create trajectory for this game
        trajectory1 = []
        trajectory2 = []

        # Play game
        game = GolfGame(num_players=2, agent_types=agent_types, q_agents=agents)
        game_scores = game.play_game(verbose=False, trajectories=[trajectory1, trajectory2])

        # For each trajectory, update the shared agent
        for idx, (traj, score) in enumerate(zip([trajectory1, trajectory2], game_scores)):
            if traj:
                winner_idx = game_scores.index(min(game_scores))
                if idx == winner_idx:
                    reward = 10.0
                else:
                    if score <= 5:
                        reward = 2.0
                    elif score <= 10:
                        reward = 0.0
                    elif score <= 15:
                        reward = -2.0
                    else:
                        reward = -5.0
                agent.train_on_trajectory(traj, reward, score)
                agent.notify_game_end()

        # Record statistics
        training_stats['games_played'] += 1
        training_stats['scores'].append(game_scores[0]) # Q-learning score
        training_stats['opponent_scores'].append(game_scores[1]) # Opponent score
        training_stats['training_times'].append(time.time() - start_time)

        # Track Q-table growth
        states, entries = agent.get_q_table_size()
        training_stats['qtable_states'].append(states)
        training_stats['qtable_entries'].append(entries)
        training_stats['epsilon_values'].append(agent.epsilon)

        # Decay epsilon periodically
        if epsilon_decay_interval and (game_num + 1) % epsilon_decay_interval == 0:
            agent.decay_epsilon(factor=epsilon_decay_factor)

        # Progress updates
        if verbose and (game_num + 1) % progress_report_interval == 0:
            win_rate = training_stats['wins'] / (game_num + 1)
            avg_score = np.mean(training_stats['scores'])
            avg_time = np.mean(training_stats['training_times'])
            bootstrap_status = "BOOTSTRAP" if game_num < n_bootstrap_games else "Q-LEARNING"
            print(f"  Game {game_num + 1}: {bootstrap_status} | Win rate={win_rate:.2%}, "
                  f"Avg score={avg_score:.2f}, States={states}, Epsilon={agent.epsilon:.3f}, "
                  f"Avg time={avg_time:.3f}s")

    # Final training statistics
    final_win_rate = training_stats['wins'] / num_games
    final_avg_score = np.mean(training_stats['scores'])
    final_states, final_entries = agent.get_q_table_size()
    total_time = sum(training_stats['training_times'])

    print(f"\n🎯 TRAINING COMPLETE!")
    print(f"   • Games played: {num_games}")
    print(f"   • Win rate: {final_win_rate:.2%} ({training_stats['wins']}/{num_games})")
    print(f"   • Average score: {final_avg_score:.2f}")
    print(f"   • Final Q-table: {final_states} states, {final_entries} entries")
    print(f"   • Final epsilon: {agent.epsilon:.3f}")
    print(f"   • Total training time: {total_time:.2f}s")
    print(f"   • Average time per game: {total_time/num_games:.3f}s")
    if use_imitation_learning:
        bootstrap_games = min(n_bootstrap_games, num_games)
        qlearning_games = max(0, num_games - n_bootstrap_games)
        print(f"   • Bootstrapping phase: {bootstrap_games} games")
        print(f"   • Q-learning phase: {qlearning_games} games")

    return agent, training_stats



if __name__ == "__main__":
    # Run the training function with GPU support
    print("Starting Q-learning agent training with GPU acceleration...")
    agent, training_stats = train_qlearning_agent(
        num_games=2000,  # Train for 1000 games
        opponent_type="ev_ai",  # Train against EV agent
        verbose=True,
        use_gpu=True,  # Enable GPU acceleration
        # Q-learning hyperparameters
        learning_rate=0.1,
        discount_factor=0.9,
        epsilon=0.2,
        epsilon_decay_factor=0.995,
        # Bootstrapping and imitation learning
        n_bootstrap_games=250,  # Use EVAgent for first 250 games
        use_imitation_learning=True,  # Enable bootstrapping
        # Training configuration
        epsilon_decay_interval=100,  # Decay epsilon every 100 games
        progress_report_interval=100  # Report progress every 100 games
    )

    print("\n" + "="*70)
    print("TRAINING COMPLETE!")
    print("="*70)
    print(f"Trained agent has {len(agent.q_table)} states in Q-table")
    print(f"Win rate: {training_stats['wins']/training_stats['games_played']:.2%}")
    print(f"Average score: {np.mean(training_stats['scores']):.2f}")
    print("Use RL_analytics.py for full analysis and visualizations")