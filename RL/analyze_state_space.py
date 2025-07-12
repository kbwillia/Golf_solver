#!/usr/bin/env python3
"""
Comprehensive Golf Q-Learning State Space Analysis

This script analyzes the state representation used in your Q-learning agent
and calculates both theoretical and actual state space sizes.
"""

from RL_agents import QLearningAgent
from RL.RL_game import GolfGame
from models import Card
import math
from collections import defaultdict

def analyze_state_representation():
    """Examine how the Q-learning agent represents states"""
    print("=== STATE REPRESENTATION ANALYSIS ===\n")

    # Look at the get_state_key method
    print("Current state representation (from agents.py, line ~264):")
    print("```python")
    print("def get_state_key(self, player, game_state):")
    print("    known_cards = []")
    print("    for i, card in enumerate(player.grid):")
    print("        if player.known[i] and card:")
    print("            known_cards.append(card.rank)  # Only rank, not suit")
    print("        else:")
    print("            known_cards.append('?')")
    print("    ")
    print("    # Sort known cards for consistency")
    print("    known_cards_sorted = sorted([c for c in known_cards if c != '?'])")
    print("    unknown_count = known_cards.count('?')")
    print("    ")
    print("    # Include discard top and round for context")
    print("    discard_top = game_state.discard_pile[-1].rank if game_state.discard_pile else 'None'")
    print("    ")
    print("    return f'{known_cards_sorted}_{unknown_count}_{discard_top}_{game_state.round}'")
    print("```\n")

def calculate_theoretical_state_space():
    """Calculate the theoretical state space size"""
    print("=== THEORETICAL STATE SPACE CALCULATION ===\n")

    # Card ranks (suits don't matter in state representation)
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    num_ranks = len(ranks)

    print(f"Card ranks: {num_ranks} different ranks")
    print(f"Grid size: 4 cards per player")
    print(f"Max rounds: 4")

    # Calculate combinations for known cards
    # For each card position, we can have:
    # - Unknown card ('?')
    # - Any of the 13 ranks

    # But we need to consider that the state uses:
    # 1. Sorted list of known card ranks (order doesn't matter)
    # 2. Count of unknown cards
    # 3. Top discard card rank (or 'None')
    # 4. Round number

    # print("\nState components:")
    # print("1. Known cards (sorted list of ranks)")
    # print("2. Unknown card count (0-4)")
    # print("3. Discard pile top (13 ranks + 'None')")
    # print("4. Round number (1-4)")

    # For known cards: we can have 0-4 known cards
    # Each subset of ranks can appear in any combination
    total_known_combinations = 0

    for num_known in range(5):  # 0 to 4 known cards
        print(f"\n  {num_known} known cards:")

        if num_known == 0:
            combinations = 1  # Empty set
        else:
            # Combinations of ranks with repetition allowed
            # (multiset - same rank can appear multiple times)
            combinations = math.comb(num_ranks + num_known - 1, num_known)

        total_known_combinations += combinations
    #     print(f"    Combinations: {combinations:,}")

    # print(f"\nTotal known card combinations: {total_known_combinations:,}")

    # Discard pile possibilities
    discard_possibilities = num_ranks + 1  # 13 ranks + 'None'

    # Round possibilities
    round_possibilities = 4  # rounds 1-4

    # Total theoretical state space
    total_states = total_known_combinations * discard_possibilities * round_possibilities

    print(f"Discard possibilities: {discard_possibilities}")
    print(f"Round possibilities: {round_possibilities}")
    print(f"\nTheoretical total states: {total_states:,}")

    # Action space per state
    max_actions_per_state = 8  # 4 positions × 2 action types (take_discard, draw_deck)
    total_state_action_pairs = total_states * max_actions_per_state

    print(f"Max actions per state: {max_actions_per_state}")
    print(f"Theoretical state-action pairs: {total_state_action_pairs:,}")

    return total_states

