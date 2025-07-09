import random
import itertools
from collections import defaultdict
from models import Card
from probabilities import expected_value_draw_vs_discard

class RandomAgent:
    """Random agent that makes random legal moves"""
    def choose_action(self, player, game_state, trajectory=None):
        positions = [i for i, known in enumerate(player.known) if not known]
        if not positions:
            return None

        action = random.choice(['draw_deck', 'take_discard'])
        pos = random.choice(positions)

        if action == 'take_discard' and game_state.discard_pile:
            return {'type': 'take_discard', 'position': pos}
        else:
            # For draw_deck, also decide whether to keep the card
            keep = random.choice([True, False])
            return {'type': 'draw_deck', 'position': pos, 'keep': keep}

class HumanAgent:
    """Human agent that allows manual input for testing gameplay"""
    def choose_action(self, player, game_state, trajectory=None):
        # Available positions are those that are not face-up to all players
        positions = [i for i, known in enumerate(player.known) if not known]
        if not positions:
            print("No moves available - all cards are face-up!")
            return None

        print(f"\n=== YOUR TURN ===")

        # Show current state of all grids first
        print("=== CURRENT GAME STATE ===")
        for i, p in enumerate(game_state.players):
            print(f"{p.name} ({p.agent_type}):")
            if p == player:
                # Human player can see their own privately visible cards
                print(p)
            else:
                # For AI players, show what the human player can see of them
                def show_other(i):
                    return str(p.grid[i]) if p.known[i] else '?'
                other_display = f"[ {show_other(0)} | {show_other(1)} ]\n[ {show_other(2)} | {show_other(3)} ]"
                print(other_display)
            print()

        print(f"Your grid (you can see your bottom two cards):")
        print(player)
        print(f"Top of discard pile: {game_state.discard_pile[-1] if game_state.discard_pile else 'None'}")
        print(f"Available positions: {[i+1 for i in positions]} (1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right)")

        # Show other players' grids (only face-up cards)
        print(f"\nOther players' grids (face-up cards only):")
        for i, p in enumerate(game_state.players):
            if p != player:
                # Create a display showing only face-up cards
                def show_other(i):
                    return str(p.grid[i]) if p.known[i] else '?'
                other_display = f"[ {show_other(0)} | {show_other(1)} ]\n[ {show_other(2)} | {show_other(3)} ]"
                print(f"  {p.name}: {other_display}")

        while True:
            try:
                print(f"\nChoose your action:")
                print("1. Take discard card")
                print("2. Draw from deck")
                print("q. Quit game")

                choice = input("Enter 1, 2, or q: ").strip().lower()

                if choice == "q":
                    print("Game quit by player.")
                    raise KeyboardInterrupt  # This will exit the game

                if choice == "1":
                    if not game_state.discard_pile:
                        print("No discard pile available!")
                        continue

                    pos = input(f"Enter position to place card {[i+1 for i in positions]}: ").strip()
                    pos = int(pos) - 1  # Convert to 0-based index

                    if pos not in positions:
                        print(f"Invalid position! Choose from {[i+1 for i in positions]}")
                        continue

                    return {'type': 'take_discard', 'position': pos}

                elif choice == "2":
                    if not game_state.deck:
                        print("No cards left in deck!")
                        continue

                    # Draw the card and show it to the player
                    drawn_card = game_state.deck[-1]  # Peek at the top card
                    print(f"\nYou drew: {drawn_card}")

                    # First decide: keep or discard
                    keep = input("Keep the drawn card? (y/n): ").strip().lower()

                    if keep in ['y', 'yes']:
                        # If keeping, choose position to swap
                        pos = input(f"Enter position to place card {[i+1 for i in positions]}: ").strip()
                        pos = int(pos) - 1  # Convert to 0-based index

                        if pos not in positions:
                            print(f"Invalid position! Choose from {[i+1 for i in positions]}")
                            continue

                        print(f"Current card at position {pos+1}: {player.grid[pos] if player.known[pos] else '?'}")
                        return {'type': 'draw_deck', 'position': pos, 'keep': True}
                    else:
                        # If discarding, ask if they want to flip one of their own cards
                        print(f"\nYou're discarding the {drawn_card}.")
                        print("You must flip one of your own cards face-up.")

                        # Show available positions for flipping
                        flip_positions = [i for i, known in enumerate(player.known) if not known]
                        print(f"Available positions to flip: {[i+1 for i in flip_positions]}")

                        # If there's only one position available, automatically choose it
                        if len(flip_positions) == 1:
                            flip_pos = flip_positions[0]
                            print(f"Automatically flipping position {flip_pos+1} (only option available).")
                        else:
                            flip_pos = input(f"Enter position to flip {[i+1 for i in flip_positions]}: ").strip()
                            flip_pos = int(flip_pos) - 1

                        if flip_pos not in flip_positions:
                            print(f"Invalid position! Choose from {[i+1 for i in flip_positions]}")
                            continue

                        return {'type': 'draw_deck', 'position': -1, 'keep': False, 'flip_position': flip_pos}

                else:
                    print("Invalid choice! Enter 1, 2, or q.")

            except (ValueError, IndexError):
                print("Invalid input! Please try again.")

