#!/usr/bin/env python3
"""
RL Analytics Module

This module provides comprehensive analysis tools for Q-learning agents,
including Q-table viewing, growth tracking, and performance analysis.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import *
from game import GolfGame
import pandas as pd
import numpy as np
import csv
from RL.RL_viz import *
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from tqdm import trange
import time

# Create output directory if it doesn't exist
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(output_dir, exist_ok=True)

def get_output_path(filename):
    """Helper function to get full path for output files"""
    return os.path.join(output_dir, filename)



def analyze_qtable(q_table, verbose=True):
    """Analyze Q-table contents and show interesting patterns (supports dict or tensor Q-tables)"""
    if verbose:
        print("\n" + "="*70)
        print("Q-TABLE ANALYSIS")
        print("="*70)

    if not q_table:
        if verbose:
            print("Q-table is empty!")
        return {}

    total_states = len(q_table)
    # For tensor Q-tables, each value is a tensor, not a dict
    def get_num_actions(actions):
        if isinstance(actions, dict):
            return len(actions)
        elif hasattr(actions, 'shape'):
            return actions.shape[0]
        else:
            return 0
    total_entries = sum(get_num_actions(actions) for actions in q_table.values())

    stats = {
        'total_states': total_states,
        'total_entries': total_entries,
        'avg_actions_per_state': total_entries/total_states if total_states > 0 else 0
    }

    if verbose:
        print(f"Total states: {total_states:,}")
        print(f"Total state-action pairs: {total_entries:,}")
        print(f"Average actions per state: {stats['avg_actions_per_state']:.1f}")

    # Convert to flat list for analysis
    all_qvalues = []
    state_action_pairs = []

    for state_key, actions in q_table.items():
        if isinstance(actions, dict):
            for action_key, q_value in actions.items():
                if not np.isnan(q_value):  # Only include non-NaN values
                    all_qvalues.append(q_value)
                    state_action_pairs.append((state_key, action_key, q_value))
        elif hasattr(actions, 'shape'):
            for action_idx in range(actions.shape[0]):
                q_value = actions[action_idx].item()
                if not np.isnan(q_value):  # Only include non-NaN values
                    state_action_pairs.append((state_key, action_idx, q_value))
                    all_qvalues.append(q_value)

    if not all_qvalues:
        if verbose:
            print("No Q-values found!")
        return stats

    stats.update({
        'min_qvalue': min(all_qvalues),
        'max_qvalue': max(all_qvalues),
        'mean_qvalue': np.mean(all_qvalues),
        'std_qvalue': np.std(all_qvalues),
        'total_qvalues': len(all_qvalues)
    })

    if verbose:
        print(f"\nQ-value statistics:")
        print(f"  Min Q-value: {stats['min_qvalue']:.3f}")
        print(f"  Max Q-value: {stats['max_qvalue']:.3f}")
        print(f"  Mean Q-value: {stats['mean_qvalue']:.3f}")
        print(f"  Std Q-value: {stats['std_qvalue']:.3f}")

        # Show top and bottom Q-values
        sorted_pairs = sorted(state_action_pairs, key=lambda x: x[2], reverse=True)

    return stats



def analyze_state_patterns(q_table, verbose=True):
    """Analyze patterns in the states"""
    if verbose:
        print(f"\n" + "="*70)
        print("STATE PATTERN ANALYSIS")
        print("="*70)

    if not q_table:
        return {}

    # Parse state components
    rounds = {}
    unknown_counts = {}
    discard_tops = {}
    known_card_counts = {}

    for state_key in q_table.keys():
        try:
            # Parse state format: ['A', 'K']_2_7_3
            parts = state_key.split('_')
            if len(parts) >= 4:
                known_cards_str = parts[0]
                unknown_count = int(parts[1])
                discard_top = parts[2]
                round_num = int(parts[3])

                # Count known cards
                if known_cards_str.startswith('[') and known_cards_str.endswith(']'):
                    cards_content = known_cards_str[1:-1]
                    if cards_content.strip():
                        known_card_count = len(cards_content.split(','))
                    else:
                        known_card_count = 0
                else:
                    known_card_count = 0

                # Track statistics
                rounds[round_num] = rounds.get(round_num, 0) + 1
                unknown_counts[unknown_count] = unknown_counts.get(unknown_count, 0) + 1
                discard_tops[discard_top] = discard_tops.get(discard_top, 0) + 1
                known_card_counts[known_card_count] = known_card_counts.get(known_card_count, 0) + 1
        except:
            continue

    # if verbose:
        # print("States by round:")
        # for round_num in sorted(rounds.keys()):
        #     # print(f"  Round {round_num}: {rounds[round_num]} states")


        # print(f"\nStates by known card count:")
        # for count in sorted(known_card_counts.keys()):
        #     print(f"  {count} known: {known_card_counts[count]} states")

        # print(f"\nTop 10 discard cards:")
        # sorted_discards = sorted(discard_tops.items(), key=lambda x: x[1], reverse=True)
        # for discard, count in sorted_discards[:10]:
        #     print(f"  {discard}: {count} states")

    # return {
    #     'rounds': rounds,
    #     'unknown_counts': unknown_counts,
    #     'discard_tops': discard_tops,
    #     'known_card_counts': known_card_counts
    # }


def analyze_growth_patterns(games, states, entries, scores=None):
    """Analyze Q-table growth patterns"""
    print(f"\n" + "="*50)
    print("GROWTH ANALYSIS")
    print("="*50)

    if len(games) < 2:
        print("Not enough data points for analysis")
        return {}

    # Calculate growth rates
    state_growth_rates = []
    entry_growth_rates = []

    for i in range(1, len(games)):
        games_diff = games[i] - games[i-1]
        state_diff = states[i] - states[i-1]
        entry_diff = entries[i] - entries[i-1]

        state_growth_rate = state_diff / games_diff if games_diff > 0 else 0
        entry_growth_rate = entry_diff / games_diff if games_diff > 0 else 0

        state_growth_rates.append(state_growth_rate)
        entry_growth_rates.append(entry_growth_rate)

    # Final statistics
    final_states = states[-1]
    final_entries = entries[-1]
    total_games = games[-1]

    analysis = {
        'total_games': total_games,
        'final_states': final_states,
        'final_entries': final_entries,
        'avg_state_growth_rate': np.mean(state_growth_rates),
        'avg_entry_growth_rate': np.mean(entry_growth_rates),
        'actions_per_state': final_entries/final_states if final_states > 0 else 0,
        'state_discovery_rate': final_states/total_games,
        'entry_growth_rate': final_entries/total_games,
        'state_space_utilization': final_states/133280  # Based on our calculation
    }

    print(f"Average state discovery rate: {analysis['avg_state_growth_rate']:.2f} states/game")
    print(f"Average entry growth rate: {analysis['avg_entry_growth_rate']:.2f} entries/game")
    print(f"\nFinal statistics:")
    print(f"  Total games: {analysis['total_games']}")
    print(f"  Final states: {analysis['final_states']:,}")
    print(f"  Final entries: {analysis['final_entries']:,}")
    print(f"  Actions per state: {analysis['actions_per_state']:.1f}")
    print(f"  State discovery rate: {analysis['state_discovery_rate']:.2f} states/game")
    print(f"  Entry growth rate: {analysis['entry_growth_rate']:.1f} entries/game")
    print(f"  State space utilization: {analysis['state_space_utilization']:.1%}")

    return analysis


def save_qtable_to_csv(q_table, filename, agent, state_action_last_action_map=None):
    """
    Save Q-table to CSV file for external analysis

    Args:
        q_table: The Q-table dictionary
        filename: Output CSV filename
        agent: The QLearningAgent instance (for debug state info)
        state_action_last_action_map: Optional mapping of states to last actions
    """
    output_path = get_output_path(filename)
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['state', 'action', 'q_value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for state, actions in q_table.items():
            if isinstance(actions, dict):
                for action, q_value in actions.items():
                    if not np.isnan(q_value):  # Only save explored actions
                        writer.writerow({'state': state, 'action': action, 'q_value': q_value})
            elif hasattr(actions, 'shape'):
                for action_idx in range(actions.shape[0]):
                    q_value = actions[action_idx].item()
                    if not np.isnan(q_value):  # Only save explored actions
                        writer.writerow({'state': state, 'action': action_idx, 'q_value': q_value})

    print(f"Q-table saved to {output_path} with {sum(1 for _ in csv.DictReader(open(output_path))) - 1} entries")

def parse_state_for_last_action(state_key):
    """Parse state key to extract context about the game situation"""
    try:
        # Expected format: "('3', '6', '7')_-1.5_J_4"
        parts = state_key.split('_')
        if len(parts) >= 4:
            known_cards = parts[0]     # e.g., "('3', '6', '7')"
            draw_advantage = parts[1]  # e.g., "-1.5"
            discard_rank = parts[2]    # e.g., "J"
            round_num = parts[3]       # e.g., "4"

            # Create a context string that gives insight into the situation
            if float(draw_advantage) < -0.5:
                decision_context = "Draw favored"
            elif float(draw_advantage) > 0.5:
                decision_context = "Discard favored"
            else:
                decision_context = "Close decision"

            return f"R{round_num}: {decision_context}, Discard:{discard_rank}"
        else:
            return f"Context: {state_key[:30]}..."
    except:
        return f"Unknown context"

def save_growth_data(games, states, entries, scores, filename="growth_data.csv"):
    """Save growth tracking data to CSV"""
    data = {
        'games': games,
        'states': states,
        'entries': entries,
        'scores': scores
    }

    df = pd.DataFrame(data)
    output_path = get_output_path(filename)
    df.to_csv(output_path, index=False)
    print(f"Growth data exported to {output_path} ({len(games)} data points)")
    return df

def save_trajectory_to_csv(trajectory, filename):
    """
    Save a trajectory to a CSV file.
    This function is designed to export the full trajectory, including duplicates.
    """
    output_path = get_output_path(filename)
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['state_key', 'action_key', 'action', 'game', 'round']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for step in trajectory:
            writer.writerow({
                'state_key': step['state_key'],
                'action_key': step['action_key'],
                'action': step['action'],
                'round': step.get('round', '?'),
                'game': step.get('game', '?'),
                # 'last_action': step.get('last_action', '')
            })
    print(f"Trajectory saved to {output_path} with {len(trajectory)} steps")

# Import training function from the new training module
from RL.train import train_qlearning_agent

def analyze_trained_agent(agent, training_stats, save_prefix="trained_agent", opponent_type="ev_ai"):
    """
    Analyze a trained Q-learning agent and generate visualizations.

    Args:
        agent: Trained QLearningAgent
        training_stats: Statistics from training phase
        save_prefix: Prefix for saved files

    Returns:
        analysis_results: Dictionary with analysis results
    """
    print("="*70)
    print("TRAINED AGENT ANALYSIS PHASE")
    print("="*70)

    # 1. Q-table analysis
    qtable_stats = analyze_qtable(agent.q_table, verbose=True)
    state_patterns = analyze_state_patterns(agent.q_table, verbose=True)

    # 2. Training progress visualizations
    games = list(range(1, len(training_stats['scores']) + 1))

    # Plot Q-table growth during training (combined state/entry growth)
    plot_qtable_state_and_entry_growth(
        games,
        training_stats['qtable_states'],
        training_stats['qtable_entries'],
        save_filename=f"{save_prefix}_qtable_state_entry_growth.png"
    )

    # Plot learning curves
    # Combine scores from both agents into the expected format
    all_scores = [[qlearning_score, opponent_score] for qlearning_score, opponent_score in
                  zip(training_stats['scores'], training_stats['opponent_scores'])]

    plot_learning_curves(
        games,
        all_scores,  # Both agents' scores
        ["qlearning", opponent_type],
        save_filename=f"{save_prefix}_learning_curve.png"
    )

    # 3. Q-value distribution
    plot_qvalue_distribution(
        agent.q_table,
        save_filename=f"{save_prefix}_qvalue_distribution.png"
    )

    # 4. Save Q-table
    save_qtable_to_csv(
        agent.q_table,
        f"{save_prefix}_qtable.csv",
        agent
    )

    # 5. Action type tracking visualization
    # Load the full trajectory from the output CSV
    import csv
    trajectory_path = get_output_path("trajectory_train.csv")
    trajectory = []
    if os.path.exists(trajectory_path):
        with open(trajectory_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Reconstruct action as dict if possible, else keep as string
                try:
                    import ast
                    action = ast.literal_eval(row['action']) if 'action' in row and row['action'].startswith('{') else row['action']
                except:
                    action = row['action']
                trajectory.append({
                    'state_key': row['state_key'],
                    'action_key': row['action_key'],
                    'action': action,
                    'game': int(row['game']) if row['game'] != '?' else None,
                    'round': int(row['round']) if row['round'] != '?' else None
                })
        # Plot action type tracking
        plot_action_type_tracking(
            trajectory,
            round_info=True,
            save_filename=f"{save_prefix}_action_type_tracking.png"
        )

    # 5. Theoretical state space comparison
    theoretical_stats = calculate_theoretical_state_space()
    actual_states = len(agent.q_table)
    utilization = actual_states / theoretical_stats if theoretical_stats > 0 else 0

    print(f"\n📊 STATE SPACE UTILIZATION:")
    print(f"   • Theoretical max states: {theoretical_stats:,}")
    print(f"   • Actual states discovered: {actual_states:,}")
    print(f"   • Utilization: {utilization:.2%}")

    analysis_results = {
        'qtable_stats': qtable_stats,
        'state_patterns': state_patterns,
        'training_stats': training_stats,
        'state_space_utilization': utilization,
        'theoretical_states': theoretical_stats,
        'actual_states': actual_states
    }

    # Save persistent Q-table for incremental learning
    agent.save_q_table_csv()  # This will save to output/qtable_train.csv by default

    return analysis_results

# ============================================================================
# COMPREHENSIVE TRAINING + ANALYSIS WORKFLOW
# ============================================================================

def complete_training_and_analysis_workflow(
    training_games=1000,
    batch_size=100,  # Number of games to play simultaneously
    opponent_type="ev_ai",
    verbose=True,
    save_prefix="complete_analysis",
    use_gpu=True,  # Enable GPU acceleration
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
    Complete workflow: Train agent first, then analyze thoroughly.
    Uses batch training for better GPU utilization.

    Args:
        training_games: Number of games for training
        batch_size: Number of games to play simultaneously (for GPU efficiency)
        opponent_type: Type of opponent
        verbose: Whether to print progress
        save_prefix: Prefix for saved files
        use_gpu: Whether to use GPU acceleration

        # Q-learning hyperparameters
        learning_rate: Learning rate for Q-value updates
        discount_factor: Discount factor for future rewards
        epsilon: Initial exploration rate
        epsilon_decay_factor: Factor to decay epsilon

        # Bootstrapping and imitation learning
        n_bootstrap_games: Number of games to use EVAgent for bootstrapping
        use_imitation_learning: Whether to use EVAgent for initial imitation

        # Training configuration
        epsilon_decay_interval: How often to decay epsilon
        progress_report_interval: How often to report progress

    Returns:
        agent: Trained QLearningAgent
        results: Complete analysis results
    """
    print("🚀 STARTING COMPLETE BATCH TRAINING + ANALYSIS WORKFLOW")
    print("="*70)
    start_time = time.time()

    # Phase 1: Batch Training
    from RL.train import train_qlearning_agent_batch

    agent, training_stats = train_qlearning_agent_batch(
        num_games=training_games,
        batch_size=batch_size,
        opponent_type=opponent_type,
        verbose=verbose,
        use_gpu=use_gpu,
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        epsilon_decay_factor=epsilon_decay_factor,
        n_bootstrap_games=n_bootstrap_games,
        use_imitation_learning=use_imitation_learning,
        epsilon_decay_interval=epsilon_decay_interval,
        progress_report_interval=progress_report_interval
    )

    # Phase 2: Analysis
    analysis_results = analyze_trained_agent(
        agent=agent,
        training_stats=training_stats,
        save_prefix=save_prefix,
        opponent_type=opponent_type
    )

    # Phase 3: Summary
    print(f"\n🎉 WORKFLOW COMPLETE!")
    print(f"   • Training: {training_games} games vs {opponent_type}")
    print(f"   • Final win rate: {training_stats['wins']/training_games:.2%}")
    print(f"   • Q-table size: {len(agent.q_table)} states")
    print(f"   • Files saved with prefix: {save_prefix}")

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"\n⏱️ Total runtime: {elapsed:.2f} seconds")

    return agent, analysis_results

