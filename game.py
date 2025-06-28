import itertools
import random
from models import Player, Card
from agents import RandomAgent, HeuristicAgent, QLearningAgent, HumanAgent

class GolfGame:
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    SUITS = ['♠', '♥', '♦', '♣']

    def __init__(self, num_players=4, agent_types=None, q_agents=None):
        self.num_players = num_players
        if agent_types is None:
            agent_types = ["random"] * num_players
        self.players = [Player(f'P{i+1}', agent_types[i]) for i in range(num_players)]
        self.agents = self.create_agents(agent_types, q_agents)
        self.deck = self.create_deck()
        self.discard_pile = []
        self.turn = 0  # Player index
        self.round = 1
        self.max_rounds = 4
        self.deal()

    def create_agents(self, agent_types, q_agents=None):
        agents = []
        for i, agent_type in enumerate(agent_types):
            if agent_type == "random":
                agents.append(RandomAgent())
            elif agent_type == "heuristic":
                agents.append(HeuristicAgent())
            elif agent_type == "qlearning":
                # Use persistent Q-learning agent if provided
                if q_agents and i < len(q_agents):
                    agents.append(q_agents[i])
                else:
                    agents.append(QLearningAgent())
            elif agent_type == "human":
                agents.append(HumanAgent())
            else:
                agents.append(RandomAgent())  # Default to random
        return agents

    def create_deck(self):
        return [Card(rank, suit) for rank, suit in itertools.product(self.RANKS, self.SUITS)]

    def deal(self):
        random.shuffle(self.deck)
        for player in self.players:
            for i in range(4):
                player.grid[i] = self.deck.pop()
        # Start discard pile
        self.discard_pile.append(self.deck.pop())

    def play_turn(self, player, trajectory=None):
        agent = self.agents[self.turn]
        action = agent.choose_action(player, self, trajectory)

        if not action:
            return  # No moves left

        if action['type'] == 'take_discard' and self.discard_pile:
            # Take from discard pile, swap with pos
            new_card = self.discard_pile.pop()
            old_card = player.grid[action['position']]
            player.grid[action['position']] = new_card
            # Make the card visible to ALL players (public)
            for p in self.players:
                p.known[action['position']] = True
            player.add_to_discard_memory(old_card)
            self.discard_pile.append(old_card)
        elif action['type'] == 'draw_deck' and self.deck:
            # Draw from deck
            new_card = self.deck.pop()
            if action.get('keep', True):
                old_card = player.grid[action['position']]
                player.grid[action['position']] = new_card
                # Make the card visible to ALL players (public)
                for p in self.players:
                    p.known[action['position']] = True
                player.add_to_discard_memory(old_card)
                self.discard_pile.append(old_card)
            else:
                player.add_to_discard_memory(new_card)
                self.discard_pile.append(new_card)

    def all_players_done(self):
        return all(all(p.known) for p in self.players)

    def next_player(self):
        self.turn = (self.turn + 1) % self.num_players
        if self.turn == 0:
            self.round += 1

    def play_game(self, verbose=True, trajectories=None):
        if trajectories is None:
            trajectories = [None] * self.num_players

        # Each player must take exactly 4 turns, so game should last exactly 4 rounds
        while self.round <= self.max_rounds:
            player = self.players[self.turn]
            if verbose:
                print(f"\n-- {player.name}'s turn (Round {self.round}) --")
                print(f"Agent: {player.agent_type}")
                print(player)
                print(f"Top of discard: {self.discard_pile[-1]}")

            # Check if player has any moves available
            available_positions = [i for i, known in enumerate(player.known) if not known]
            if available_positions:
                self.play_turn(player, trajectories[self.turn])
            else:
                # Player has no moves (all cards face-up), but still counts as a turn
                if verbose:
                    print(f"{player.name} has no moves available (all cards face-up)")

            self.next_player()

        # Reveal all cards
        for p in self.players:
            p.reveal_all()
        if verbose:
            print("\n=== FINAL GRIDS ===")
            for p in self.players:
                print(f"{p.name} ({p.agent_type}):\n{p}\n")
        scores = [self.calculate_score(p.grid) for p in self.players]
        if verbose:
            for i, s in enumerate(scores):
                print(f"{self.players[i].name} ({self.players[i].agent_type}) score: {s}")
            winner_idx = scores.index(min(scores))
            print(f"Winner: {self.players[winner_idx].name} ({self.players[winner_idx].agent_type})")
        return scores

    def calculate_score(self, grid):
        scores = [card.score() if card else 0 for card in grid]
        total_score = sum(scores)
        ranks = [card.rank if card else None for card in grid]
        pairs = []
        used = set()
        for pos1, pos2 in itertools.combinations(range(4), 2):
            if (ranks[pos1] and ranks[pos2] and ranks[pos1] == ranks[pos2]
                and pos1 not in used and pos2 not in used):
                pairs.append((pos1, pos2))
                used.add(pos1)
                used.add(pos2)
                total_score -= (scores[pos1] + scores[pos2])
        return total_score