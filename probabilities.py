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

def prob_draw_lower_than_min_faceup(game, player=None):
    """For a specific player, probability that next card is lower than their lowest visible card."""
    deck = game.deck
    if not deck:
        return '0.0%'

    # Use specified player or default to first player for backwards compatibility
    target_player = player if player is not None else game.players[0]

    # For human player, include both known (public) and privately_visible cards
    # For AI players, only include known (public) cards
    if target_player.agent_type == 'human':
        # Include cards that are either publicly known or privately visible
        visible_cards = [card for i, card in enumerate(target_player.grid)
                       if card and (target_player.known[i] or target_player.privately_visible[i])]
    else:
        # For AI players, only include publicly known cards
        visible_cards = [card for i, card in enumerate(target_player.grid)
                       if card and target_player.known[i]]

    if not visible_cards:
        return '0.0%'

    min_val = min(card.score() for card in visible_cards)
    lower = [card for card in deck if card.score() < min_val]
    prob = len(lower) / len(deck)
    return f'{round(prob * 100, 1)}%'




def prob_draw_pair(game, player=None):
    """For a specific player, probability that next card matches any rank in their visible grid."""
    deck = game.deck
    if not deck:
        return '0.0%'

    # Use specified player or default to first player for backwards compatibility
    target_player = player if player is not None else game.players[0]

    # For human player, include both known (public) and privately_visible cards
    # For AI players, only include known (public) cards
    if target_player.agent_type == 'human':
        # Include cards that are either publicly known or privately visible
        visible_cards = [card for i, card in enumerate(target_player.grid)
                       if card and (target_player.known[i] or target_player.privately_visible[i])]
    else:
        # For AI players, only include publicly known cards
        visible_cards = [card for i, card in enumerate(target_player.grid)
                       if card and target_player.known[i]]

    ranks_in_grid = set(card.rank for card in visible_cards)
    matching = [card for card in deck if card.rank in ranks_in_grid]
    prob = len(matching) / len(deck)
    return f'{round(prob * 100, 1)}%'


def prob_improve_hand(game, player=None):
    """
    For a specific player, return the probability that drawing the next card would improve their hand,
    either by:
    - Forming a pair with any card in their visible grid, or
    - Being lower than any card in their visible grid (for a potential swap).
    """
    deck = game.deck
    if not deck:
        return '0.0%'

    # Use specified player or default to first player for backwards compatibility
    target_player = player if player is not None else game.players[0]

    # For human player, include both known (public) and privately_visible cards
    # For AI players, only include known (public) cards
    if target_player.agent_type == 'human':
        # Include cards that are either publicly known or privately visible
        visible_cards = [card for i, card in enumerate(target_player.grid)
                       if card and (target_player.known[i] or target_player.privately_visible[i])]
    else:
        # For AI players, only include publicly known cards
        visible_cards = [card for i, card in enumerate(target_player.grid)
                       if card and target_player.known[i]]

    if not visible_cards:
        return '0.0%'

    all_ranks = set(card.rank for card in visible_cards)
    all_scores = [card.score() for card in visible_cards]

    improving_cards = 0
    for card in deck:
        makes_pair = card.rank in all_ranks
        beats_known = any(card.score() < s for s in all_scores)
        if makes_pair or beats_known:
            improving_cards += 1

    prob = improving_cards / len(deck)
    return f'{round(prob * 100, 1)}%'



def get_probabilities(game):
    """Return a dict of interesting probabilities/statistics for the current game state."""
    # Calculate probabilities for each player to maintain backwards compatibility
    prob_draw_lower_results = []
    prob_draw_pair_results = []
    prob_improve_hand_results = []

    for player in game.players:
        prob_draw_lower_results.append(prob_draw_lower_than_min_faceup(game, player))
        prob_draw_pair_results.append(prob_draw_pair(game, player))
        prob_improve_hand_results.append(prob_improve_hand(game, player))

    return {
        'deck_counts': get_deck_counts(game),
        'private_deck_counts': get_private_deck_counts(game),
        'prob_draw_lower_than_min_faceup': prob_draw_lower_results,
        'prob_draw_pair': prob_draw_pair_results,
        'prob_improve_hand': prob_improve_hand_results,
        'expected_value_draw_vs_discard': expected_value_draw_vs_discard(game),
        'average_deck_score': round(average_score_of_deck(game), 2) if game.deck else 0,
    }