def sample_actual_states():
    """Generate some actual states to see the representation in practice"""
    print("\n=== SAMPLE ACTUAL STATES ===\n")

    agent = QLearningAgent()
    states_seen = set()

    # Generate states from a few game scenarios
    for game_num in range(10):
        print(f"Game {game_num + 1} sample states:")

        game = GolfGame(num_players=2, agent_types=['random', 'qlearning'], q_agents=[None, agent])

        # Sample a few turns
        for turn in range(min(8, 20)):  # Max 8 turns or until game ends
            if game.is_game_over():
                break

            current_player = game.players[game.turn]

            # Only analyze Q-learning agent states (player 1)
            if game.turn == 1:
                state_key = agent.get_state_key(current_player, game)
                states_seen.add(state_key)

                # Show details for first few
                if len(states_seen) <= 5:
                    print(f"  Turn {turn}: {state_key}")

                    # Break down the state
                    parts = state_key.split('_')
                    known_cards = parts[0]
                    unknown_count = parts[1]
                    discard_top = parts[2]
                    round_num = parts[3]

                    print(f"    Known cards: {known_cards}")
                    print(f"    Unknown count: {unknown_count}")
                    print(f"    Discard top: {discard_top}")
                    print(f"    Round: {round_num}")

            # Make a simple move to advance game
            positions = [i for i, known in enumerate(current_player.known) if not known]
            if positions:
                if game.discard_pile:
                    action = {'type': 'take_discard', 'position': positions[0]}
                else:
                    action = {'type': 'draw_deck', 'position': positions[0], 'keep': True}
                try:
                    game.take_turn(action)
                except:
                    break
            else:
                break

        print()

    print(f"Unique states observed in samples: {len(states_seen)}")
    return states_seen

def run_quick_training_analysis():
    """Run a quick training session and analyze the Q-table growth"""
    print("=== QUICK TRAINING ANALYSIS ===\n")

    from simulation import run_simulations_with_training

    print("Running 100 games to analyze Q-table growth...")
    stats = run_simulations_with_training(
        num_games=100,
        agent_types=['random', 'qlearning'],
        verbose=False
    )

    # Get Q-table stats
    if 'q_learning_progress' in stats and stats['q_learning_progress']:
        final_progress = stats['q_learning_progress'][-1][1]
        if 'qlearning_1' in final_progress:
            states = final_progress['qlearning_1']['states']
            entries = final_progress['qlearning_1']['entries']

            print(f"After 100 games:")
            print(f"  Actual states discovered: {states:,}")
            print(f"  State-action pairs: {entries:,}")
            print(f"  Average actions per state: {entries/states:.1f}")

            # Performance
            q_score = stats['average_scores']['qlearning']
            random_score = stats['average_scores']['random']
            improvement = random_score - q_score

            print(f"\nPerformance:")
            print(f"  Q-learning score: {q_score:.2f}")
            print(f"  Random score: {random_score:.2f}")
            print(f"  Improvement: {improvement:+.2f}")

            return states, entries

    return 0, 0

def main():
    """Run complete state space analysis"""
    print("GOLF Q-LEARNING STATE SPACE ANALYSIS")
    print("=" * 50)

    # 1. Analyze representation
    analyze_state_representation()

    # 2. Calculate theoretical bounds
    theoretical_states = calculate_theoretical_state_space()

    # 3. Sample actual states
    sample_states = sample_actual_states()

    # 4. Quick training analysis
    actual_states, actual_entries = run_quick_training_analysis()

    # 5. Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Theoretical max states: {theoretical_states:,}")
    print(f"Actual states (100 games): {actual_states:,}")
    if actual_states > 0:
        print(f"State space utilization: {actual_states/theoretical_states:.1%}")
    print(f"Sample unique states: {len(sample_states)}")

    print(f"\nState space is {'MANAGEABLE' if actual_states < 10000 else 'LARGE'} for Q-learning")
    print("Location in code: agents.py, line ~264, get_state_key() method")

if __name__ == "__main__":
    main()