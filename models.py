import itertools
import random
from collections import defaultdict

class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}{self.suit}"

    def __repr__(self):
        return self.__str__()

    def score(self):
        if self.rank == 'A':
            return 1
        elif self.rank == 'J':
            return 0
        elif self.rank in ['Q', 'K']:
            return 10
        else:
            return int(self.rank)

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return hash((self.rank, self.suit))

class Player:
    def __init__(self, name, agent_type="random"):
        self.name = name
        self.agent_type = agent_type
        self.grid = [None] * 4  # 2x2 grid: [TL, TR, BL, BR]
        self.known = [False, False, True, True]  # Bottom two cards privately visible to this player
        # Memory for tracking seen cards
        self.memory = {
            'all_seen_cards': [],
            'discard_history': [],
            'cards_per_rank': {rank: 0 for rank in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']}
        }

    def reveal_all(self):
        self.known = [True] * 4

    def __str__(self):
        def show(i):
            return str(self.grid[i]) if self.known[i] else '?'
        return f"[ {show(0)} | {show(1)} ]\n[ {show(2)} | {show(3)} ]"

    def update_memory(self, new_cards):
        """Update memory with newly seen cards"""
        for card in new_cards:
            if card and card not in self.memory['all_seen_cards']:
                self.memory['all_seen_cards'].append(card)
                self.memory['cards_per_rank'][card.rank] += 1

    def add_to_discard_memory(self, card):
        """Add card to discard pile memory"""
        if card:
            self.memory['discard_history'].append(card)
            self.update_memory([card])

    def get_deck_probabilities(self, additional_seen_cards=None):
        """Calculate probability distribution of remaining cards in deck"""
        rank_counts = self.memory['cards_per_rank'].copy()

        if additional_seen_cards:
            for card in additional_seen_cards:
                if card:
                    rank_counts[card.rank] += 1

        remaining_cards = {}
        for rank in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']:
            remaining_cards[rank] = max(0, 4 - rank_counts[rank])

        total_remaining = sum(remaining_cards.values())
        probabilities = {}
        for rank in ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']:
            probabilities[rank] = remaining_cards[rank] / total_remaining if total_remaining > 0 else 0

        return probabilities, total_remaining

    def expected_score_for_unknown_position(self, probabilities):
        """Calculate expected score for an unknown card position"""
        expected = 0
        for rank, prob in probabilities.items():
            card_score = Card(rank, '♠').score()
            expected += prob * card_score
        return expected