# ============================================================================
# COMPREHENSIVE ANALYSIS FUNCTIONS
# ============================================================================

def full_qtable_analysis(num_games=100, show_full_table=False, use_gpu=True, batch_size=50):
    """Perform complete Q-table analysis using batch training"""
    print("="*70)
    print("COMPREHENSIVE Q-TABLE ANALYSIS (BATCH TRAINING)")
    print("="*70)

    # Train agent using batch training
    from RL.train import train_qlearning_agent_batch

    agent, training_stats = train_qlearning_agent_batch(
        num_games=num_games,
        batch_size=batch_size,
        opponent_type="ev_ai",
        verbose=True,
        use_gpu=use_gpu
    )

    # Analyze Q-table
    stats = analyze_qtable(agent.q_table, verbose=True)
    patterns = analyze_state_patterns(agent.q_table, verbose=True)

    # Show full table if requested
    if show_full_table:
        display_full_qtable(agent.q_table)

    # Save data
    save_qtable_to_csv(agent.q_table, "qtable_export.csv", agent)

    # Plot Q-value distribution
    plot_qvalue_distribution(agent.q_table)

    return agent, stats, patterns

def full_growth_analysis(num_games=200, checkpoint_interval=10):
    """Perform complete growth analysis"""
    print("="*70)
    print("COMPREHENSIVE GROWTH ANALYSIS")
    print("="*70)

    # Track growth
    agent, games, states, entries, scores = track_qtable_growth(
        num_games, checkpoint_interval, verbose=True
    )

    # Analyze growth patterns
    growth_stats = analyze_growth_patterns(games, states, entries, scores)

    # Plot growth
    # plot_qtable_growth(games, states, entries, scores) # This line was removed

    # Save data
    save_growth_data(games, states, entries, scores)

    # Final Q-table analysis
    print(f"\n" + "="*50)
    print("FINAL Q-TABLE STATE")
    print("="*50)
    qtable_stats = analyze_qtable(agent.q_table, verbose=True)

    return agent, growth_stats, qtable_stats





