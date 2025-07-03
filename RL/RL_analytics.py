#!/usr/bin/env python3
"""
RL Analytics Module

This module provides comprehensive analysis tools for Q-learning agents,
including Q-table viewing, growth tracking, and performance analysis.
"""

from RL_agents import QLearningAgent
from RL.RL_game import GolfGame
from simulation import run_simulations_with_training
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from quick_test import train_agent_directly

# ============================================================================
# Q-TABLE TRAINING AND ACCESS
# ============================================================================



# ============================================================================
# Q-TABLE ANALYSIS AND DISPLAY
# ============================================================================

def analyze_qtable(q_table, verbose=True):
    """Analyze Q-table contents and show interesting patterns"""
    if verbose:
        print("\n" + "="*70)
        print("Q-TABLE ANALYSIS")
        print("="*70)

    if not q_table:
        if verbose:
            print("Q-table is empty!")
        return {}

    total_states = len(q_table)
    total_entries = sum(len(actions) for actions in q_table.values())

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
        for action_key, q_value in actions.items():
            all_qvalues.append(q_value)
            state_action_pairs.append((state_key, action_key, q_value))

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

        print(f"\nTop 10 highest Q-values:")
        print("State | Action | Q-value")
        print("-" * 70)
        for i, (state, action, qval) in enumerate(sorted_pairs[:10]):
            print(f"{state:<35} | {action:<20} | {qval:7.3f}")

        print(f"\nTop 10 lowest Q-values:")
        print("State | Action | Q-value")
        print("-" * 70)
        for i, (state, action, qval) in enumerate(sorted_pairs[-10:]):
            print(f"{state:<35} | {action:<20} | {qval:7.3f}")

    return stats

def display_full_qtable(q_table):
    """Display complete Q-table contents"""
    print(f"\n" + "="*70)
    print("COMPLETE Q-TABLE CONTENTS")
    print("="*70)

    if not q_table:
        print("Q-table is empty!")
        return

    print(f"{'State':<35} | {'Action':<20} | {'Q-value'}")
    print("-" * 70)

    for state_key in sorted(q_table.keys()):
        actions = q_table[state_key]
        for action_key in sorted(actions.keys()):
            q_value = actions[action_key]
            print(f"{state_key:<35} | {action_key:<20} | {q_value:8.3f}")

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

    if verbose:
        print("States by round:")
        for round_num in sorted(rounds.keys()):
            print(f"  Round {round_num}: {rounds[round_num]} states")

        print(f"\nStates by unknown card count:")
        for count in sorted(unknown_counts.keys()):
            print(f"  {count} unknown: {unknown_counts[count]} states")

        print(f"\nStates by known card count:")
        for count in sorted(known_card_counts.keys()):
            print(f"  {count} known: {known_card_counts[count]} states")

        print(f"\nTop 10 discard cards:")
        sorted_discards = sorted(discard_tops.items(), key=lambda x: x[1], reverse=True)
        for discard, count in sorted_discards[:10]:
            print(f"  {discard}: {count} states")

    return {
        'rounds': rounds,
        'unknown_counts': unknown_counts,
        'discard_tops': discard_tops,
        'known_card_counts': known_card_counts
    }

# ============================================================================
# Q-TABLE GROWTH TRACKING
# ============================================================================

def track_qtable_growth(num_games=500, checkpoint_interval=25, verbose=True):
    """Track Q-table growth during training"""
    if verbose:
        print(f"Tracking Q-table growth over {num_games} games...")

    agent = QLearningAgent()

    # Track growth
    game_checkpoints = []
    state_counts = []
    entry_counts = []
    scores = []

    for game_num in range(num_games):
        # Create trajectories for training
        trajectory = []

        # Create and play game
        game = GolfGame(num_players=2, agent_types=['random', 'qlearning'], q_agents=[None, agent])
        game_scores = game.play_game(verbose=False, trajectories=[None, trajectory])

        # Train the agent
        winner_idx = game_scores.index(min(game_scores))
        if trajectory:
            # Calculate reward
            if winner_idx == 1:  # Q-learning agent won
                reward = 10.0
            else:
                # Reward based on score
                if game_scores[1] <= 5:
                    reward = 2.0
                elif game_scores[1] <= 10:
                    reward = 0.0
                elif game_scores[1] <= 15:
                    reward = -2.0
                else:
                    reward = -5.0

            agent.train_on_trajectory(trajectory, reward, game_scores[1])

        # Track at checkpoints
        if (game_num + 1) % checkpoint_interval == 0:
            states = len(agent.q_table)
            entries = sum(len(actions) for actions in agent.q_table.values())
            score = game_scores[1]

            game_checkpoints.append(game_num + 1)
            state_counts.append(states)
            entry_counts.append(entries)
            scores.append(score)

            if verbose:
                print(f"Game {game_num+1:3d}: {states:3d} states, {entries:4d} entries, score: {score:5.1f}")

    return agent, game_checkpoints, state_counts, entry_counts, scores

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

# ============================================================================
# PLOTTING AND VISUALIZATION
# ============================================================================

