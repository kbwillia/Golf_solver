from collections import Counter

def get_deck_counts(game):
    """Return a dict of rank -> count for cards that could still be in the deck (unknown cards)."""
    # Start with a full deck (4 of each rank)
    full_deck_counts = {rank: 4 for rank in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']}

    # Subtract all known public cards
    for player in game.players:
        for i, card in enumerate(player.grid):
            if card and player.known[i]:  # Card exists and is public
                full_deck_counts[card.rank] -= 1

    # Subtract cards in the discard pile (they are public)
    if game.discard_pile:
        for card in game.discard_pile:
            full_deck_counts[card.rank] -= 1

    # Ensure no negative counts
    for rank in full_deck_counts:
        full_deck_counts[rank] = max(0, full_deck_counts[rank])

    return full_deck_counts


def get_private_deck_counts(game):
    """Return a dict of rank -> count for full_deck count - the players private cards."""
    # Start with a full deck (4 of each rank)
    full_deck_counts = {rank: 4 for rank in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']}

    # Subtract all known public cards
    for player in game.players:
        for i, card in enumerate(player.grid):
            if card and player.known[i]:  # Card exists and is public
                full_deck_counts[card.rank] -= 1

    # Subtract cards in the discard pile (they are public)
    if game.discard_pile:
        for card in game.discard_pile:
            full_deck_counts[card.rank] -= 1

    # Subtract human player's private cards (bottom 2 face-down cards they saw initially)
    human_player = game.players[0]  # Human is always player 0
    for i, card in enumerate(human_player.grid):
        if card and not human_player.known[i] and i >= 2:  # Bottom 2 cards (positions 2,3) that are not public
            full_deck_counts[card.rank] -= 1

    # Ensure no negative counts
    for rank in full_deck_counts:
        full_deck_counts[rank] = max(0, full_deck_counts[rank])

    return full_deck_counts

def prob_draw_lower_than_min_faceup(game):
    """For each player, probability that next card is lower than their lowest card (face-up or not)."""
    results = []
    deck = game.deck
    if not deck:
        return ['0.0%' for _ in game.players]
    for player in game.players:
        player_cards = [card for card in player.grid if card]
        if not player_cards:
            results.append('0.0%')
            continue
        min_val = min(card.score() for card in player_cards)
        lower = [card for card in deck if card.score() < min_val]
        prob = len(lower) / len(deck)
        results.append(f'{round(prob * 100, 1)}%')
    return results




def prob_draw_pair(game):
    """For each player, probability that next card matches any rank in their grid."""
    results = []
    deck = game.deck
    if not deck:
        return ['0.0%' for _ in game.players]
    for player in game.players:
        ranks_in_grid = set(card.rank for card in player.grid if card)
        matching = [card for card in deck if card.rank in ranks_in_grid]
        prob = len(matching) / len(deck)
        results.append(f'{round(prob * 100, 1)}%')
    return results


def prob_improve_hand(game):
    """
    For each player, return the probability that drawing the next card would improve their hand,
    either by:
    - Forming a pair with any card in their grid, or
    - Being lower than any card in their grid (for a potential swap).
    """
    results = []
    deck = game.deck
    if not deck:
        return ['0.0%' for _ in game.players]

    for player in game.players:
        player_cards = [card for card in player.grid if card]
        if not player_cards:
            results.append('0.0%')
            continue

        all_ranks = set(card.rank for card in player_cards)
        all_scores = [card.score() for card in player_cards]

        improving_cards = 0
        for card in deck:
            makes_pair = card.rank in all_ranks
            beats_known = any(card.score() < s for s in all_scores)
            if makes_pair or beats_known:
                improving_cards += 1

        prob = improving_cards / len(deck)
        results.append(f'{round(prob * 100, 1)}%')

    return results





def get_probabilities(game):
    """Return a dict of interesting probabilities/statistics for the current game state."""
    return {
        'deck_counts': get_deck_counts(game),
        'private_deck_counts': get_private_deck_counts(game),
        'prob_draw_lower_than_min_faceup': prob_draw_lower_than_min_faceup(game),
        'prob_draw_pair': prob_draw_pair(game),
        'prob_improve_hand': prob_improve_hand(game),
        'expected_value_draw_vs_discard': expected_value_draw_vs_discard(game),
    }

def expected_value_draw_vs_discard(game):
    """
    Calculate the expected value of drawing from deck vs taking the discard card.
    Returns a dict with expected values and recommendation for the human player.
    """
    if not game.deck or not game.discard_pile:
        return {
            'draw_expected_value': 0,
            'discard_expected_value': 0,
            'recommendation': 'No valid comparison possible',
            'draw_advantage': 0
        }

    human_player = game.players[0]
    discard_card = game.discard_pile[-1]

    # Get available positions for human player (face-down cards)
    # Include both top row (unknown) and bottom row (private but known to human)
    available_positions = []
    for i in range(4):
        if not human_player.known[i]:  # Not public yet
            available_positions.append(i)

    if not available_positions:
        return {
            'draw_expected_value': 0,
            'discard_expected_value': 0,
            'recommendation': 'No available positions',
            'draw_advantage': 0
        }

    # Calculate current hand score using game's calculate_score method
    current_score = game.calculate_score(human_player.grid)

    # Calculate expected value of taking the discard card
    # Try placing discard card in each available position and find best improvement
    best_discard_improvement = 0
    for pos in available_positions:
        if human_player.grid[pos]:  # If there's a card to replace
            # Create a test grid with discard card in this position
            test_grid = human_player.grid.copy()
            test_grid[pos] = discard_card
            test_score = game.calculate_score(test_grid)
            improvement = current_score - test_score  # Lower score is better
            best_discard_improvement = max(best_discard_improvement, improvement)

    discard_expected_value = best_discard_improvement

    # Calculate expected value of drawing from deck (two-step process)
    # Use private deck counts (human's perspective) for more accurate probabilities
    deck_counts = get_private_deck_counts(game)
    total_remaining_cards = sum(deck_counts.values())

    if total_remaining_cards == 0:
        # No cards left in deck
        draw_expected_value = 0
    else:
        draw_expected_value = 0

        for rank, count in deck_counts.items():
            if count > 0:
                # Create a card of this rank to get its score
                from models import Card
                drawn_card = Card(rank, '♠')  # Suit doesn't matter for score
                drawn_score = drawn_card.score()

                # For each possible drawn card, calculate the best two-step decision
                best_draw_improvement = 0

                # Step 1: Evaluate keeping the drawn card
                for pos in available_positions:
                    if human_player.grid[pos]:  # If there's a card to replace
                        # Create a test grid with drawn card in this position
                        test_grid = human_player.grid.copy()
                        test_grid[pos] = drawn_card
                        test_score = game.calculate_score(test_grid)
                        improvement = current_score - test_score  # Lower score is better
                        best_draw_improvement = max(best_draw_improvement, improvement)

                # Step 2: Evaluate discarding the drawn card and flipping one of your own
                # Find the best card to flip (the one that improves your hand most)
                best_flip_improvement = 0
                for flip_pos in available_positions:
                    if human_player.grid[flip_pos]:  # If there's a card to flip
                        # When you flip a card, you're revealing information
                        # This can be strategically valuable even if it doesn't change your score
                        # For now, we'll give a small strategic bonus for revealing cards
                        # (this could be refined based on game theory analysis)

                        # The card stays the same but becomes public (known)
                        # For immediate scoring, no change, but strategic value exists
                        # We'll give a small bonus for the strategic value of revealing information
                        strategic_bonus = 0.1  # Small bonus for revealing information
                        flip_improvement = strategic_bonus
                        best_flip_improvement = max(best_flip_improvement, flip_improvement)

                # Choose the better option: keep drawn card or discard and flip
                best_improvement = max(best_draw_improvement, best_flip_improvement)

                # Weight by probability of drawing this card
                probability = count / total_remaining_cards
                draw_expected_value += best_improvement * probability

    # Calculate the advantage of drawing over taking discard
    draw_advantage = draw_expected_value - discard_expected_value

    # Generate recommendation
    if draw_advantage > 0.5:
        recommendation = f"Draw from deck (expected +{draw_advantage:.1f} advantage)"
    elif draw_advantage < -0.5:
        recommendation = f"Take discard (expected +{-draw_advantage:.1f} advantage)"
    else:
        recommendation = "Either action is similar (draw slightly preferred)"

    return {
        'draw_expected_value': round(draw_expected_value, 2),
        'discard_expected_value': round(discard_expected_value, 2),
        'recommendation': recommendation,
        'draw_advantage': round(draw_advantage, 2),
        'discard_card': f"{discard_card.rank}{discard_card.suit}",
        'discard_score': discard_card.score(),
        'current_hand_score': current_score
    }

