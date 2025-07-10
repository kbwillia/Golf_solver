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
from tqdm import trange
import torch
import torch.nn as nn
import torch.optim as optim
from collections import defaultdict
import time

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

    def get_q_value(self, state, action):
        """Get Q-value using GPU tensors"""
        state_key = str(state)
        if state_key not in self.q_table:
            # Initialize with zeros on GPU
            self.q_table[state_key] = torch.zeros(12, dtype=torch.float32, device=self.device)

        return self.q_table[state_key][action].item()

    def update_q_value(self, state, action, new_value):
        """Update Q-value using GPU tensors"""
        state_key = str(state)
        if state_key not in self.q_table:
            self.q_table[state_key] = torch.zeros(12, dtype=torch.float32, device=self.device)

        # Update the tensor value
        self.q_table[state_key][action] = new_value

    def get_best_action(self, state, legal_actions):
        """Get best action using GPU tensors"""
        state_key = str(state)
        if state_key not in self.q_table:
            self.q_table[state_key] = torch.zeros(12, dtype=torch.float32, device=self.device)

        # Get Q-values for all actions
        q_values = self.q_table[state_key]

        # Mask illegal actions with very low values
        mask = torch.ones(12, dtype=torch.bool, device=self.device)
        mask[legal_actions] = False
        q_values_masked = q_values.clone()
        q_values_masked[mask] = float('-inf')

        # Return best legal action
        return torch.argmax(q_values_masked).item()

    def train_on_trajectory(self, trajectory, reward, final_score):
        """Train on trajectory using GPU acceleration"""
        if not trajectory:
            return

        # Convert trajectory to tensors for batch processing
        states = []
        actions = []
        next_states = []

        for state, action, next_state in trajectory:
            states.append(state_to_tensor(state, self.device))
            actions.append(action)
            next_states.append(state_to_tensor(next_state, self.device))

        # Batch process updates
        for i, (state, action, next_state) in enumerate(zip(states, actions, next_states)):
            current_q = self.get_q_value(str(state), action)

            # Calculate target Q-value
            if i == len(trajectory) - 1:  # Final state
                target_q = reward
            else:
                # Get max Q-value for next state
                next_state_key = str(next_state)
                if next_state_key in self.q_table:
                    next_q_values = self.q_table[next_state_key]
                    max_next_q = torch.max(next_q_values).item()
                else:
                    max_next_q = 0.0
                target_q = reward + self.discount_factor * max_next_q

            # Update Q-value
            new_q = current_q + self.learning_rate * (target_q - current_q)
            self.update_q_value(str(state), action, new_q)

    def get_q_table_size(self):
        """Get Q-table size information"""
        total_entries = sum(len(q_tensor) for q_tensor in self.q_table.values())
        return len(self.q_table), total_entries

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
        num_games=1000,  # Train for 1000 games
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