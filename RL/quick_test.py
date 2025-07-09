#!/usr/bin/env python3
"""
Quick test of Q-learning performance with visualizations
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

from game import GolfGame
from models import Player
from agents import RandomAgent, HeuristicAgent, QLearningAgent, EVAgent, AdvancedEVAgent

def create_visualizations(agent_types, all_scores, game_numbers, avg_scores, wins, total_games):
    """Create matplotlib/seaborn visualizations"""
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")

    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # 1. Game Progression Plot (Games vs Score)
    # Calculate running averages for each agent
    for i, agent in enumerate(agent_types):
        agent_scores = [scores[i] for scores in all_scores]
        running_avg = np.cumsum(agent_scores) / np.arange(1, len(agent_scores) + 1)

        # Color mapping for agents
        colors = {
            "random": "#FF6B6B",
            "heuristic": "#4ECDC4",
            "qlearning": "#45B7D1",
            "ev_ai": "#96CEB4",
            "advanced_ev": "#FFEAA7",
            "human": "#DDA0DD"
        }

        color = colors.get(agent, "#95A5A6")
        ax1.plot(game_numbers, running_avg, label=agent, color=color, linewidth=2, alpha=0.8)

    ax1.set_xlabel('Game Number', fontsize=12)
    ax1.set_ylabel('Running Average Score', fontsize=12)
    ax1.set_title('Agent Performance Over Time (Running Average)', fontsize=14, fontweight='bold')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, total_games)

    # Add horizontal line at y=0 for reference
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.5, label='Zero Score')

    # 2. Score Distribution Plot
    # Prepare data for distribution plot
    distribution_data = []
    for i, agent in enumerate(agent_types):
        agent_scores = [scores[i] for scores in all_scores]
        for score in agent_scores:
            distribution_data.append({'Agent': agent, 'Score': score})

    df = pd.DataFrame(distribution_data)

    # Create violin plot with individual points
    sns.violinplot(data=df, x='Agent', y='Score', ax=ax2, inner='box', alpha=0.7)

    # Add individual points with jitter
    sns.stripplot(data=df, x='Agent', y='Score', ax=ax2, size=3, alpha=0.4, color='black', jitter=0.2)

    # Add mean lines
    for i, agent in enumerate(agent_types):
        agent_scores = [scores[i] for scores in all_scores]
        mean_score = np.mean(agent_scores)
        ax2.axhline(y=mean_score, color='red', linestyle='--', alpha=0.7, xmin=i/len(agent_types), xmax=(i+1)/len(agent_types))

    ax2.set_xlabel('Agent Type', fontsize=12)
    ax2.set_ylabel('Score', fontsize=12)
    ax2.set_title('Score Distribution by Agent Type', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # Rotate x-axis labels for better readability
    ax2.tick_params(axis='x', rotation=45)

    # Add statistics text
    stats_text = f"Total Games: {total_games}\n"
    for i, agent in enumerate(agent_types):
        agent_scores = [scores[i] for scores in all_scores]
        mean_score = np.mean(agent_scores)
        std_score = np.std(agent_scores)
        win_rate = (wins[i] / total_games) * 100
        stats_text += f"{agent}: μ={mean_score:.2f}, σ={std_score:.2f}, Win%={win_rate:.1f}%\n"

    # Add text box with statistics
    ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, fontsize=9,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()

    # Save the plot
    plot_filename = f"agent_performance_comparison_{total_games}_games.png"
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')

    # Show the plot
    plt.show()

    return plot_filename

def quick_test(agent_types, num_games):
    """Quick test with minimal output, just generates graphs"""
    num_agents = len(agent_types)
    total_scores = [0] * num_agents
    wins = [0] * num_agents

    # Track all scores for visualization
    all_scores = []
    game_numbers = []

    print(f"Running {num_games} games with {num_agents} agents...")

    for game_num in range(num_games):
        game = GolfGame(num_players=num_agents, agent_types=agent_types)
        scores = game.play_game(verbose=False)

        # Track scores and wins
        for i, score in enumerate(scores):
            total_scores[i] += score

        # Track wins (lowest score wins)
        winner_idx = scores.index(min(scores))
        wins[winner_idx] += 1

        # Store data for visualization
        all_scores.append(scores)
        game_numbers.append(game_num + 1)

    # Calculate averages
    avg_scores = [total / num_games for total in total_scores]

    # Create visualizations
    plot_filename = create_visualizations(agent_types, all_scores, game_numbers, avg_scores, wins, num_games)

    return avg_scores, wins, plot_filename

if __name__ == "__main__":
    quick_test(["ev_ai", "random", "heuristic", "advanced_ev"], 100)