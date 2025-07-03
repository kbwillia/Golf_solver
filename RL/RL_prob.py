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