def plot_qtable_growth(games, states, entries, scores, save_filename="qtable_growth.png"):
    """Plot Q-table growth charts"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

    # Plot 1: States over time
    ax1.plot(games, states, 'b-', linewidth=2, marker='o', markersize=4)
    ax1.set_xlabel('Games Played')
    ax1.set_ylabel('Number of States')
    ax1.set_title('Q-table State Count Growth')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Entries over time
    ax2.plot(games, entries, 'g-', linewidth=2, marker='s', markersize=4)
    ax2.set_xlabel('Games Played')
    ax2.set_ylabel('Number of State-Action Pairs')
    ax2.set_title('Q-table Entry Count Growth')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Performance over time (moving average)
    if len(scores) > 5:
        # Calculate moving average
        window = min(5, len(scores))
        moving_avg = np.convolve(scores, np.ones(window)/window, mode='valid')
        games_avg = games[window-1:]
        ax3.plot(games, scores, 'r-', alpha=0.3, label='Individual')
        ax3.plot(games_avg, moving_avg, 'r-', linewidth=2, label='Moving Avg')
        ax3.legend()
    else:
        ax3.plot(games, scores, 'r-', linewidth=2, marker='^', markersize=4)

    ax3.set_xlabel('Games Played')
    ax3.set_ylabel('Score')
    ax3.set_title('Performance Over Time')
    ax3.grid(True, alpha=0.3)
    ax3.invert_yaxis()  # Lower scores are better

    # Plot 4: Actions per state
    actions_per_state = [e/s if s > 0 else 0 for e, s in zip(entries, states)]
    ax4.plot(games, actions_per_state, 'm-', linewidth=2, marker='d', markersize=4)
    ax4.set_xlabel('Games Played')
    ax4.set_ylabel('Actions per State')
    ax4.set_title('Q-table Density')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_filename, dpi=300, bbox_inches='tight')
    print(f"\nPlots saved to {save_filename}")
    plt.show()

def plot_qvalue_distribution(q_table, save_filename="qvalue_distribution.png"):
    """Plot Q-value distribution"""
    if not q_table:
        print("No Q-table data to plot!")
        return

    # Extract all Q-values
    all_qvalues = [q for actions in q_table.values() for q in actions.values()]

    if not all_qvalues:
        print("No Q-values found!")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Histogram of Q-values
    ax1.hist(all_qvalues, bins=30, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Q-value')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Q-value Distribution')
    ax1.grid(True, alpha=0.3)

    # Box plot of Q-values
    ax2.boxplot(all_qvalues)
    ax2.set_ylabel('Q-value')
    ax2.set_title('Q-value Box Plot')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_filename, dpi=300, bbox_inches='tight')
    print(f"Q-value distribution plots saved to {save_filename}")
    plt.show()

# ============================================================================
# DATA EXPORT
# ============================================================================

def save_qtable_to_csv(q_table, filename="qtable_export.csv"):
    """Save Q-table to CSV for external analysis"""
    data = []
    for state_key, actions in q_table.items():
        for action_key, q_value in actions.items():
            data.append({
                'state': state_key,
                'action': action_key,
                'q_value': q_value
            })

    if data:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"\nQ-table exported to {filename} ({len(data)} entries)")
        return df
    else:
        print("\nNo Q-table data to save!")
        return None

def save_growth_data(games, states, entries, scores, filename="growth_data.csv"):
    """Save growth tracking data to CSV"""
    data = {
        'games': games,
        'states': states,
        'entries': entries,
        'scores': scores
    }

    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Growth data exported to {filename} ({len(games)} data points)")
    return df

# ============================================================================
# COMPREHENSIVE ANALYSIS FUNCTIONS
# ============================================================================

def full_qtable_analysis(num_games=100, show_full_table=False):
    """Perform complete Q-table analysis"""
    print("="*70)
    print("COMPREHENSIVE Q-TABLE ANALYSIS")
    print("="*70)

    # Train agent
    agent = train_agent_directly(num_games, verbose=True)

    # Analyze Q-table
    stats = analyze_qtable(agent.q_table, verbose=True)
    patterns = analyze_state_patterns(agent.q_table, verbose=True)

    # Show full table if requested
    if show_full_table:
        display_full_qtable(agent.q_table)

    # Save data
    save_qtable_to_csv(agent.q_table)

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
    plot_qtable_growth(games, states, entries, scores)

    # Save data
    save_growth_data(games, states, entries, scores)

    # Final Q-table analysis
    print(f"\n" + "="*50)
    print("FINAL Q-TABLE STATE")
    print("="*50)
    qtable_stats = analyze_qtable(agent.q_table, verbose=True)

    return agent, growth_stats, qtable_stats

# ============================================================================
# MAIN EXECUTION FUNCTIONS
# ============================================================================

def quick_qtable_view(num_games=50):
    """Quick Q-table viewer for testing"""
    print("QUICK Q-TABLE VIEWER")
    print("="*50)

    agent = train_agent_directly(num_games, verbose=True)
    analyze_qtable(agent.q_table, verbose=True)
    analyze_state_patterns(agent.q_table, verbose=True)
    # Always save Q-table to CSV
    save_qtable_to_csv(agent.q_table, filename="qtable_export.csv")
    print("Q-table saved to qtable_export.csv")
    return agent

def quick_growth_view(num_games=100, checkpoint_interval=10):
    """Quick growth viewer for testing"""
    print("QUICK GROWTH VIEWER")
    print("="*50)

    agent, games, states, entries, scores = track_qtable_growth(
        num_games, checkpoint_interval, verbose=True
    )

    analyze_growth_patterns(games, states, entries, scores)
    plot_qtable_growth(games, states, entries, scores, "quick_growth.png")

    return agent, games, states, entries, scores

if __name__ == "__main__":
    # Example usage
    print("RL ANALYTICS MODULE")
    print("Available functions:")

    print("- full_qtable_analysis(num_games=100)")

    # Run a quick demo
    quick_qtable_view(num_games=25)
