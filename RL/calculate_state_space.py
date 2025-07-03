#!/usr/bin/env python3
"""
Simple mathematical calculation of Q-learning state space for Golf card game

This calculates the theoretical state space based on the state representation
used in agents.py get_state_key() method.
"""

import math
from itertools import combinations_with_replacement

def calculate_golf_state_space():
    """Calculate the exact state space size mathematically"""

    print("GOLF Q-LEARNING STATE SPACE CALCULATION")
    print("=" * 50)

    # State representation from agents.py line ~264:
    # return f"{known_cards_sorted}_{unknown_count}_{discard_top}_{game_state.round}"

    print("\nState representation components:")
    print("1. known_cards_sorted: sorted list of known card ranks")
    print("2. unknown_count: number of unknown cards (0-4)")
    print("3. discard_top: top card of discard pile (13 ranks + 'None')")
    print("4. round: game round number (1-4)")

    # Constants
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    num_ranks = len(ranks)  # 13
    grid_size = 4
    max_rounds = 4

    print(f"\nConstants:")
    print(f"  Card ranks: {num_ranks}")
    print(f"  Grid size: {grid_size} cards")
    print(f"  Max rounds: {max_rounds}")

    # Calculate known card combinations
    # For each possible number of known cards (0-4), calculate combinations
    total_known_combinations = 0

    print(f"\nKnown card combinations:")
    for num_known in range(grid_size + 1):  # 0 to 4 known cards
        if num_known == 0:
            # No known cards - empty list
            combinations = 1
        else:
            # Multiset: combinations with repetition
            # e.g., ['2', '2', '7'] is different from ['2', '7']
            combinations = math.comb(num_ranks + num_known - 1, num_known)

        total_known_combinations += combinations
        print(f"  {num_known} known cards: {combinations:,} combinations")

    print(f"  Total known combinations: {total_known_combinations:,}")

    # Discard pile top card possibilities
    discard_possibilities = num_ranks + 1  # 13 ranks + 'None'
    print(f"\nDiscard pile possibilities: {discard_possibilities}")

    # Round possibilities
    round_possibilities = max_rounds
    print(f"Round possibilities: {round_possibilities}")

    # Total state space
    total_states = total_known_combinations * discard_possibilities * round_possibilities

    print(f"\nTOTAL STATE SPACE: {total_states:,}")

    # Action space calculation
    max_actions_per_state = 8  # 4 positions × 2 actions (take_discard, draw_deck)
    # But in practice, fewer actions available depending on known cards
    avg_actions_per_state = 4  # Rough estimate

    max_state_action_pairs = total_states * max_actions_per_state
    avg_state_action_pairs = total_states * avg_actions_per_state

    print(f"\nAction space:")
    print(f"  Max actions per state: {max_actions_per_state}")
    print(f"  Avg actions per state: ~{avg_actions_per_state}")
    print(f"  Max state-action pairs: {max_state_action_pairs:,}")
    print(f"  Avg state-action pairs: ~{avg_state_action_pairs:,}")

    # Memory estimates (rough)
    bytes_per_float = 8  # Q-value storage
    bytes_per_state_key = 50  # String key storage estimate

    memory_mb = (avg_state_action_pairs * bytes_per_float + total_states * bytes_per_state_key) / (1024 * 1024)

    print(f"\nMemory estimate:")
    print(f"  Q-table storage: ~{memory_mb:.1f} MB")

    # Assessment
    print(f"\nASSESSMENT:")
    if total_states < 1000:
        assessment = "VERY SMALL - trivial for Q-learning"
    elif total_states < 10000:
        assessment = "SMALL - excellent for Q-learning"
    elif total_states < 100000:
        assessment = "MEDIUM - good for Q-learning"
    elif total_states < 1000000:
        assessment = "LARGE - challenging but feasible"
    else:
        assessment = "VERY LARGE - may need approximation methods"

    print(f"  State space size: {assessment}")
    print(f"  Memory requirements: {'Minimal' if memory_mb < 100 else 'Moderate' if memory_mb < 1000 else 'High'}")

    return total_states

def show_example_states():
    """Show some example state representations"""
    print(f"\nEXAMPLE STATES:")
    print("Format: [known_cards]_unknown_count_discard_top_round")
    print("  []_4_None_1        - Start of game, no known cards")
    print("  ['2']_3_7_1        - Know one '2', discard top is '7'")
    print("  ['2','7']_2_K_2    - Know '2' and '7', discard top 'K', round 2")
    print("  ['A','A','3']_1_Q_3 - Know two Aces and a 3, round 3")
    print("  ['2','5','7','K']_0_A_4 - All cards known, final round")

def main():
    total_states = calculate_golf_state_space()
    show_example_states()

    print(f"\nCode location: agents.py, get_state_key() method (around line 264)")
    print(f"This calculation is exact based on the current state representation.")

if __name__ == "__main__":
    main()