import random
import itertools
import re
from collections import defaultdict
# Import from same directory
from models import Card
from probabilities import expected_value_draw_vs_discard
import csv
import os

# Point values used for reward shaping (matches Card.score())
_RANK_SCORE = {
    'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 0, 'Q': 10, 'K': 10,
}
_HIGH_RANKS = frozenset({'10', 'Q', 'K'})  # bad to keep unpaired (J is 0 — good)

# Add PyTorch imports for GPU support  asdf
try:
    import torch
    import torch.nn as nn
    import numpy as np
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("Warning: PyTorch not available. GPUQLearningAgent will not work.")

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
            if keep:
                return {'type': 'draw_deck', 'position': pos, 'keep': True}
            else:
                return {'type': 'draw_deck', 'position': -1, 'keep': False, 'flip_position': pos}

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

# Default dense reward-shaping weights (editable from /rl UI).
# For a true solve, set enabled=False (or all weights to 0) so learning
# optimizes only terminal golf outcomes — shaped rewards can bias the policy.
DEFAULT_REWARD_SHAPING = {
    "enabled": True,
    "step": 0.05,
    "pair": 1.5,
    "high_keep": -0.8,
    "low_keep": 0.3,
    "midhigh_keep": -0.4,
    "flip": 0.1,
}

# Soft Q prior on first visit: map visible-hand golf strength → Q₀ ∈ [-scale, +scale]
DEFAULT_SOFT_PRIOR = {
    "enabled": True,
    "max_round": 0,   # deal-only prior (0..max_round inclusive); use 1–2 for wider early bias
    "scale": 5.0,     # |Q₀| cap — matches terminal reward magnitude band
}

# Human-demo-derived action heuristics (CPU tabular). Soft priors seed Q₀;
# hard gates filter legal actions outside bootstrap (teacher stays unmasked).
DEFAULT_ACTION_HEURISTICS = {
    "discard_soft_prior": True,   # first-visit Q bias on take_discard
    "discard_hard_gate": True,    # forbid take of junk discard (unless pair)
    "discard_junk_min_pts": 8,    # hard: ban take if pts >= this and not pair
    "discard_soft_scale": 5.0,    # |bias| for soft discard prior
    "pair_force_take": True,      # hard: if discard pairs known rank → only take
    "ban_junk_on_private": True,  # hard last-turn: no 10/Q/K onto low private
    "junk_private_max_pts": 3,    # "low" private card threshold (pts <= this)
}