def expected_score_blind(grid, known, rank_probabilities, privately_visible=None):
    """
    Compute the expected score of a grid, using:
      - True values for known cards
      - Probability-weighted expected values for unknown cards
      - For pairs: count a pair if both cards are known or (for human) privately visible
    """
    from models import Card
    scores = []
    ranks = []
    for i in range(4):
        if known[i] and grid[i]:
            scores.append(grid[i].score())
            ranks.append(grid[i].rank)
        elif privately_visible is not None and privately_visible[i] and grid[i]:
            scores.append(grid[i].score())
            ranks.append(grid[i].rank)
        else:
            # Use expected value for unknown
            expected = sum(Card(rank, '♠').score() * prob for rank, prob in rank_probabilities.items())
            scores.append(expected)
            # For pairing, treat as unknown (None)
            ranks.append(None)
    total_score = sum(scores)
    # Only count pairs if both cards are known or privately visible
    used = set()
    for pos1 in range(4):
        for pos2 in range(pos1+1, 4):
            if (ranks[pos1] is not None and ranks[pos2] is not None and
                ranks[pos1] == ranks[pos2] and pos1 not in used and pos2 not in used):
                # For human, check privately_visible as well
                if (known[pos1] or (privately_visible is not None and privately_visible[pos1])) and \
                   (known[pos2] or (privately_visible is not None and privately_visible[pos2])):
                    # Subtract both scores (they become zero)
                    total_score -= (scores[pos1] + scores[pos2])
                    used.add(pos1)
                    used.add(pos2)
    return total_score