def main(num_games=200, verbose=True, opponent_type="ev_ai", use_gpu=True, batch_size=100):
    print("="*70)
    print("Q-LEARNING AGENT COMPLETE ANALYSIS (BATCH TRAINING)")
    print("="*70)

    # Use the complete workflow function instead
    agent, results = complete_training_and_analysis_workflow(
        training_games=num_games,
        batch_size=batch_size,
        opponent_type=opponent_type,
        verbose=verbose,
        save_prefix=f"analysis_{num_games}_games_batch",
        use_gpu=use_gpu
    )

    return agent, results

if __name__ == "__main__":
    # Run the complete batch training + analysis workflow
    print("Starting Q-learning agent batch training and analysis...")
    training_games = 500 # matched to 2.8% of state space
    n_bootstrap_games = training_games * 0.75
    agent, results = complete_training_and_analysis_workflow(
        training_games=training_games,  # Train for 500 games
        batch_size=200,  # Batch size for GPU efficiency
        opponent_type="ev_ai",  # Train against EV agent
        verbose=True,
        save_prefix="trained_agent_500_games_batch",
        use_gpu=False,  # Enable GPU acceleration
        # Q-learning hyperparameters
        learning_rate=0.1,
        discount_factor=0.9,
        epsilon=0.2,
        epsilon_decay_factor=1.0, #0.995
        # Bootstrapping and imitation learning
        n_bootstrap_games=n_bootstrap_games,  # Use EVAgent for first 375 games
        use_imitation_learning=True,  # Enable bootstrapping
        # Training configuration
        epsilon_decay_interval=100,  # Decay epsilon every 100 games
        progress_report_interval=100  # Report progress every 100 games
    )

    print("\n" + "="*70)
    print("FINAL RESULTS SUMMARY")
    print("="*70)
    print(f"Trained agent has {len(agent.q_table)} states in Q-table")
    print(f"Win rate: {results['training_stats']['wins']/results['training_stats']['games_played']:.2%}")
    print(f"State space utilization: {results['state_space_utilization']:.2%}")
    print("All visualizations and data saved to output/ directory")