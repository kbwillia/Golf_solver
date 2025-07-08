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
        'average_deck_score': round(average_score_of_deck(game), 2) if game.deck else 0,
    }

def expected_value_draw_vs_discard(game):
    """
    Calculate the expected value (EV) of drawing from the deck vs taking the discard card for the human player.

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

    human_player = game.players[0]
    discard_card = game.discard_pile[-1]

    # Get available positions for human player (face-down cards)
    available_positions = [i for i in range(4) if not human_player.known[i]]

    if not available_positions:
        return {
            'draw_expected_value': 0,
            'discard_expected_value': 0,
            'recommendation': 'No available positions',
            'draw_advantage': 0
        }

    # Calculate current hand score using game's calculate_score method
    current_score = game.calculate_score(human_player.grid)

    # --- Discard EV ---
    # Try placing discard card in each available position and find best (most negative) change
    best_discard_ev = 0  # 0 means no change; negative is good
    for pos in available_positions:
        if human_player.grid[pos]:  # If there's a card to replace
            test_grid = human_player.grid.copy()
            test_grid[pos] = discard_card
            test_score = game.calculate_score(test_grid)
            ev = test_score - current_score  # Negative = score goes down (good)
            best_discard_ev = min(best_discard_ev, ev)  # Most negative (best improvement)

    discard_expected_value = best_discard_ev

    # --- Draw EV ---
    # For each possible card you could draw, calculate the best (most negative) change (swap or flip), weighted by probability
    deck_counts = get_private_deck_counts(game)
    total_remaining_cards = sum(deck_counts.values())

    if total_remaining_cards == 0:
        draw_expected_value = 0
    else:
        draw_expected_value = 0
        for rank, count in deck_counts.items():
            if count > 0:
                from models import Card
                drawn_card = Card(rank, '♠')  # Suit doesn't matter for score

                # Step 1: Evaluate keeping the drawn card (swap into each available position)
                best_draw_ev = 0  # 0 means no change; negative is good
                for pos in available_positions:
                    if human_player.grid[pos]:
                        test_grid = human_player.grid.copy()
                        test_grid[pos] = drawn_card
                        test_score = game.calculate_score(test_grid)
                        ev = test_score - current_score  # Negative = score goes down (good)
                        best_draw_ev = min(best_draw_ev, ev)

                # Step 2: Evaluate discarding the drawn card and flipping one of your own
                # (Small bonus for revealing info, not for score change)
                best_flip_ev = 0
                for flip_pos in available_positions:
                    if human_player.grid[flip_pos]:
                        strategic_bonus = -0.1  # Small negative bonus for revealing information (good)
                        flip_ev = strategic_bonus
                        best_flip_ev = min(best_flip_ev, flip_ev)

                # Choose the better option: keep drawn card or discard and flip
                best_ev = min(best_draw_ev, best_flip_ev)

                # Weight by probability of drawing this card
                probability = count / total_remaining_cards
                draw_expected_value += best_ev * probability

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

def which_card_to_swap_for_discard(game):
    """if the player wants to swap the discard card, which card should they swap it with?"""
    # get the discard card
    discard_card = game.discard_pile[-1]
    # get the human player
    human_player = game.players[0]
    # get the available positions for the human player
    available_positions = [i for i, known in enumerate(human_player.known) if not known]
    # get the cards in the human player's grid
    cards_in_grid = [card for card in human_player.grid if card]
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

