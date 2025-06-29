from collections import Counter

def get_deck_counts(game):
    """Return a dict of rank -> count for all cards left in the deck."""
    return dict(Counter(card.rank for card in game.deck))

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
        'prob_draw_lower_than_min_faceup': prob_draw_lower_than_min_faceup(game),
        'prob_draw_pair': prob_draw_pair(game),
        'prob_improve_hand': prob_improve_hand(game),
    }