class QLearningAgent:
    """Q-learning agent that actually learns from experience"""
    def __init__(self, learning_rate=0.1, discount_factor=0.9, epsilon=0.2,
                 n_bootstrap_games=250, reward_shaping=None, exploration_beta=0.5,
                 soft_prior=None, action_heuristics=None):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table = defaultdict(lambda: defaultdict(float))
        # Visit counts N(s,a) — used for count-based exploration + coverage/sparsity
        self.visit_counts = defaultdict(lambda: defaultdict(int))
        self.exploration_beta = float(exploration_beta)
        self.training_mode = True
        # When False, choose_action records trajectories but skips online BC/Q mutations
        # (used by parallel rollout workers; main process applies updates).
        self.online_updates = True
        self.n_bootstrap_games = n_bootstrap_games
        self.games_played = 0
        # Optional HumanDemoPolicy: human action on state match, else EV (bootstrap only)
        self.human_demo_policy = None
        self.reward_shaping = dict(DEFAULT_REWARD_SHAPING)
        if reward_shaping:
            self.reward_shaping.update(reward_shaping)
        self.soft_prior = dict(DEFAULT_SOFT_PRIOR)
        if soft_prior:
            self.soft_prior.update(soft_prior)
        self.action_heuristics = dict(DEFAULT_ACTION_HEURISTICS)
        if action_heuristics:
            self.action_heuristics.update(action_heuristics)

    def get_state_key(self, player, game_state):
        # Separate public cards (flipped, visible to all) from private cards (known only to this player)
        public_cards = tuple(sorted(card.rank for i, card in enumerate(player.grid)
                                  if card and player.known[i]))
        private_cards = tuple(sorted(card.rank for i, card in enumerate(player.grid)
                                   if card and player.privately_visible[i] and not player.known[i]))

        # Discard card rank (since score isn't useful for Jacks)
        discard_rank = game_state.discard_pile[-1].rank if game_state.discard_pile else 'none'

        # Round number
        round_num = game_state.round

        if getattr(game_state, 'drawn_card', None):
            drawn_card_str = game_state.drawn_card.rank
        else:
            drawn_card_str = 'none'
        # No EV advantage bucket — bootstrap already teaches EV; adv_ only exploded the table
        return f"pub_{public_cards}_priv_{private_cards}_dis_{discard_rank}_drawn_{drawn_card_str}_round_{round_num}"

    def get_action_key(self, action):
        """Convert action to a string key"""
        if action['type'] == 'draw_deck' and not action.get('keep', True):
            # For draw-discard-flip actions, use flip_position
            return f"{action['type']}_flip_{action['flip_position']}"
        else:
            # For take_discard and draw_deck_keep actions, use position
            return f"{action['type']}_{action['position']}"

    def get_legal_actions(self, player, game_state):
        """Get all legal actions for the current game state"""
        actions = []

        # Get available positions (cards that are not public/face-up)
        available_positions = [i for i, known in enumerate(player.known) if not known]

        if not available_positions:
            return actions

        # Add take discard actions (if discard pile exists)
        if game_state.discard_pile:
            for pos in available_positions:
                actions.append({'type': 'take_discard', 'position': pos})

        # Add draw deck actions (if deck exists)
        if game_state.deck:
            # Draw and keep actions
            for pos in available_positions:
                actions.append({'type': 'draw_deck', 'position': pos, 'keep': True})

            # Draw, discard, and flip actions
            for flip_pos in available_positions:
                actions.append({'type': 'draw_deck', 'keep': False, 'flip_position': flip_pos})

        return actions

    def is_bootstrapping(self):
        """True only during EV pretraining (games_played < n_bootstrap_games)."""
        return self.n_bootstrap_games > 0 and self.games_played < self.n_bootstrap_games

    def behavioral_clone(self, state_key, action_key, target=1.0):
        """
        Behavioral cloning: pull expert action's Q toward `target`.
        Only used during bootstrap — stop once Q-learning phase begins.
        """
        current = self.get_q(state_key, action_key)
        self.q_table[state_key][action_key] = (
            current + self.learning_rate * (target - current)
        )

    @staticmethod
    def _parse_round(state_key: str) -> int | None:
        m = re.search(r"_round_(\d+)$", state_key or "")
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    def _hand_strength_prior(self, state_key: str) -> float:
        """Map visible hand golf points → Q₀ ∈ [-scale, +scale].

        Low points (A/2/J) → positive prior; high points (10/Q/K) → negative.
        Neutral (~5 pts/card) → ~0. No visible cards → 0.
        """
        sp = self.soft_prior or {}
        scale = float(sp.get("scale", 5.0) or 5.0)
        round_num = self._parse_round(state_key)
        max_round = int(sp.get("max_round", 2))
        if round_num is not None and round_num > max_round:
            return 0.0

        _, _, hand_ranks = self._parse_state_ranks(state_key)
        if not hand_ranks:
            return 0.0
        pts = [_RANK_SCORE.get(r, 5) for r in hand_ranks]
        avg = sum(pts) / len(pts)
        # avg 0 → +scale, avg 5 → 0, avg 10 → -scale
        prior = scale * (1.0 - avg / 5.0)
        return float(max(-scale, min(scale, prior)))

    def has_q(self, state_key, action_key) -> bool:
        """True if (s,a) was written explicitly (learned, loaded, or soft-prior seeded)."""
        if state_key not in self.q_table:
            return False
        return action_key in self.q_table[state_key]

    def get_q(self, state_key, action_key) -> float:
        """Read Q(s,a); on first visit optionally seed soft priors."""
        if self.has_q(state_key, action_key):
            return float(self.q_table[state_key][action_key])
        prior = 0.0
        if (self.soft_prior or {}).get("enabled", True):
            prior = self._hand_strength_prior(state_key)
        prior += self._discard_take_soft_prior(state_key, action_key)
        self.q_table[state_key][action_key] = prior
        return float(prior)

    @staticmethod
    def _parse_state_ranks(state_key):
        """Extract discard/drawn ranks and known hand ranks from a state key."""
        dis_m = re.search(r'_dis_([^_]+)_drawn_', state_key)
        drawn_m = re.search(r'_drawn_([^_]+)_round_', state_key)
        discard_rank = dis_m.group(1) if dis_m else 'none'
        drawn_rank = drawn_m.group(1) if drawn_m else 'none'
        hand_ranks = set(re.findall(r"'([A2-9JQK]|10)'", state_key))
        return discard_rank, drawn_rank, hand_ranks

    @staticmethod
    def _rank_pts(rank) -> int:
        if not rank or rank == "none":
            return 5
        return int(_RANK_SCORE.get(str(rank), 5))

    def _discard_take_soft_prior(self, state_key: str, action_key: str) -> float:
        """First-visit bias on take_discard from human discard-gate stats.

        discard ≤2 or pair → +scale; 3–4 → +0.3·scale; ≥7 non-pair → −scale.
        """
        ah = self.action_heuristics or {}
        if not ah.get("discard_soft_prior", True):
            return 0.0
        if not (action_key or "").startswith("take_discard"):
            return 0.0
        discard_rank, _, hand_ranks = self._parse_state_ranks(state_key)
        if not discard_rank or discard_rank == "none":
            return 0.0
        scale = float(ah.get("discard_soft_scale", 5.0) or 5.0)
        is_pair = discard_rank in hand_ranks
        pts = self._rank_pts(discard_rank)
        if is_pair or pts <= 2:
            return float(scale)
        if pts <= 4:
            return float(0.3 * scale)
        if pts >= 7 and not is_pair:
            return float(-scale)
        return 0.0

    @staticmethod
    def _player_known_ranks(player) -> set:
        ranks = set()
        priv = getattr(player, "privately_visible", None) or [False] * 4
        for i, card in enumerate(player.grid):
            if not card:
                continue
            if player.known[i] or (i < len(priv) and priv[i]):
                ranks.add(card.rank)
        return ranks

    def _is_last_turn(self, player, game_state) -> bool:
        """True on final round or when only one non-public slot remains."""
        max_r = int(getattr(game_state, "max_rounds", 4) or 4)
        round_num = int(getattr(game_state, "round", 1) or 1)
        avail = sum(1 for k in player.known if not k)
        return round_num >= max_r or avail <= 1

    def _incoming_rank_for_action(self, action, game_state):
        """Rank being placed by take/keep, if known at decision time."""
        if action.get("type") == "take_discard":
            if game_state.discard_pile:
                return game_state.discard_pile[-1].rank
            return None
        if action.get("type") == "draw_deck" and action.get("keep", True):
            drawn = getattr(game_state, "drawn_card", None)
            return drawn.rank if drawn else None
        return None

    def _plants_junk_on_low_private(self, action, player, game_state) -> bool:
        """True if take/keep would put 10/Q/K onto a known low private card."""
        ah = self.action_heuristics or {}
        max_priv = int(ah.get("junk_private_max_pts", 3))
        if action.get("type") == "draw_deck" and not action.get("keep", True):
            return False
        pos = action.get("position")
        if pos is None:
            return False
        try:
            pos = int(pos)
        except (TypeError, ValueError):
            return False
        priv = getattr(player, "privately_visible", None) or [False] * 4
        if pos >= len(player.grid) or not player.grid[pos]:
            return False
        if player.known[pos] or not (pos < len(priv) and priv[pos]):
            return False  # only ban replacing still-private known lows
        if self._rank_pts(player.grid[pos].rank) > max_priv:
            return False
        incoming = self._incoming_rank_for_action(action, game_state)
        if incoming is None:
            return False  # unknown draw — can't gate keep yet
        return incoming in _HIGH_RANKS

    def filter_heuristic_actions(self, actions, player, game_state):
        """Apply hard human-demo gates. Never returns empty if `actions` was non-empty.

        Used outside bootstrap so EV/human teachers are not remasked.
        """
        if not actions:
            return actions
        ah = self.action_heuristics or {}
        discard = game_state.discard_pile[-1] if game_state.discard_pile else None
        discard_rank = discard.rank if discard else None
        known = self._player_known_ranks(player)
        is_pair = bool(discard_rank and discard_rank in known)
        junk_min = int(ah.get("discard_junk_min_pts", 8))

        filtered = list(actions)

        if ah.get("discard_hard_gate", True) and discard_rank and not is_pair:
            if self._rank_pts(discard_rank) >= junk_min:
                filtered = [a for a in filtered if a.get("type") != "take_discard"]

        if ah.get("pair_force_take", True) and is_pair:
            takes = [a for a in filtered if a.get("type") == "take_discard"]
            if takes:
                filtered = takes

        if ah.get("ban_junk_on_private", True) and self._is_last_turn(player, game_state):
            filtered = [
                a for a in filtered
                if not self._plants_junk_on_low_private(a, player, game_state)
            ]

        return filtered if filtered else list(actions)

    def shaped_step_reward(self, step):
        """
        Dense reward shaping from a trajectory step (weights from self.reward_shaping).
        Disable via reward_shaping['enabled']=False for unbiased / solve-mode training.
        """
        rs = self.reward_shaping
        if not rs.get("enabled", True):
            return 0.0

        reward = float(rs.get("step", 0.05))
        action = step.get('action')
        if isinstance(action, str):
            try:
                import ast
                action = ast.literal_eval(action)
            except (ValueError, SyntaxError):
                return reward
        if not isinstance(action, dict):
            return reward

        discard_rank, drawn_rank, hand_ranks = self._parse_state_ranks(step.get('state_key', ''))
        placed_rank = None
        if action.get('type') == 'take_discard':
            placed_rank = discard_rank if discard_rank != 'none' else None
        elif action.get('type') == 'draw_deck' and action.get('keep', True):
            # keep path: drawn is usually unknown at decision time (drawn_none);
            # skip pair/high shaping when we can't see the card
            if drawn_rank != 'none':
                placed_rank = drawn_rank

        if placed_rank and placed_rank != 'none':
            if placed_rank in hand_ranks:
                reward += float(rs.get("pair", 1.5))
            elif placed_rank in _HIGH_RANKS:
                reward += float(rs.get("high_keep", -0.8))
            else:
                pts = _RANK_SCORE.get(placed_rank, 5)
                if pts <= 3:
                    reward += float(rs.get("low_keep", 0.3))
                elif pts >= 8:
                    reward += float(rs.get("midhigh_keep", -0.4))

        if action.get('type') == 'draw_deck' and not action.get('keep', True):
            reward += float(rs.get("flip", 0.1))

        return reward

    def choose_action(self, player, game_state, trajectory=None):
        legal_actions = self.get_legal_actions(player, game_state)
        if not legal_actions:
            return None

        # Bootstrapping: human demo when state matches/close, else EVAgent
        if self.is_bootstrapping():
            action = None
            if self.human_demo_policy:
                try:
                    from human_bootstrap import choose_bootstrap_action

                    action, _tier = choose_bootstrap_action(
                        encoder=self,
                        policy=self.human_demo_policy,
                        player=player,
                        game_state=game_state,
                        legal_actions=legal_actions,
                    )
                except Exception:
                    action = None
            if action is None:
                ev_agent = EVAgent()
                action = ev_agent.choose_action(player, game_state)
            if action not in legal_actions:
                # Human/EV action may not compare equal by identity — rematch by key
                matched = None
                try:
                    want = self.get_action_key(action) if action else None
                    if want:
                        for a in legal_actions:
                            if self.get_action_key(a) == want:
                                matched = a
                                break
                except Exception:
                    matched = None
                action = matched if matched is not None else random.choice(legal_actions)
            # Real imitation: boost the expert action's Q (behavioral cloning).
            # Stops automatically when bootstrap ends.
            if self.online_updates:
                state_key = self.get_state_key(player, game_state)
                action_key = self.get_action_key(action)
                self.behavioral_clone(state_key, action_key, target=1.0)
        else:
            # Hard human-demo gates (discard junk / pair force / last-turn private)
            legal_actions = self.filter_heuristic_actions(
                legal_actions, player, game_state
            )
            # Custom epsilon-greedy: 1/3 take_discard, 1/3 draw_deck_keep, 1/3 draw_deck_discard_flip
            if self.training_mode and random.random() < self.epsilon:
                # Group legal actions by type
                type_groups = {
                    'take_discard': [],
                    'draw_deck_keep': [],
                    'draw_deck_discard_flip': []
                }
                for a in legal_actions:
                    if a['type'] == 'take_discard':
                        type_groups['take_discard'].append(a)
                    elif a['type'] == 'draw_deck' and a.get('keep', True):
                        type_groups['draw_deck_keep'].append(a)
                    elif a['type'] == 'draw_deck' and not a.get('keep', True):
                        type_groups['draw_deck_discard_flip'].append(a)
                # Pick a type at random (only among those with available actions)
                available_types = [k for k, v in type_groups.items() if v]
                chosen_type = random.choice(available_types)
                action = random.choice(type_groups[chosen_type])
            else:
                state_key = self.get_state_key(player, game_state)
                best_action = None
                best_value = float('-inf')
                beta = float(getattr(self, "exploration_beta", 0.0) or 0.0)
                for action_candidate in legal_actions:
                    action_key = self.get_action_key(action_candidate)
                    q_value = self.get_q(state_key, action_key)
                    # Count-based bonus: prefer rarely tried (s,a)
                    if beta > 0:
                        n = int(self.visit_counts[state_key][action_key])
                        q_value = q_value + beta / (n + 1) ** 0.5
                    if q_value > best_value:
                        best_value = q_value
                        best_action = action_candidate
                action = best_action

        # Record trajectory if provided
        if trajectory is not None:
            state_key = self.get_state_key(player, game_state)
            action_key = self.get_action_key(action)
            # Legal keys after heuristic filter (Q phase) so max-Q bootstrap matches policy
            traj_legal = legal_actions
            trajectory.append({
                'state_key': state_key,
                'action_key': action_key,
                'action': action,
                # Legal action keys at this state — needed for true max_{a'} Q(s', a')
                'legal_action_keys': [self.get_action_key(a) for a in traj_legal],
                'round': getattr(game_state, 'round', None)
            })
        return action

    def notify_game_end(self):
        self.games_played += 1

    def _max_next_q(self, next_state_key, next_action_keys) -> float:
        """Q-learning bootstrap: max over legal action keys at s' (not the taken action only)."""
        if not next_action_keys:
            return 0.0
        return max(float(self.get_q(next_state_key, ak)) for ak in next_action_keys)

    def update(self, state_key, action_key, reward, next_state_key, next_actions, done=False):
        """Update Q-values using the Q-learning rule.

        next_actions may be a list of action dicts or action-key strings.
        When done=True (terminal), bootstrap value is 0.
        """
        if done:
            max_next_q = 0.0
        elif not next_actions:
            max_next_q = 0.0
        else:
            keys = []
            for a in next_actions:
                if isinstance(a, str):
                    keys.append(a)
                else:
                    keys.append(self.get_action_key(a))
            max_next_q = self._max_next_q(next_state_key, keys)

        current_q = self.get_q(state_key, action_key)
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        self.q_table[state_key][action_key] = new_q

    def train_on_trajectory(self, trajectory, final_reward, final_score, n_step=3):
        """n-step Q-learning with dense step shaping + terminal reward.

        Priority 1: bootstrap with max Q over *legal* actions at s_{t+n}, not the
        action that happened to be taken in the trajectory.
        """
        if not trajectory:
            return

        n_step = max(1, int(n_step))
        T = len(trajectory)
        rewards = []
        for i, step in enumerate(trajectory):
            r = float(self.shaped_step_reward(step))
            if i == T - 1:
                r += float(final_reward)
            rewards.append(r)

        for t in range(T):
            G = 0.0
            discount = 1.0
            hit_terminal = False
            for k in range(n_step):
                idx = t + k
                if idx >= T:
                    hit_terminal = True
                    break
                G += discount * rewards[idx]
                if idx == T - 1:
                    hit_terminal = True
                    break
                discount *= self.discount_factor

            if not hit_terminal:
                # Full n-step window: bootstrap at s_{t+n} with max over legal actions
                boot = trajectory[t + n_step]
                next_state_key = boot["state_key"]
                legal_keys = boot.get("legal_action_keys") or []
                if not legal_keys and boot.get("action_key"):
                    legal_keys = [boot["action_key"]]
                max_next = self._max_next_q(next_state_key, legal_keys)
                G += discount * max_next

            state_key = trajectory[t]["state_key"]
            action_key = trajectory[t]["action_key"]
            current_q = self.get_q(state_key, action_key)
            self.q_table[state_key][action_key] = current_q + self.learning_rate * (
                G - current_q
            )
            self.visit_counts[state_key][action_key] = int(
                self.visit_counts[state_key][action_key]
            ) + 1

    def set_training_mode(self, training):
        """Enable or disable training mode"""
        self.training_mode = training

    def get_q_table_size(self):
        """Get the size of the Q-table for debugging"""
        total_entries = sum(len(actions) for actions in self.q_table.values())
        return len(self.q_table), total_entries

    def get_coverage_stats(self, well_visited_min: int = 5) -> dict:
        """Sparsity / completion proxies for the growing Q-table.

        There is no known finite 'full' state space — completion is relative:
        - completion_pct: fraction of (s,a) entries with N >= well_visited_min
        - sparsity_index: 1 - completion_pct (1 = all under-visited, 0 = all well-visited)
        - mean_visits: average N(s,a) over entries that exist
        """
        visits = []
        for sk, actions in self.q_table.items():
            for ak in actions:
                visits.append(int(self.visit_counts[sk][ak]))
        n = len(visits)
        if n == 0:
            return {
                "states": 0,
                "entries": 0,
                "mean_visits": 0.0,
                "median_visits": 0.0,
                "pct_once": 0.0,
                "completion_pct": 0.0,
                "sparsity_index": 1.0,
                "well_visited_min": well_visited_min,
            }
        visits_sorted = sorted(visits)
        well = sum(1 for v in visits if v >= well_visited_min)
        once = sum(1 for v in visits if v <= 1)
        completion = well / n
        return {
            "states": len(self.q_table),
            "entries": n,
            "mean_visits": float(sum(visits) / n),
            "median_visits": float(visits_sorted[n // 2]),
            "pct_once": once / n,
            "completion_pct": completion,
            "sparsity_index": 1.0 - completion,
            "well_visited_min": well_visited_min,
        }

    def decay_epsilon(self, factor=0.995):
        """Decay epsilon for better exploration/exploitation balance"""
        self.epsilon = max(0.01, self.epsilon * factor)

    def save_q_table_csv(self, filename="qtable_train.csv"):
        override = (os.environ.get("RL_OUTPUT_DIR") or "").strip()
        if override:
            os.makedirs(override, exist_ok=True)
            output_path = os.path.join(override, filename)
        else:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RL', 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['state_key', 'action_key', 'q_value', 'visits'])
            for state_key, actions in self.q_table.items():
                for action_key, q_value in actions.items():
                    visits = int(self.visit_counts[state_key][action_key])
                    writer.writerow([state_key, action_key, q_value, visits])
        print(f"Q-table saved to {output_path}")

    def load_q_table_csv(self, filename="qtable_train.csv"):
        override = (os.environ.get("RL_OUTPUT_DIR") or "").strip()
        if override:
            output_path = os.path.join(override, filename)
        else:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RL', 'output')
            output_path = os.path.join(output_dir, filename)
        if not os.path.exists(output_path):
            print(f"No Q-table file found at {output_path}, starting fresh.")
            return
        with open(output_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)
            for row in reader:
                if len(row) < 3:
                    continue
                state_key, action_key, q_value = row[0], row[1], row[2]
                try:
                    self.q_table[state_key][action_key] = float(q_value)
                    if len(row) >= 4 and row[3] != "":
                        self.visit_counts[state_key][action_key] = int(float(row[3]))
                except ValueError:
                    continue
        print(f"Loaded Q-table from {output_path}")

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


# ============================================================================
# GPU-ACCELERATED Q-LEARNING AGENT
# ============================================================================

def get_device():
    """Get the best available device (GPU if available, else CPU)"""
    if not TORCH_AVAILABLE:
        return None

    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"🚀 Using GPU: {torch.cuda.get_device_name(0)}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        device = torch.device("cpu")
        print("💻 Using CPU")
    return device


class GPUQLearningAgent(QLearningAgent):
    """GPU-accelerated version of QLearningAgent using PyTorch tensors for computation, but same Q-table structure as CPU agent."""

    def __init__(self, learning_rate=0.1, discount_factor=0.9, epsilon=0.2,
                 n_bootstrap_games=0, device=None, reward_shaping=None):
        super().__init__(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            epsilon=epsilon,
            n_bootstrap_games=n_bootstrap_games,
            reward_shaping=reward_shaping,
        )
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for GPUQLearningAgent")
        self.device = device if device else get_device()
        # Q-table is now a defaultdict of defaultdicts, just like CPU agent
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.optimizer = None
        self.criterion = nn.MSELoss()

    def get_q_value(self, state_key, action_key):
        # Use float value from dict, but can convert to tensor for computation
        return self.q_table[state_key][action_key]

    def update_q_value(self, state_key, action_key, new_value):
        self.q_table[state_key][action_key] = new_value

    def train_on_trajectory(self, trajectory, final_reward, final_score):
        """Delegate to base class (includes dense reward shaping)."""
        return QLearningAgent.train_on_trajectory(self, trajectory, final_reward, final_score)

    def update(self, state_key, action_key, reward, next_state_key, next_actions, done=False):
        """Same Q-learning rule as CPU (legal max), optional tensor max."""
        if done or not next_actions:
            max_next_q = 0.0
        else:
            keys = []
            for a in next_actions:
                if isinstance(a, str):
                    keys.append(a)
                else:
                    keys.append(self.get_action_key(a))
            next_qs = [self.q_table[next_state_key][ak] for ak in keys]
            max_next_q = float(torch.tensor(next_qs, device=self.device).max()) if next_qs else 0.0
        current_q = self.q_table[state_key][action_key]
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        self.q_table[state_key][action_key] = new_q

    def train_on_batch_trajectories_vectorized(self, batch_trajectories, batch_rewards, batch_scores):
        """Batch training via n-step Q path on the base class."""
        if not batch_trajectories:
            return
        for trajectory, reward, score in zip(batch_trajectories, batch_rewards, batch_scores):
            QLearningAgent.train_on_trajectory(self, trajectory, reward, score, n_step=3)

    def get_q_table_size(self):
        """Get the size of the Q-table for debugging (matches CPU agent)."""
        total_entries = sum(len(actions) for actions in self.q_table.values())
        return len(self.q_table), total_entries