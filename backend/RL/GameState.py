class GameState:
    """Encapsulates the state representation for the Q-table and agent logic, using a dictionary for readability."""
    def __init__(self, player, game_state):
        # Known cards (ranks only, not suits)
        known_cards = [card.rank if player.known[i] and card else '?' for i, card in enumerate(player.grid)]
        known_cards_sorted = tuple(sorted([c for c in known_cards if c != '?']))
        unknown_count = known_cards.count('?')
        discard_top = game_state.discard_pile[-1].rank if game_state.discard_pile else 'None'
        round_num = game_state.round
        self.state_dict = {
            'known_cards_sorted': known_cards_sorted,
            'unknown_count': unknown_count,
            'discard_top': discard_top,
            'round': round_num
        }

    # Allow dictionary-like access: gs['discard_top']
    def __getitem__(self, key):
        return self.state_dict[key]

    # Allow setting values like a dictionary: gs['round'] = 2
    def __setitem__(self, key, value):
        self.state_dict[key] = value

    def as_dict(self):
        return dict(self.state_dict)

    # Allow GameState objects to be used as keys in dicts/sets (e.g., Q-table)
    def __hash__(self):
        # Use a tuple of the dict values for hashing
        return hash((self.state_dict['known_cards_sorted'],
                     self.state_dict['unknown_count'],
                     self.state_dict['discard_top'],
                     self.state_dict['round']))

    # Allow comparison between GameState objects (e.g., for equality in Q-table)
    def __eq__(self, other):
        if not isinstance(other, GameState):
            return False
        return self.state_dict == other.state_dict

    # String representation for debugging and Q-table keys
    def __str__(self):
        """
        State string format:
        (known_cards_sorted)_(unknown_count)_(discard_top)_(round)
        Example: ('7', '7', 'J')_1_A_4
        - known_cards_sorted: tuple of known card ranks (sorted, positions not tracked)
        - unknown_count: number of unknown cards in the grid
        - discard_top: rank of the top card on the discard pile
        - round: current round number
        """
        d = self.state_dict
        return f"{d['known_cards_sorted']}_{d['unknown_count']}_{d['discard_top']}_{d['round']}"

    # Used to get a string key for Q-table lookups
    def to_key(self):
        return str(self)

    @staticmethod
    def calculate_state_space():
        """Calculate the exact state space size mathematically for the current state representation."""
        import math
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        num_ranks = len(ranks)
        grid_size = 4
        max_rounds = 4
        total_known_combinations = 0
        for num_known in range(grid_size + 1):
            if num_known == 0:
                combinations = 1
            else:
                combinations = math.comb(num_ranks + num_known - 1, num_known)
            total_known_combinations += combinations
        discard_possibilities = num_ranks + 1  # 13 ranks + 'None'
        round_possibilities = max_rounds
        total_states = total_known_combinations * discard_possibilities * round_possibilities
        return total_states