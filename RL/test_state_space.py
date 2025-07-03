#!/usr/bin/env python3
"""
Test script to analyze Q-learning state space complexity and growth
"""

from simulation import run_simulations_with_training
from agents import QLearningAgent
from game import GolfGame
import matplotlib.pyplot as plt
import numpy as np

def analyze_state_space_growth():
    """Run training and track how the Q-table grows"""
    print("=== Q-LEARNING STATE SPACE ANALYSIS ===\n")

    # Test different numbers of training games
    test_sizes = [100]

    for num_games in test_sizes:
        print(f"Training for {num_games} games...")
        stats = run_simulations_with_training(
            num_games,
            ['random', 'qlearning'],
            verbose=False
        )

        # Get final Q-table size
        if 'q_learning_progress' in stats and stats['q_learning_progress']:
            final_progress = stats['q_learning_progress'][-1][1]
            if 'qlearning_1' in final_progress:
                states = final_progress['qlearning_1']['states']
                entries = final_progress['qlearning_1']['entries']

                print(f"  Final Q-table: {states:,} states, {entries:,} state-action pairs")
                print(f"  Avg actions per state: {entries/states:.1f}")

                # Calculate theoretical vs actual
                print(f"  Q-learning final score: {stats['average_scores']['qlearning']:.2f}")
                print(f"  Random baseline score: {stats['average_scores']['random']:.2f}")
                improvement = stats['average_scores']['random'] - stats['average_scores']['qlearning']
                print(f"  Improvement: {improvement:+.2f} points\n")

def test_state_representation():
    """Test the state representation by examining some actual states"""
    print("=== TESTING STATE REPRESENTATION ===\n")

    agent = QLearningAgent()

    # Create a few test games and see what states are generated
    for i in range(5):
        game = GolfGame(num_players=2, agent_types=['random', 'qlearning'], q_agents=[None, agent])

        # Play a few turns and check states
        turn_count = 0
        while not game.is_game_over() and turn_count < 10:
            current_player = game.players[game.turn]

            if game.turn == 1:  # Q-learning agent
                state_key = agent.get_state_key(current_player, game)
                print(f"Game {i+1}, Turn {turn_count+1}: {state_key}")

            # Make a move
            if hasattr(current_player, 'agent') and hasattr(current_player.agent, 'choose_action'):
                action = current_player.agent.choose_action(current_player, game)
                if action:
                    game.take_turn(action)
            else:
                # Simple random action for non-agent players
                positions = [i for i, known in enumerate(current_player.known) if not known]
                if positions and game.discard_pile:
                    action = {'type': 'take_discard', 'position': positions[0]}
                    game.take_turn(action)
                else:
                    break

            turn_count += 1

        print()

def compare_agent_performance():
    """Compare Q-learning vs other agents with smaller test"""
    print("=== AGENT PERFORMANCE COMPARISON ===\n")

        # Quick 100 game test
    stats = run_simulations_with_training(
        100,
        ['random', 'heuristic', 'qlearning'],
        verbose=False
    )

    print("Results after 100 games:")
    for agent_type in ['random', 'heuristic', 'qlearning']:
        avg_score = stats['average_scores'][agent_type]
        win_rate = stats['win_rates'][agent_type]
        print(f"  {agent_type:12}: {avg_score:5.2f} avg score, {win_rate:5.1%} win rate")

    # Show learning progress
    if 'score_by_interval' in stats and 'qlearning' in stats['score_by_interval']:
        intervals = stats['score_by_interval']['qlearning']
        if len(intervals) >= 2:
            first_avg = intervals[0]['avg_score']
            last_avg = intervals[-1]['avg_score']
            improvement = first_avg - last_avg
            print(f"\nQ-learning improvement: {improvement:+.2f} points ({first_avg:.2f} → {last_avg:.2f})")

if __name__ == "__main__":
    analyze_state_space_growth()
    test_state_representation()
    compare_agent_performance()