from collections import Counter

def get_deck_counts(game):
    """Return a dict of rank -> count for all cards left in the deck."""
    return dict(Counter(card.rank for card in game.deck))

def prob_draw_lower_than_min_faceup(game):
    """For each player, probability that next card is lower than their lowest face-up card."""
    results = []
    deck = game.deck
    if not deck:
        return [0.0 for _ in game.players]
    for player in game.players:
        # Find all face-up cards (public or privately visible to player)
        faceup = [card for i, card in enumerate(player.grid) if player.known[i] and card]
        if not faceup:
            results.append(None)
            continue
        min_val = min(card.score() for card in faceup)
        lower = [card for card in deck if card.score() < min_val]
        prob = len(lower) / len(deck)
        results.append(round(prob, 3))
    return results

def prob_draw_pair(game):
    """For each player, probability that next card matches any rank in their grid."""
    results = []
    deck = game.deck
    if not deck:
        return [0.0 for _ in game.players]
    for player in game.players:
        ranks_in_grid = set(card.rank for card in player.grid if card)
        matching = [card for card in deck if card.rank in ranks_in_grid]
        prob = len(matching) / len(deck)
        results.append(round(prob, 3))
    return results

def get_probabilities(game):
    """Return a dict of interesting probabilities/statistics for the current game state."""
    return {
        'deck_counts': get_deck_counts(game),
        'prob_draw_lower_than_min_faceup': prob_draw_lower_than_min_faceup(game),
        'prob_draw_pair': prob_draw_pair(game),
    }
