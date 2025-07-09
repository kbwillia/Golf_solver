#!/usr/bin/env python3
"""
RL Training Module

This module provides comprehensive training functions for Q-learning agents,
including bootstrapping, imitation learning, and hyperparameter control.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import *
from game import GolfGame
import numpy as np

# Create output directory if it doesn't exist
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(output_dir, exist_ok=True)

def get_output_path(filename):
    """Helper function to get full path for output files"""
    return os.path.join(output_dir, filename)

# ============================================================================
# DEDICATED TRAINING PHASE
# ============================================================================

def train_qlearning_agent(
    num_games=1000,
    opponent_type="ev_ai",
    verbose=True,
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
    Dedicated training phase for Q-learning agent with comprehensive parameters.
    Focus on training first, then return the trained agent for analysis.

    Args:
        num_games: Number of games to train on
        opponent_type: Type of opponent ("evagent", "random", etc.)
        verbose: Whether to print progress

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
        trained_agent: The trained QLearningAgent
        training_stats: Dictionary with training statistics
    """
    print("="*70)
    print("Q-LEARNING AGENT TRAINING PHASE")
    print("="*70)

    # Initialize agent with custom parameters
    agent = QLearningAgent(
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        n_bootstrap_games=n_bootstrap_games if use_imitation_learning else 0
    )

    # Set up opponent
    if opponent_type == "ev_ai":
        opponent_agent = EVAgent()
    elif opponent_type == "random":
        opponent_agent = RandomAgent()
    else:
        raise ValueError(f"Unknown opponent type: {opponent_type}")

    agent_types = ["qlearning", opponent_type]

    # Training statistics
    training_stats = {
        'games_played': 0,
        'wins': 0,
        'losses': 0,
        'scores': [],
        'qtable_states': [],
        'qtable_entries': [],
        'epsilon_values': []
    }

    print(f"Training against {opponent_type} for {num_games} games...")
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

    for game_num in range(num_games):
        # Create trajectory for this game
        trajectory = []

        # Play game
        game = GolfGame(num_players=2, agent_types=agent_types, q_agents=[agent, opponent_agent])
        game_scores = game.play_game(verbose=False, trajectories=[trajectory, None])

        # Determine winner and calculate reward
        winner_idx = game_scores.index(min(game_scores))
        qlearning_score = game_scores[0]
        opponent_score = game_scores[1]

        if winner_idx == 0:  # Q-learning agent won
            reward = 10.0
            training_stats['wins'] += 1
        else:
            training_stats['losses'] += 1
            # Reward based on score
            if qlearning_score <= 5:
                reward = 2.0
            elif qlearning_score <= 10:
                reward = 0.0
            elif qlearning_score <= 15:
                reward = -2.0
            else:
                reward = -5.0

        # Train the agent
        if trajectory:
            agent.train_on_trajectory(trajectory, reward, qlearning_score)
            agent.notify_game_end()

        # Record statistics
        training_stats['games_played'] += 1
        training_stats['scores'].append(qlearning_score)

        # Track Q-table growth
        states, entries = agent.get_q_table_size()
        training_stats['qtable_states'].append(states)
        training_stats['qtable_entries'].append(entries)
        training_stats['epsilon_values'].append(agent.epsilon)

        # Decay epsilon periodically
        if (game_num + 1) % epsilon_decay_interval == 0:
            agent.decay_epsilon(factor=epsilon_decay_factor)

        # Progress updates
        if verbose and (game_num + 1) % progress_report_interval == 0:
            win_rate = training_stats['wins'] / (game_num + 1)
            avg_score = np.mean(training_stats['scores'])
            bootstrap_status = "BOOTSTRAP" if game_num < n_bootstrap_games else "Q-LEARNING"
            print(f"  Game {game_num + 1}: {bootstrap_status} | Win rate={win_rate:.2%}, "
                  f"Avg score={avg_score:.2f}, States={states}, Epsilon={agent.epsilon:.3f}")

    # Final training statistics
    final_win_rate = training_stats['wins'] / num_games
    final_avg_score = np.mean(training_stats['scores'])
    final_states, final_entries = agent.get_q_table_size()

    print(f"\n🎯 TRAINING COMPLETE!")
    print(f"   • Games played: {num_games}")
    print(f"   • Win rate: {final_win_rate:.2%} ({training_stats['wins']}/{num_games})")
    print(f"   • Average score: {final_avg_score:.2f}")
    print(f"   • Final Q-table: {final_states} states, {final_entries} entries")
    print(f"   • Final epsilon: {agent.epsilon:.3f}")
    if use_imitation_learning:
        bootstrap_games = min(n_bootstrap_games, num_games)
        qlearning_games = max(0, num_games - n_bootstrap_games)
        print(f"   • Bootstrapping phase: {bootstrap_games} games")
        print(f"   • Q-learning phase: {qlearning_games} games")

    return agent, training_stats



if __name__ == "__main__":
    # Run the training function
    print("Starting Q-learning agent training...")
    agent, training_stats = train_qlearning_agent(
        num_games=1000,  # Train for 1000 games
        opponent_type="ev_ai",  # Train against EV agent
        verbose=True,
        # Q-learning hyperparameters
        learning_rate=0.1,
        discount_factor=0.9,
        epsilon=0.2,
        epsilon_decay_factor=0.995,
        # Bootstrapping and imitation learning
        n_bootstrap_games=1000,  # Use EVAgent for first 250 games
        use_imitation_learning=True,  # Enable bootstrapping
        # Training configuration
        epsilon_decay_interval=None,  # Decay epsilon every 100 games
        progress_report_interval=100  # Report progress every 100 games
    )

    print("\n" + "="*70)
    print("TRAINING COMPLETE!")
    print("="*70)
    print(f"Trained agent has {len(agent.q_table)} states in Q-table")
    print(f"Win rate: {training_stats['wins']/training_stats['games_played']:.2%}")
    print(f"Average score: {np.mean(training_stats['scores']):.2f}")
    print("Use RL_analytics.py for full analysis and visualizations")