def expected_value_draw_vs_discard(game, player=None):
    """
    Calculate the expected value (EV) of drawing from the deck vs taking the discard card for the specified player.
    If no player is specified, defaults to game.players[0] (for backwards compatibility).

    In Golf, **lower scores are better**. Here, EV is defined as the **expected change in score**:
        - A **negative EV** means your score is expected to go down (good).
        - A **positive EV** means your score is expected to go up (bad).

    The function returns a dict with:
        - draw_expected_value: Expected change in score if you draw from the deck (averaged over all possible draws)
        - discard_expected_value: Best possible change in score if you take the discard card
        - recommendation: Which action is better (draw or discard)
        - draw_advantage: Difference between draw_expected_value and discard_expected_value (negative = draw is better)

    Calculation details:
    1. **Discard EV**: For each available position in your grid, try swapping in the discard card and calculate the change (test_score - current_score). The best (most negative) change is used as the discard EV.
    2. **Draw EV**: For each possible card you could draw, calculate the best (most negative) change (swap or flip), weighted by probability
    3. **Interpretation**: Negative EV means a drop in your score (good in golf).
    """
    if not game.deck or not game.discard_pile:
        return {
            'draw_expected_value': 0,
            'discard_expected_value': 0,
            'recommendation': 'No valid comparison possible',
            'draw_advantage': 0
        }

    # Use specified player or default to first player for backwards compatibility
    target_player = player if player is not None else game.players[0]
    discard_card = game.discard_pile[-1]

    # Get available positions for target player (face-down cards)
    available_positions = [i for i in range(4) if not target_player.known[i]]

    if not available_positions:
        return {
            'draw_expected_value': 0,
            'discard_expected_value': 0,
            'recommendation': 'No available positions',
            'draw_advantage': 0
        }

    # Get probabilities for unknown cards
    private_deck_counts = get_private_deck_counts(game)
    total_private = sum(private_deck_counts.values())
    rank_probabilities = {rank: count / total_private if total_private > 0 else 0 for rank, count in private_deck_counts.items()}

    # Calculate current hand score using expected_score_blind
    current_score = expected_score_blind(target_player.grid, target_player.known, rank_probabilities, getattr(target_player, 'privately_visible', None))

    # --- Discard EV ---
    # Try placing discard card in each available position and find best (most negative) change
    best_discard_ev = 0
    best_discard_position = None
    from models import Card

    for pos in available_positions:
        # For human, treat privately_visible as known
        is_known = target_player.known[pos]
        is_private = hasattr(target_player, 'privately_visible') and target_player.privately_visible[pos]
        if (is_known or is_private) and target_player.grid[pos]:
            current_card_score = target_player.grid[pos].score()
        else:
            # If unknown, use expected score
            current_card_score = sum(Card(rank, '♠').score() * prob for rank, prob in rank_probabilities.items())
        # Simulate swapping in the discard card
        test_grid = target_player.grid.copy()
        test_grid[pos] = discard_card
        test_known = target_player.known.copy()
        test_known[pos] = True  # After swap, this card is known
        # For human, update privately_visible as well
        test_privately_visible = getattr(target_player, 'privately_visible', None)
        if test_privately_visible is not None:
            test_privately_visible = test_privately_visible.copy()
            test_privately_visible[pos] = True
        test_score = expected_score_blind(test_grid, test_known, rank_probabilities, test_privately_visible)
        ev = test_score - current_score
        if ev < best_discard_ev or best_discard_position is None:
            best_discard_ev = ev
            best_discard_position = pos

    discard_expected_value = best_discard_ev

    # --- Draw EV ---
    # For each possible card you could draw, calculate the best (most negative) change (swap or flip), weighted by probability
    deck_counts = get_private_deck_counts(game)
    total_remaining_cards = sum(deck_counts.values())

    if total_remaining_cards == 0:
        draw_expected_value = 0
        best_draw_position = None
        best_flip_position = None
        best_action_type = "keep"  # "keep" or "flip"
    else:
        draw_expected_value = 0
        best_overall_ev = float('inf')
        best_draw_position = None
        best_flip_position = None
        best_action_type = "keep"

        for rank, count in deck_counts.items():
            if count > 0:
                drawn_card = Card(rank, '♠')  # Suit doesn't matter for score

                # Step 1: Evaluate keeping the drawn card (swap into each available position)
                best_draw_ev = float('inf')
                current_best_draw_position = None
                for pos in available_positions:
                    # If the card is known, use its actual value
                    if target_player.known[pos] and target_player.grid[pos]:
                        current_card_score = target_player.grid[pos].score()
                    else:
                        # If unknown, use expected score
                        current_card_score = sum(Card(r, '♠').score() * prob for r, prob in rank_probabilities.items())
                    test_grid = target_player.grid.copy()
                    test_grid[pos] = drawn_card
                    test_known = target_player.known.copy()
                    test_known[pos] = True  # After swap, this card is known
                    test_score = expected_score_blind(test_grid, test_known, rank_probabilities, getattr(target_player, 'privately_visible', None))
                    ev = test_score - current_score
                    if ev < best_draw_ev:
                        best_draw_ev = ev
                        current_best_draw_position = pos

                # Step 2: Evaluate discarding the drawn card and flipping one of your own
                # Calculate actual expected score change when flipping each position
                best_flip_ev = float('inf')
                current_best_flip_position = None
                for flip_pos in available_positions:
                    if target_player.grid[flip_pos]:
                        # Calculate expected score change when this card is revealed
                        test_known = target_player.known.copy()
                        test_known[flip_pos] = True  # This card becomes known
                        test_score = expected_score_blind(target_player.grid, test_known, rank_probabilities, getattr(target_player, 'privately_visible', None))
                        ev = test_score - current_score
                        if ev < best_flip_ev:
                            best_flip_ev = ev
                            current_best_flip_position = flip_pos

                # Choose the better option: keep drawn card or discard and flip
                if best_draw_ev < best_flip_ev:
                    current_best_ev = best_draw_ev
                    current_action_type = "keep"
                    current_best_position = current_best_draw_position
                else:
                    current_best_ev = best_flip_ev
                    current_action_type = "flip"
                    current_best_position = current_best_flip_position

                # Track the overall best action across all possible draws
                if current_best_ev < best_overall_ev:
                    best_overall_ev = current_best_ev
                    best_action_type = current_action_type
                    if current_action_type == "keep":
                        best_draw_position = current_best_position
                        best_flip_position = None
                    else:
                        best_draw_position = None
                        best_flip_position = current_best_position

                # Weight by probability of drawing this card
                probability = count / total_remaining_cards
                draw_expected_value += current_best_ev * probability

    # --- Draw Advantage ---
    # Difference between draw and discard EVs (negative = draw is better)
    draw_advantage = draw_expected_value - discard_expected_value

    # --- Recommendation ---
    # If draw_advantage is negative, drawing is better; if positive, discard is better
    if draw_advantage < -0.5:
        recommendation = "Draw from deck"
    elif draw_advantage > 0.5:
        recommendation = "Take discard"
    else:
        # Dynamic: whichever EV is lower (more negative) is slightly preferred
        if draw_expected_value < discard_expected_value:
            recommendation = "Either action is similar (draw slightly preferred)"
        elif discard_expected_value < draw_expected_value:
            recommendation = "Either action is similar (discard slightly preferred)"
        else:
            recommendation = "Either action is similar"

    return {
        'draw_expected_value': round(draw_expected_value, 2),
        'discard_expected_value': round(discard_expected_value, 2),
        'recommendation': recommendation,
        'draw_advantage': round(draw_advantage, 2),
        'discard_card': f"{discard_card.rank}{discard_card.suit}",
        'discard_score': discard_card.score(),
        'current_hand_score': current_score,
        'best_discard_position': best_discard_position,
        'best_draw_position': best_draw_position,
        'best_flip_position': best_flip_position,
        'best_action_type': best_action_type,  # "keep" or "flip"
    }