class HeuristicAgent:
    """Heuristic agent using strategy from original main.py"""
    def choose_action(self, player, game_state, trajectory=None):
        positions = [i for i, known in enumerate(player.known) if not known]
        if not positions:
            return None

        # Update memory with current known cards and discard top
        current_known = [card for i, card in enumerate(player.grid) if player.known[i] and card]
        discard_top = game_state.discard_pile[-1] if game_state.discard_pile else None
        player.update_memory(current_known + ([discard_top] if discard_top else []))

        # Calculate current score
        current_score = self.calculate_score([card if player.known[i] else None for i, card in enumerate(player.grid)])

        # Get deck probabilities
        deck_probs, total_remaining = player.get_deck_probabilities()

        # Calculate baseline expected score (doing nothing)
        baseline_unknown_expected = 0
        for i in range(4):
            if not player.known[i]:
                baseline_unknown_expected += player.expected_score_for_unknown_position(deck_probs)
        baseline_expected = current_score + baseline_unknown_expected

        best_action = None
        best_improvement = float('-inf')

        # Evaluate taking discard card
        if discard_top:
            for pos in positions:
                improvement = self.evaluate_take_discard_action(pos, discard_top, player, deck_probs, baseline_expected)
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_action = {'type': 'take_discard', 'position': pos}

        # Evaluate drawing from deck
        for pos in positions:
            improvement = self.evaluate_draw_deck_action(pos, player, deck_probs, baseline_expected)
            if improvement > best_improvement:
                best_improvement = improvement
                best_action = {'type': 'draw_deck', 'position': pos, 'keep': True}

        # If no good action found, take discard if available, otherwise draw
        if not best_action:
            if discard_top:
                best_action = {'type': 'take_discard', 'position': random.choice(positions)}
            else:
                best_action = {'type': 'draw_deck', 'position': random.choice(positions), 'keep': True}

        return best_action

    def calculate_score(self, grid):
        """Calculate score for a grid (some cards might be None)"""
        scores = [card.score() if card else 0 for card in grid]
        total_score = sum(scores)

        ranks = [card.rank if card else None for card in grid]
        pairs = []
        used_positions = set()

        for pos1, pos2 in itertools.combinations(range(4), 2):
            if (ranks[pos1] and ranks[pos2] and
                ranks[pos1] == ranks[pos2] and
                pos1 not in used_positions and pos2 not in used_positions):
                pairs.append((pos1, pos2))
                used_positions.add(pos1)
                used_positions.add(pos2)
                total_score -= (scores[pos1] + scores[pos2])

        return total_score

    def evaluate_take_discard_action(self, position, discard_card, player, deck_probs, baseline_expected):
        """Evaluate taking discard card and placing it at position"""
        new_grid = player.grid.copy()
        new_grid[position] = discard_card
        new_known = player.known.copy()
        new_known[position] = True

        known_score = self.calculate_score([card if new_known[i] else None for i, card in enumerate(new_grid)])

        # Add expected score for unknown positions
        unknown_expected = 0
        for i in range(4):
            if not new_known[i]:
                unknown_expected += player.expected_score_for_unknown_position(deck_probs)

        total_expected = known_score + unknown_expected
        return baseline_expected - total_expected

    def evaluate_draw_deck_action(self, position, player, deck_probs, baseline_expected):
        """Evaluate drawing from deck and expected outcome at position"""
        total_expected_score = 0

        for rank, prob in deck_probs.items():
            if prob == 0:
                continue

            drawn_card = Card(rank, '♠')
            new_grid = player.grid.copy()
            new_grid[position] = drawn_card
            new_known = player.known.copy()
            new_known[position] = True

            known_score = self.calculate_score([card if new_known[i] else None for i, card in enumerate(new_grid)])

            unknown_expected = 0
            for i in range(4):
                if not new_known[i]:
                    unknown_expected += player.expected_score_for_unknown_position(deck_probs)

            total_score = known_score + unknown_expected
            total_expected_score += prob * total_score

        return baseline_expected - total_expected_score

