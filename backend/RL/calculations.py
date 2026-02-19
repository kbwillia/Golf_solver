def calculate_theoretical_state_space():
    """
    Calculate the theoretical number of states and state-action pairs for the Golf game.

    Returns:
        dict: Dictionary containing theoretical counts and breakdown
    """
    print("="*70)
    print("THEORETICAL STATE SPACE CALCULATION")
    print("="*70)

    # Game parameters
    num_positions = 4  # 2x2 grid
    num_cards = 52     # Standard deck
    num_rounds = 4     # 4 rounds per game

    # State components:
    # 1. Public cards (flipped cards) - 0 to 4 cards
    # 2. Private cards (known but not flipped) - 0 to 4 cards
    # 3. Discard top card - 1 card (or None if no discard pile)
    # 4. Round number - 1 to 4
    # 5. Draw advantage (EV) - continuous value, but we'll discretize

    print("State Space Components:")
    print(f"  • Grid positions: {num_positions}")
    print(f"  • Total cards in deck: {num_cards}")
    print(f"  • Rounds per game: {num_rounds}")

    # Calculate state space size
    total_states = 0

    # For each possible number of public cards (0 to 4)
    for num_public in range(5):  # 0, 1, 2, 3, 4
        num_private = num_positions - num_public

        # Number of ways to choose public cards from 52 cards
        if num_public == 0:
            public_combinations = 1
        else:
            # C(52, num_public) * num_public! (order matters for positions)
            public_combinations = 1
            for i in range(num_public):
                public_combinations *= (52 - i)

        # Number of ways to choose private cards from remaining cards
        if num_private == 0:
            private_combinations = 1
        else:
            remaining_cards = 52 - num_public
            private_combinations = 1
            for i in range(num_private):
                private_combinations *= (remaining_cards - i)

        # Discard top card possibilities
        # If no discard pile, it's None
        # If discard pile exists, it's one of the remaining cards
        discard_possibilities = 1  # None
        if num_public + num_private < 52:  # Some cards still in deck
            discard_possibilities += (52 - num_public - num_private)

        # Round possibilities (1 to 4)
        round_possibilities = num_rounds

        # Draw advantage discretization
        # We'll assume a reasonable discretization (e.g., -10 to +10 in 0.5 steps)
        ev_possibilities = 41  # -10, -9.5, -9, ..., 9.5, 10

        # Total states for this public/private combination
        states_for_combination = (public_combinations *
                                private_combinations *
                                discard_possibilities *
                                round_possibilities *
                                ev_possibilities)

        total_states += states_for_combination

        print(f"  • {num_public} public, {num_private} private: {states_for_combination:,} states")

    print(f"\nTotal theoretical states: {total_states:,}")

    # Action space calculation
    # For each state, possible actions depend on:
    # 1. Number of available positions (unflipped cards)
    # 2. Whether discard pile exists
    # 3. Whether deck has cards

    print(f"\nAction Space Analysis:")



        # Actions per available position:
        # - take_discard (if discard pile exists)
        # - draw_deck_keep (if deck has cards)
        # - draw_deck_discard_flip (if deck has cards and there are other positions to flip)

        actions_per_position = 0
        if available_positions > 0:
            # Always can draw from deck if it has cards
            actions_per_position += 2  # draw_keep + draw_discard_flip
            # Can take from discard if discard pile exists
            actions_per_position += 1  # take_discard

        total_actions_for_combination = available_positions * actions_per_position

        # Estimate number of states with this combination
        # (This is a rough estimate - actual number depends on card combinations)
        estimated_states = total_states // 5  # Rough estimate

        total_actions += total_actions_for_combination * estimated_states
        state_count += estimated_states

        print(f"  • {num_public} public cards: {available_positions} positions, {actions_per_position} actions/position")

    avg_actions_per_state = total_actions / state_count if state_count > 0 else 0
    total_state_action_pairs = total_states * avg_actions_per_state

    print(f"\nAverage actions per state: {avg_actions_per_state:.1f}")
    print(f"Total theoretical state-action pairs: {total_state_action_pairs:,.0f}")

    # Practical considerations
    print(f"\nPractical Considerations:")
    print(f"  • Many states are unreachable due to game rules")
    print(f"  • Card combinations are constrained by deck composition")
    print(f"  • Some state transitions are impossible")
    print(f"  • Actual reachable states likely much smaller")

    # Estimate reachable states (rough guess: 1-5% of theoretical)
    estimated_reachable_states = total_states * 0.02  # 2% estimate
    estimated_reachable_pairs = total_state_action_pairs * 0.02

    print(f"\nEstimated reachable states: {estimated_reachable_states:,.0f}")
    print(f"Estimated reachable state-action pairs: {estimated_reachable_pairs:,.0f}")

    return {
        'total_theoretical_states': total_states,
        'total_theoretical_pairs': total_state_action_pairs,
        'avg_actions_per_state': avg_actions_per_state,
        'estimated_reachable_states': estimated_reachable_states,
        'estimated_reachable_pairs': estimated_reachable_pairs,
        'state_space_utilization': 0.02  # Estimated percentage
    }