import itertools
import random
from models import Player, Card
from agents import RandomAgent, HeuristicAgent, QLearningAgent, HumanAgent, EVAgent, AdvancedEVAgent

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
        self.last_action = None
        self.action_history = []
        self.last_action_turn = None
        self.drawn_card = None  # Add this line

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
            elif agent_type == "ev_ai":
                agents.append(EVAgent())
            elif agent_type == "advanced_ev":
                agents.append(AdvancedEVAgent())
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

    def display_all_grids(self):
        """Display all player grids showing what each player can see"""
        print("\n=== CURRENT GRID STATE ===")
        for i, player in enumerate(self.players):
            print(f"{player.name} ({player.agent_type}):")
            if player.agent_type == "human":
                # Human player can see their own privately visible cards
                print(player)
            else:
                # For AI players, show what the human player can see of them
                def show_other(i):
                    return str(player.grid[i]) if player.known[i] else '?'
                other_display = f"[ {show_other(0)} | {show_other(1)} ]\n[ {show_other(2)} | {show_other(3)} ]"
                print(other_display)
            print()

        # Show what just happened
        if hasattr(self, 'last_action'):
            print(f"Last action: {self.last_action}")
            print()

    def play_turn(self, player, trajectory=None):
        agent = self.agents[self.turn]
        action = agent.choose_action(player, self, trajectory)

        if not action:
            return  # No moves left

        # Track what action was taken
        if action['type'] == 'take_discard' and self.discard_pile:
            # Take from discard pile, swap with pos
            new_card = self.discard_pile.pop()
            old_card = player.grid[action['position']]
            player.grid[action['position']] = new_card
            # Make the card visible to ALL players (public) - only for this player's grid
            player.known[action['position']] = True
            player.add_to_discard_memory(old_card)
            self.discard_pile.append(old_card)
            self.last_action = f"<strong>{player.name}</strong> took {new_card} from discard and placed it at position {action['position']+1}, discarding {old_card}"
            current_turn_id = (self.turn, self.round)
            if self.action_history and self.last_action_turn == current_turn_id:
                self.action_history[-1] = self.last_action
            else:
                self.action_history.append(self.last_action)
            self.last_action_turn = current_turn_id
        elif action['type'] == 'draw_deck' and self.deck:
            # Draw from deck
            new_card = self.deck.pop()
            self.drawn_card = new_card  # Store the drawn card in the game state

            if action.get('keep', True):
                # Keep the drawn card and swap with position
                old_card = player.grid[action['position']]
                player.grid[action['position']] = new_card
                # Make the card visible to ALL players (public) - only for this player's grid
                player.known[action['position']] = True
                player.add_to_discard_memory(old_card)
                self.discard_pile.append(old_card)
                self.last_action = f"<strong>{player.name}</strong> drew {new_card} and kept it at position {action['position']+1}, discarding {old_card}"
                current_turn_id = (self.turn, self.round)
                if self.action_history and self.last_action_turn == current_turn_id:
                    self.action_history[-1] = self.last_action
                else:
                    self.action_history.append(self.last_action)
                self.last_action_turn = current_turn_id
                self.drawn_card = None  # Reset after decision
            else:
                # Discard the drawn card and flip a grid card
                player.add_to_discard_memory(new_card)
                self.last_action = f"<strong>{player.name}</strong> drew {new_card} and discarded it"
                current_turn_id = (self.turn, self.round)
                if self.action_history and self.last_action_turn == current_turn_id:
                    self.action_history[-1] = self.last_action
                else:
                    self.action_history.append(self.last_action)
                self.last_action_turn = current_turn_id
                self.drawn_card = None  # Reset after decision

                # If player chose to flip one of their own cards, that card goes to discard pile
                if 'flip_position' in action:
                    flip_pos = action['flip_position']
                    # Get the card that was flipped
                    flipped_card = player.grid[flip_pos]
                    # Make the card at flip_position visible to ALL players - only for this player's grid
                    player.known[flip_pos] = True
                    # Put the flipped card on the discard pile
                    if flipped_card:
                        player.add_to_discard_memory(flipped_card)
                        self.discard_pile.append(flipped_card)
                        self.last_action += f", flipped their card at position {flip_pos+1} ({flipped_card}), and discarded it"
                        current_turn_id = (self.turn, self.round)
                        if self.action_history and self.last_action_turn == current_turn_id:
                            self.action_history[-1] = self.last_action
                        else:
                            self.action_history.append(self.last_action)
                        self.last_action_turn = current_turn_id
                    else:
                        self.last_action += f", and flipped their card at position {flip_pos+1}"
                        current_turn_id = (self.turn, self.round)
                        if self.action_history and self.last_action_turn == current_turn_id:
                            self.action_history[-1] = self.last_action
                        else:
                            self.action_history.append(self.last_action)
                        self.last_action_turn = current_turn_id

        # Display updated grids after the action
        # self.display_all_grids() # tst

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
                    print(f"<strong>{player.name}</strong> has no moves available (all cards face-up)")

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

    def quick_test(agent_types, num_games):
        num_agents = len(agent_types)
        total_scores = [0] * num_agents

        for _ in range(num_games):
            game = GolfGame(num_players=num_agents, agent_types=agent_types)
            scores = game.play_game(verbose=False)
            for i, score in enumerate(scores):
                total_scores[i] += score

        avg_scores = [total / num_games for total in total_scores]
        print(f"Average scores over {num_games} games:")
        for agent, avg in zip(agent_types, avg_scores):
            print(f"  {agent}: {avg:.2f}")


# test