class QLearningAgent:
    """Q-learning agent that actually learns from experience"""
    def __init__(self, learning_rate=0.1, discount_factor=0.9, epsilon=0.2):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.training_mode = True

    def get_state_key(self, player, game_state):
        """Convert game state to a simplified string key for Q-table"""
        # Simplified state representation focusing on key features
        # Only track known cards and their scores, not specific suits
        known_cards = []
        for i, card in enumerate(player.grid):
            if player.known[i] and card:
                known_cards.append(card.rank)  # Only rank, not suit
            else:
                known_cards.append('?')

        # Sort known cards for consistency (same state regardless of position)
        known_cards_sorted = sorted([c for c in known_cards if c != '?'])
        unknown_count = known_cards.count('?')

        # Include discard top and round for context
        discard_top = game_state.discard_pile[-1].rank if game_state.discard_pile else 'None'

        return f"{known_cards_sorted}_{unknown_count}_{discard_top}_{game_state.round}"

    def get_action_key(self, action):
        """Convert action to a string key"""
        return f"{action['type']}_{action['position']}"

    def choose_action(self, player, game_state, trajectory=None):
        # Get legal actions first
        positions = [i for i, known in enumerate(player.known) if not known]
        if not positions:
            return None

        actions = []
        if game_state.discard_pile:
            for pos in positions:
                actions.append({'type': 'take_discard', 'position': pos})
        if game_state.deck:
            for pos in positions:
                actions.append({'type': 'draw_deck', 'position': pos, 'keep': True})

        if not actions:
            return None

        # Epsilon-greedy policy
        if self.training_mode and random.random() < self.epsilon:
            action = random.choice(actions)
        else:
            # Choose action with highest Q-value
            state_key = self.get_state_key(player, game_state)
            best_action = None
            best_value = float('-inf')

            for action in actions:
                action_key = self.get_action_key(action)
                q_value = self.q_table[state_key][action_key]
                if q_value > best_value:
                    best_value = q_value
                    best_action = action

            action = best_action or random.choice(actions)

        # Record action in trajectory for training
        if trajectory is not None:
            state_key = self.get_state_key(player, game_state)
            action_key = self.get_action_key(action)
            trajectory.append({
                'state_key': state_key,
                'action_key': action_key,
                'action': action
            })

        return action

    def update(self, state_key, action_key, reward, next_state_key, next_actions):
        """Update Q-values using Q-learning update rule"""
        max_next_q = 0
        if next_actions:
            max_next_q = max(self.q_table[next_state_key][self.get_action_key(a)]
                           for a in next_actions)

        current_q = self.q_table[state_key][action_key]
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        self.q_table[state_key][action_key] = new_q

    def train_on_trajectory(self, trajectory, final_reward, final_score):
        """Train the agent on a complete game trajectory with improved rewards"""
        if not trajectory:
            return

        # Update Q-values for each step in the trajectory
        for i, step in enumerate(trajectory):
            state_key = step['state_key']
            action_key = step['action_key']

            # Calculate immediate reward for this action
            # Give small positive reward for taking actions (encourages exploration)
            # The main learning comes from the final reward
            immediate_reward = 0.1  # Small positive reward for taking action

            # Get next state and actions (if not the last step)
            if i < len(trajectory) - 1:
                next_step = trajectory[i + 1]
                next_state_key = next_step['state_key']
                next_actions = [next_step['action']]
            else:
                next_state_key = state_key  # Terminal state
                next_actions = []
                # Add final reward to the last action
                immediate_reward += final_reward

            self.update(state_key, action_key, immediate_reward, next_state_key, next_actions)

    def set_training_mode(self, training):
        """Enable or disable training mode"""
        self.training_mode = training

    def get_q_table_size(self):
        """Get the size of the Q-table for debugging"""
        total_entries = sum(len(actions) for actions in self.q_table.values())
        return len(self.q_table), total_entries

    def decay_epsilon(self, factor=0.995):
        """Decay epsilon for better exploration/exploitation balance"""
        self.epsilon = max(0.01, self.epsilon * factor)