def which_card_to_swap_for_discard(game, player=None):
    """if the player wants to swap the discard card, which card should they swap it with?"""
    # get the discard card
    discard_card = game.discard_pile[-1]
    # get the target player (or default to first player for backwards compatibility)
    target_player = player if player is not None else game.players[0]
    # get the available positions for the target player
    available_positions = [i for i, known in enumerate(target_player.known) if not known]
    # get the cards in the target player's grid
    cards_in_grid = [card for card in target_player.grid if card]
    # get the private deck counts
    private_deck_counts = get_private_deck_counts(game)

    # get the expected value of drawing from deck vs taking the discard card
    #loop through each card and use probabilities of the private deck counts to get the expected value of swapping the discard card with that card
    for card in cards_in_grid:
        # get the probability of the card being in the private deck
        probability = private_deck_counts[card.rank] / sum(private_deck_counts.values())
        # get the expected value of swapping the discard card with that card
        expected_value = probability * card.score()
        # add the expected value to the list
        expected_values.append(expected_value)
    # return the card with the highest expected value
    return cards_in_grid[expected_values.index(max(expected_values))]

def which_card_to_swap_for_deck(game):
    """if the player wants to swap the deck card, which card should they swap it with?"""
    # get the deck card
    deck_card = game.deck[-1]
    # get the human player
    human_player = game.players[0]
    # get the available positions for the human player
    available_positions = [i for i, known in enumerate(human_player.known) if not known]
    # get the cards in the human player's grid
    pass

def average_score_of_deck(game):
    """average score of the deck"""
    # get the deck
    deck = game.deck
    # get the average score of the deck
    return sum(card.score() for card in deck) / len(deck)