class EVAgent:
    def choose_action(self, player, game, trajectory=None):
        ev = expected_value_draw_vs_discard(game, player)  # Pass the correct player
        available_positions = [i for i, known in enumerate(player.known) if not known]
        if not available_positions:
            return None  # No moves

        # Determine which action is better based on EV values, not just recommendation text
        draw_ev = ev.get('draw_expected_value', 0)
        discard_ev = ev.get('discard_expected_value', 0)

        # Choose the action with the lower (more negative) EV
        if draw_ev < discard_ev:
            # Draw is better - but check if we should keep or flip
            action_type = ev.get('best_action_type', 'keep')

            if action_type == 'flip':
                # Draw, discard, and flip a card
                best_flip_pos = ev.get('best_flip_position')
                if best_flip_pos is not None and best_flip_pos in available_positions:
                    return {'type': 'draw_deck', 'keep': False, 'flip_position': best_flip_pos}
                else:
                    # Fallback: flip first available position
                    return {'type': 'draw_deck', 'keep': False, 'flip_position': available_positions[0]}
            else:
                # Draw and keep the card
                best_pos = ev.get('best_draw_position')
                if best_pos is not None and best_pos in available_positions:
                    return {'type': 'draw_deck', 'position': best_pos, 'keep': True}
                else:
                    # Fallback: use first available position
                    return {'type': 'draw_deck', 'position': available_positions[0], 'keep': True}
        else:
            # Discard is better (or equal)
            best_pos = ev.get('best_discard_position')
            if best_pos is not None and best_pos in available_positions:
                return {'type': 'take_discard', 'position': best_pos}
            else:
                # Fallback: choose first available position
                return {'type': 'take_discard', 'position': available_positions[0]}


class AdvancedEVAgent(EVAgent):
    """
    Advanced EV Agent with sophisticated features:
    - Pair-aware flipping: Knows that flipping one half of a pair will result in zero score for that pair
    - Trajectory recording: Records decision history for analysis
    - Advanced position evaluation: Considers future pairing opportunities
    - Risk assessment: Evaluates the risk of revealing high-value cards
    """

    def __init__(self):
        self.decision_history = []  # Track all decisions for analysis
        self.pair_memory = {}  # Remember potential pairs we've seen

    def choose_action(self, player, game, trajectory=None):
        # Record this decision point
        decision_point = {
            'round': game.round,
            'turn': game.turn,
            'player_cards': self._get_visible_cards(player),
            'discard_top': str(game.discard_pile[-1]) if game.discard_pile else None,
            'available_positions': [i for i, known in enumerate(player.known) if not known]
        }

        # Get base EV analysis
        ev = expected_value_draw_vs_discard(game, player)
        available_positions = [i for i, known in enumerate(player.known) if not known]

        if not available_positions:
            return None  # No moves

        # Enhanced decision making with advanced features
        action = self._advanced_decision_making(player, game, ev, available_positions)

        # Record the decision
        decision_point['action'] = action
        decision_point['ev_analysis'] = ev
        self.decision_history.append(decision_point)

        # Record in trajectory if provided (for compatibility with Q-learning framework)
        if trajectory is not None:
            trajectory.append({
                'agent_type': 'advanced_ev',
                'decision_point': decision_point,
                'action': action
            })

        return action

    def _get_visible_cards(self, player):
        """Get all cards visible to this player (public + private)"""
        visible_cards = []
        for i, card in enumerate(player.grid):
            if card and (player.known[i] or player.privately_visible[i]):
                visible_cards.append({
                    'position': i,
                    'card': str(card),
                    'rank': card.rank,
                    'score': card.score(),
                    'public': player.known[i]
                })
        return visible_cards

    def _advanced_decision_making(self, player, game, ev, available_positions):
        """Enhanced decision making with pair awareness and risk assessment"""
        draw_ev = ev.get('draw_expected_value', 0)
        discard_ev = ev.get('discard_expected_value', 0)

        # Analyze potential pairs in current hand
        pair_analysis = self._analyze_potential_pairs(player)

        # Enhanced draw decision with pair awareness
        if draw_ev < discard_ev:
            action_type = ev.get('best_action_type', 'keep')

            if action_type == 'flip':
                # Advanced flip decision considering pairs
                best_flip_pos = self._choose_best_flip_position(player, available_positions, pair_analysis)
                return {'type': 'draw_deck', 'keep': False, 'flip_position': best_flip_pos}
            else:
                # Advanced keep decision considering pairs
                best_pos = self._choose_best_keep_position(player, ev, available_positions, pair_analysis)
                return {'type': 'draw_deck', 'position': best_pos, 'keep': True}
        else:
            # Enhanced discard decision
            best_pos = self._choose_best_discard_position(player, ev, available_positions, pair_analysis)
            return {'type': 'take_discard', 'position': best_pos}

    def _analyze_potential_pairs(self, player):
        """Analyze potential pairs in the current hand"""
        visible_cards = self._get_visible_cards(player)
        rank_counts = {}

        # Count visible cards by rank
        for card_info in visible_cards:
            rank = card_info['rank']
            rank_counts[rank] = rank_counts.get(rank, 0) + 1

        # Find potential pairs (cards that could form pairs)
        potential_pairs = {}
        for rank, count in rank_counts.items():
            if count >= 1:  # At least one card of this rank
                potential_pairs[rank] = {
                    'count': count,
                    'positions': [card['position'] for card in visible_cards if card['rank'] == rank],
                    'score': Card(rank, '♠').score(),
                    'pair_value': 0 if count >= 2 else Card(rank, '♠').score()  # Zero if already paired
                }

        return potential_pairs

    def _choose_best_flip_position(self, player, available_positions, pair_analysis):
        """Choose the best position to flip considering pair implications"""
        best_pos = available_positions[0]  # Default
        best_score = float('inf')

        for pos in available_positions:
            if not player.grid[pos]:
                continue

            card = player.grid[pos]
            rank = card.rank
            card_score = card.score()

            # Calculate the impact of flipping this card
            impact_score = card_score

            # If this card could complete a pair, flipping it might be beneficial
            if rank in pair_analysis and pair_analysis[rank]['count'] == 1:
                # This would complete a pair - the pair becomes worth 0 instead of 2 * card_score
                impact_score = card_score - (2 * card_score)  # Net benefit of -card_score
            elif rank in pair_analysis and pair_analysis[rank]['count'] >= 2:
                # Already have a pair - flipping one half reduces the pair to a single card
                impact_score = card_score  # Lose the pair bonus

            if impact_score < best_score:
                best_score = impact_score
                best_pos = pos

        return best_pos

    def _choose_best_keep_position(self, player, ev, available_positions, pair_analysis):
        """Choose the best position to keep drawn card considering pairs"""
        # Use EV recommendation as base
        best_pos = ev.get('best_draw_position')
        if best_pos is not None and best_pos in available_positions:
            return best_pos

        # Fallback: choose position that maximizes pair potential
        best_pos = available_positions[0]
        best_pair_potential = -1

        for pos in available_positions:
            if not player.grid[pos]:
                continue

            current_card = player.grid[pos]
            current_rank = current_card.rank

            # Count how many cards of this rank we already have
            rank_count = sum(1 for card_info in self._get_visible_cards(player)
                           if card_info['rank'] == current_rank)

            # Prefer positions that could form pairs
            if rank_count >= 1:
                return pos

        return best_pos

    def _choose_best_discard_position(self, player, ev, available_positions, pair_analysis):
        """Choose the best position for discard card considering pairs"""
        # Use EV recommendation as base
        best_pos = ev.get('best_discard_position')
        if best_pos is not None and best_pos in available_positions:
            return best_pos

        # Fallback: choose position that minimizes score impact
        best_pos = available_positions[0]
        best_score = float('inf')

        for pos in available_positions:
            if not player.grid[pos]:
                continue

            current_card = player.grid[pos]
            current_score = current_card.score()

            # Prefer replacing high-value cards
            if current_score > best_score:
                best_score = current_score
                best_pos = pos

        return best_pos

    def get_decision_history(self):
        """Get the complete decision history for analysis"""
        return self.decision_history

    def reset_history(self):
        """Reset decision history (useful for new games)"""
        self.decision_history = []
        self.pair_memory = {}