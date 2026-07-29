#!/usr/bin/env python3
"""
Neural DQN training path for Golf (GPU-friendly).

Unlike tabular Q-learning, this uses a PyTorch MLP over a fixed state vector and
a discrete action head. Game simulation stays on CPU; gradient updates run on
CUDA/MPS when available — this is what actually loads a GPU.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

import numpy as np

_RL_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_RL_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
if _RL_DIR not in sys.path:
    sys.path.insert(0, _RL_DIR)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError as e:
    raise SystemExit(f"PyTorch required for DQN training: {e}") from e

from agents import EVAgent, RandomAgent, AdvancedEVAgent, QLearningAgent  # noqa: E402
from game import GolfGame  # noqa: E402
from progress_io import (  # noqa: E402
    append_progress_checkpoint,
    get_output_path,
    mark_progress_complete,
    save_training_stats_json,
)

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_TO_I = {r: i for i, r in enumerate(RANKS)}
NUM_ACTIONS = 12  # 4 take_discard + 4 draw_keep + 4 draw_flip
# State: own 4*(1known+1priv+13rank) + discard13 + drawn13 + round + deck_frac + opp4*13
STATE_DIM = 4 * 15 + 13 + 13 + 1 + 1 + 4 * 13  # 140


def get_device(prefer_gpu: bool = True) -> torch.device:
    if prefer_gpu and torch.cuda.is_available():
        return torch.device("cuda")
    if prefer_gpu and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _rank_onehot(rank: str | None) -> list[float]:
    v = [0.0] * 13
    if rank in RANK_TO_I:
        v[RANK_TO_I[rank]] = 1.0
    return v


def encode_state(player, game) -> np.ndarray:
    feats: list[float] = []
    for i in range(4):
        known = 1.0 if player.known[i] else 0.0
        priv = 1.0 if player.privately_visible[i] else 0.0
        feats.append(known)
        feats.append(priv)
        card = player.grid[i]
        visible = player.known[i] or player.privately_visible[i]
        feats.extend(_rank_onehot(card.rank if card and visible else None))

    discard = game.discard_pile[-1].rank if game.discard_pile else None
    feats.extend(_rank_onehot(discard))
    drawn = game.drawn_card.rank if getattr(game, "drawn_card", None) else None
    feats.extend(_rank_onehot(drawn))
    feats.append(float(getattr(game, "round", 1)) / float(getattr(game, "max_rounds", 4) or 4))
    feats.append(len(game.deck) / 52.0)

    # Opponent public cards (player 1 if we are 0)
    opp = None
    for p in game.players:
        if p is not player:
            opp = p
            break
    for i in range(4):
        if opp and opp.known[i] and opp.grid[i]:
            feats.extend(_rank_onehot(opp.grid[i].rank))
        else:
            feats.extend([0.0] * 13)

    arr = np.asarray(feats, dtype=np.float32)
    if arr.shape[0] != STATE_DIM:
        # Pad / trim defensively
        out = np.zeros(STATE_DIM, dtype=np.float32)
        n = min(STATE_DIM, arr.shape[0])
        out[:n] = arr[:n]
        return out
    return arr


def action_to_index(action: dict) -> int:
    if action["type"] == "take_discard":
        return int(action["position"])
    if action["type"] == "draw_deck" and action.get("keep", True):
        return 4 + int(action["position"])
    # draw discard + flip
    return 8 + int(action.get("flip_position", action.get("position", 0)))


def index_to_action(idx: int) -> dict:
    idx = int(idx)
    if 0 <= idx <= 3:
        return {"type": "take_discard", "position": idx}
    if 4 <= idx <= 7:
        return {"type": "draw_deck", "position": idx - 4, "keep": True}
    return {"type": "draw_deck", "keep": False, "flip_position": idx - 8}


def legal_action_mask(player, game) -> np.ndarray:
    """Bool mask over NUM_ACTIONS."""
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    available = [i for i, known in enumerate(player.known) if not known]
    if not available:
        return mask
    if game.discard_pile:
        for pos in available:
            mask[pos] = True
    if game.deck:
        for pos in available:
            mask[4 + pos] = True
            mask[8 + pos] = True
    return mask


def shaped_step_reward(action: dict, player, game, reward_shaping: dict) -> float:
    """Lightweight shaping without state_key parsing."""
    if not reward_shaping.get("enabled", True):
        return 0.0
    reward = float(reward_shaping.get("step", 0.05))
    hand_ranks = {
        c.rank
        for i, c in enumerate(player.grid)
        if c and (player.known[i] or player.privately_visible[i])
    }
    placed = None
    if action.get("type") == "take_discard" and game.discard_pile:
        # After action discard may already be moved — use last_action context if needed
        placed = None
    if action.get("type") == "draw_deck" and not action.get("keep", True):
        reward += float(reward_shaping.get("flip", 0.1))
    if placed and placed in hand_ranks:
        reward += float(reward_shaping.get("pair", 1.5))
    return reward


class QNetwork(nn.Module):
    def __init__(self, state_dim: int = STATE_DIM, hidden: int = 256, n_actions: int = NUM_ACTIONS):
        super().__init__()
        h2 = max(hidden // 2, 64)
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, h2),
            nn.ReLU(),
            nn.Linear(h2, n_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ReplayBuffer:
    def __init__(self, capacity: int = 100_000):
        self.buf: deque = deque(maxlen=capacity)

    def push(self, transition: tuple) -> None:
        self.buf.append(transition)

    def sample(self, batch_size: int):
        batch = random.sample(self.buf, min(batch_size, len(self.buf)))
        s, a, r, ns, d, m = zip(*batch)
        return (
            np.stack(s),
            np.asarray(a, dtype=np.int64),
            np.asarray(r, dtype=np.float32),
            np.stack(ns),
            np.asarray(d, dtype=np.float32),
            np.stack(m),
        )

    def __len__(self) -> int:
        return len(self.buf)


class DQNAgent:
    """Neural DQN agent compatible with GolfGame.choose_action interface."""

    def __init__(
        self,
        device: torch.device,
        learning_rate: float = 1e-3,
        discount_factor: float = 0.9,
        epsilon: float = 0.2,
        hidden_size: int = 256,
        n_bootstrap_games: int = 0,
        reward_shaping: dict | None = None,
    ):
        self.device = device
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.n_bootstrap_games = n_bootstrap_games
        self.games_played = 0
        self.training_mode = True
        self.reward_shaping = dict(reward_shaping or {"enabled": True, "step": 0.05, "flip": 0.1, "pair": 1.5})
        self.policy = QNetwork(hidden=hidden_size).to(device)
        self.target = QNetwork(hidden=hidden_size).to(device)
        self.target.load_state_dict(self.policy.state_dict())
        self.optimizer = torch.optim.Adam(self.policy.parameters(), lr=learning_rate)
        self.pending_transition: dict[str, Any] | None = None
        self.human_demo_policy = None
        # Fake q_table attrs so existing save paths don't explode
        self.q_table = {}
        self._use_amp = device.type == "cuda"
        self._scaler = torch.cuda.amp.GradScaler(enabled=self._use_amp) if device.type == "cuda" else None
        if device.type == "cuda":
            torch.backends.cudnn.benchmark = True
        # Lightweight encoder for human-demo state keys (same as recording path)
        self._state_encoder = QLearningAgent()

    def is_bootstrapping(self) -> bool:
        return self.n_bootstrap_games > 0 and self.games_played < self.n_bootstrap_games

    def param_count(self) -> int:
        return sum(p.numel() for p in self.policy.parameters())

    def get_q_table_size(self) -> tuple[int, int]:
        n = self.param_count()
        return n, n

    def decay_epsilon(self, factor: float = 0.995) -> None:
        self.epsilon = max(0.01, self.epsilon * factor)

    def notify_game_end(self) -> None:
        self.games_played += 1
        self.pending_transition = None

    @torch.no_grad()
    def _select_greedy(self, state_vec: np.ndarray, mask: np.ndarray) -> int:
        # Inference on GPU is fine; keep contiguous float32
        t = torch.from_numpy(np.ascontiguousarray(state_vec)).unsqueeze(0).to(self.device, non_blocking=True)
        q = self.policy(t).squeeze(0).detach().float().cpu().numpy()
        q = np.where(mask, q, -1e9)
        return int(np.argmax(q))

    def choose_action(self, player, game_state, trajectory=None):
        mask = legal_action_mask(player, game_state)
        if not mask.any():
            return None
        state_vec = encode_state(player, game_state)
        legal = [index_to_action(int(i)) for i in np.flatnonzero(mask)]

        if self.is_bootstrapping():
            action = None
            if self.human_demo_policy:
                try:
                    from human_bootstrap import choose_bootstrap_action

                    action, _tier = choose_bootstrap_action(
                        encoder=self._state_encoder,
                        policy=self.human_demo_policy,
                        player=player,
                        game_state=game_state,
                        legal_actions=legal,
                    )
                except Exception:
                    action = None
            if action is None:
                ev = EVAgent()
                action = ev.choose_action(player, game_state)
            # Map chosen action onto mask; fall back to random legal
            if action is None:
                idxs = np.flatnonzero(mask)
                idx = int(random.choice(idxs))
                action = index_to_action(idx)
            else:
                try:
                    idx = action_to_index(action)
                    if not mask[idx]:
                        idxs = np.flatnonzero(mask)
                        idx = int(random.choice(idxs))
                        action = index_to_action(idx)
                except Exception:
                    idxs = np.flatnonzero(mask)
                    idx = int(random.choice(idxs))
                    action = index_to_action(idx)
        elif self.training_mode and random.random() < self.epsilon:
            idxs = np.flatnonzero(mask)
            idx = int(random.choice(idxs))
            action = index_to_action(idx)
        else:
            idx = self._select_greedy(state_vec, mask)
            action = index_to_action(idx)

        idx = action_to_index(action)
        step_r = shaped_step_reward(action, player, game_state, self.reward_shaping)
        self.pending_transition = {
            "state": state_vec,
            "action": idx,
            "mask": mask.astype(np.float32),
            "reward": step_r,
        }
        if trajectory is not None:
            # Keep CSV-compatible keys for the viz (cheap — skip EV-based state keys)
            ak = f"{action['type']}_{action.get('position', action.get('flip_position', 0))}"
            if action.get("type") == "draw_deck" and not action.get("keep", True):
                ak = f"draw_deck_flip_{action.get('flip_position', 0)}"
            elif action.get("type") == "draw_deck":
                ak = f"draw_deck_{action.get('position', 0)}"
            sk = (
                f"dqn_r{getattr(game_state, 'round', 0)}"
                f"_k{sum(1 for x in player.known if x)}"
                f"_d{game_state.discard_pile[-1].rank if game_state.discard_pile else 'n'}"
            )
            trajectory.append({
                "state_key": sk,
                "action_key": ak,
                "action": action,
                "round": getattr(game_state, "round", None),
                "state_vec": state_vec,
                "action_idx": idx,
                "mask": mask.astype(np.float32),
            })
        return action

    def close_pending(self, next_state: np.ndarray | None, next_mask: np.ndarray | None, done: bool, extra_reward: float = 0.0):
        """Finalize pending transition into (s,a,r,ns,done,next_mask)."""
        if not self.pending_transition:
            return None
        pt = self.pending_transition
        ns = next_state if next_state is not None else pt["state"]
        nm = next_mask if next_mask is not None else np.zeros(NUM_ACTIONS, dtype=np.float32)
        return (
            pt["state"],
            pt["action"],
            float(pt["reward"] + extra_reward),
            ns,
            1.0 if done else 0.0,
            nm,
        )

    def optimize(self, buffer: ReplayBuffer, batch_size: int = 256) -> float | None:
        if len(buffer) < max(64, min(batch_size // 2, 256)):
            return None
        s, a, r, ns, d, nm = buffer.sample(batch_size)
        st = torch.as_tensor(s, device=self.device)
        at = torch.as_tensor(a, device=self.device)
        rt = torch.as_tensor(r, device=self.device)
        nst = torch.as_tensor(ns, device=self.device)
        dt = torch.as_tensor(d, device=self.device)
        nmt = torch.as_tensor(nm, device=self.device)

        with torch.cuda.amp.autocast(enabled=self._use_amp):
            q = self.policy(st).gather(1, at.unsqueeze(1)).squeeze(1)
            with torch.no_grad():
                next_q = self.target(nst)
                # float16 cannot hold -1e9 — use dtype-safe mask fill
                neg = torch.finfo(next_q.dtype).min / 2
                next_q = next_q.masked_fill(nmt < 0.5, neg)
                max_next = next_q.max(dim=1).values
                max_next = torch.where(torch.isfinite(max_next), max_next, torch.zeros_like(max_next))
                target = rt + (1.0 - dt) * self.discount_factor * max_next
            loss = F.smooth_l1_loss(q.float(), target.float())

        self.optimizer.zero_grad(set_to_none=True)
        if self._scaler is not None:
            self._scaler.scale(loss).backward()
            self._scaler.unscale_(self.optimizer)
            nn.utils.clip_grad_norm_(self.policy.parameters(), 5.0)
            self._scaler.step(self.optimizer)
            self._scaler.update()
        else:
            loss.backward()
            nn.utils.clip_grad_norm_(self.policy.parameters(), 5.0)
            self.optimizer.step()
        return float(loss.detach().float().item())

    def optimize_steps(self, buffer: ReplayBuffer, steps: int, batch_size: int = 256) -> float | None:
        """Run many GPU updates back-to-back (keeps the 3090 busy between CPU rollouts)."""
        last = None
        for i in range(max(0, int(steps))):
            loss = self.optimize(buffer, batch_size=batch_size)
            if loss is not None:
                last = loss
            if (i + 1) % 4 == 0:
                self.soft_update_target(tau=0.01)
        return last

    def soft_update_target(self, tau: float = 0.01) -> None:
        for tp, pp in zip(self.target.parameters(), self.policy.parameters()):
            tp.data.copy_(tau * pp.data + (1.0 - tau) * tp.data)

    def save(self, path: str | None = None) -> str:
        path = path or get_output_path("dqn_policy.pt")
        torch.save({
            "policy": self.policy.state_dict(),
            "target": self.target.state_dict(),
            "epsilon": self.epsilon,
            "games_played": self.games_played,
        }, path)
        print(f"Saved DQN weights to {path}")
        return path

    def load(self, path: str | None = None) -> bool:
        path = path or get_output_path("dqn_policy.pt")
        if not os.path.exists(path):
            return False
        try:
            ckpt = torch.load(path, map_location=self.device)
            self.policy.load_state_dict(ckpt["policy"])
            self.target.load_state_dict(ckpt.get("target", ckpt["policy"]))
        except Exception as e:
            # Architecture / size changes (e.g. deeper net) must not kill the run
            print(f"Skipping incompatible checkpoint {path}: {e}")
            return False
        self.epsilon = float(ckpt.get("epsilon", self.epsilon))
        self.games_played = int(ckpt.get("games_played", 0))
        print(f"Loaded DQN weights from {path}")
        return True


def _make_opponent(opponent_type: str):
    if opponent_type == "ev_ai":
        return EVAgent(), "ev_ai"
    if opponent_type == "random":
        return RandomAgent(), "random"
    if opponent_type == "advanced_ev":
        return AdvancedEVAgent(), "advanced_ev"
    raise ValueError(f"Unknown opponent_type: {opponent_type}")


def _terminal_reward(score: float, game_scores: list[float]) -> float:
    if score == min(game_scores) or score == 0:
        return 10.0
    if score <= 5:
        return 5.0
    if score <= 20:
        return -4.0
    return -10.0


def _counts_as_win(our_score: float, opp_score: float) -> bool:
    return our_score < opp_score or (our_score == 0 and opp_score == 0)


def _slim_trajectory(traj: list[dict]) -> list[dict]:
    """Keep only pickle-friendly arrays for worker → main handoff."""
    out: list[dict] = []
    for step in traj or []:
        s = step.get("state_vec")
        a = step.get("action_idx")
        if s is None or a is None:
            continue
        m = step.get("mask")
        out.append({
            "state_vec": np.asarray(s, dtype=np.float32),
            "action_idx": int(a),
            "mask": np.asarray(
                m if m is not None else np.ones(NUM_ACTIONS, dtype=np.float32),
                dtype=np.float32,
            ),
        })
    return out


def _push_traj_transitions(
    buffer: ReplayBuffer,
    traj: list[dict],
    scores: list[float],
    reward_shaping: dict,
    bootstrapping: bool,
) -> int:
    """Push TD (+ optional BC) transitions; return count added."""
    added = 0
    step_r = float(reward_shaping.get("step", 0.05)) if reward_shaping.get("enabled", True) else 0.0
    for i, step in enumerate(traj):
        s = step["state_vec"]
        a = int(step["action_idx"])
        m = step["mask"]
        r = step_r
        if i + 1 < len(traj):
            ns = traj[i + 1]["state_vec"]
            nm = traj[i + 1]["mask"]
            done = 0.0
        else:
            ns = s
            nm = np.zeros(NUM_ACTIONS, dtype=np.float32)
            done = 1.0
            r += _terminal_reward(scores[0], scores)
        buffer.push((s, a, r, ns, done, m))
        added += 1
    if bootstrapping and traj:
        for step in traj:
            buffer.push((
                step["state_vec"],
                int(step["action_idx"]),
                1.0,
                step["state_vec"],
                1.0,
                step["mask"],
            ))
            added += 1
    return added


_WORKER_AGENT: DQNAgent | None = None
_WORKER_HIDDEN: int | None = None


def _play_dqn_worker_game(payload: dict[str, Any]) -> dict[str, Any]:
    """Play one game in a worker with a frozen CPU policy snapshot."""
    global _WORKER_AGENT, _WORKER_HIDDEN
    import random as _random

    seed = payload.get("seed")
    if seed is not None:
        _random.seed(seed)
        np.random.seed(int(seed) % (2**32 - 1))

    hidden = int(payload["hidden_size"])
    reward_shaping = payload.get("reward_shaping") or {"enabled": True}
    if _WORKER_AGENT is None or _WORKER_HIDDEN != hidden:
        _WORKER_AGENT = DQNAgent(
            device=torch.device("cpu"),
            learning_rate=1e-3,
            discount_factor=float(payload.get("discount_factor", 0.9)),
            epsilon=float(payload["epsilon"]),
            hidden_size=hidden,
            n_bootstrap_games=int(payload["n_bootstrap_games"]),
            reward_shaping=reward_shaping,
        )
        _WORKER_AGENT._use_amp = False
        _WORKER_AGENT._scaler = None
        _WORKER_HIDDEN = hidden

    agent = _WORKER_AGENT
    agent.reward_shaping = dict(reward_shaping)
    agent.n_bootstrap_games = int(payload["n_bootstrap_games"])
    agent.epsilon = float(payload["epsilon"])
    agent.games_played = int(payload["games_played"])
    agent.training_mode = True
    agent.pending_transition = None
    try:
        from human_bootstrap import HumanDemoPolicy

        agent.human_demo_policy = HumanDemoPolicy.from_payload(payload.get("human_demo_policy"))
    except Exception:
        agent.human_demo_policy = None
    # Skip weight reload while bootstrapping (EV/human choose actions; net unused)
    if not agent.is_bootstrapping():
        agent.policy.load_state_dict(payload["policy_state"])
        agent.policy.eval()

    opponent, opp_type = _make_opponent(payload["opponent_type"])
    agents = [agent, opponent]
    traj: list[dict] = []
    game = GolfGame(num_players=2, agent_types=["dqn", opp_type], q_agents=agents)
    game.agents = agents
    scores = game.play_game(verbose=False, trajectories=[traj, None])
    return {
        "trajectory": _slim_trajectory(traj),
        "scores": [float(scores[0]), float(scores[1])],
        "bootstrapping": bool(agent.is_bootstrapping()),
    }


def _gpu_train_steps(train_steps_per_game: int, n_transitions: int, batch_size: int) -> int:
    """One short GPU burst per parallel round — throughput over util cosplay."""
    raw = max(int(train_steps_per_game), int(n_transitions) // max(1, int(batch_size)))
    return int(min(32, max(8, raw)))


def train_dqn_agent(
    num_games: int = 5000,
    opponent_type: str = "ev_ai",
    verbose: bool = True,
    use_gpu: bool = True,
    learning_rate: float = 1e-3,
    discount_factor: float = 0.9,
    epsilon: float = 0.2,
    epsilon_decay_factor: float = 0.995,
    n_bootstrap_games: int = 500,
    use_imitation_learning: bool = True,
    epsilon_decay_interval: int = 100,
    progress_report_interval: int = 250,
    batch_size: int = 512,
    hidden_size: int = 256,
    train_steps_per_game: int = 16,
    num_workers: int | None = None,
    chunk_size: int | None = None,
    target_tau: float = 0.01,
    use_reward_shaping: bool = True,
    shape_step: float = 0.05,
    shape_pair: float = 1.5,
    shape_high_keep: float = -0.8,
    shape_low_keep: float = 0.3,
    shape_midhigh_keep: float = -0.4,
    shape_flip: float = 0.1,
    **_extra,
) -> tuple[DQNAgent, dict[str, Any]]:
    device = get_device(prefer_gpu=use_gpu)
    bootstrap_n = n_bootstrap_games if use_imitation_learning else 0
    reward_shaping = {
        "enabled": bool(use_reward_shaping),
        "step": float(shape_step),
        "pair": float(shape_pair),
        "high_keep": float(shape_high_keep),
        "low_keep": float(shape_low_keep),
        "midhigh_keep": float(shape_midhigh_keep),
        "flip": float(shape_flip),
    }

    cpu_n = os.cpu_count() or 4
    if num_workers is None or int(num_workers) <= 0:
        # Prefer a small pool for games/hour; huge pods (64 vCPU) thrash if we use all of them
        num_workers = min(8, max(2, cpu_n))
    num_workers = max(1, min(int(num_workers), cpu_n))
    if chunk_size is None or int(chunk_size) <= 0:
        chunk_size = max(num_workers, num_workers * 2)
    chunk_size = max(1, int(chunk_size))

    train_steps_per_game = max(4, int(train_steps_per_game))
    batch_size = max(32, int(batch_size))
    hidden_size = max(32, int(hidden_size))
    # Throughput floors — do NOT force huge GPU taxes
    if device.type == "cuda":
        train_steps_per_game = max(train_steps_per_game, 8)

    print("=" * 70)
    print("NEURAL DQN TRAINING (PARALLEL ROLLOUTS + GPU UPDATES)")
    print("=" * 70)
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Workers: {num_workers} (cpu_count={cpu_n}) chunk={chunk_size}")
    print(f"State dim={STATE_DIM} actions={NUM_ACTIONS} hidden={hidden_size} batch={batch_size}")
    print(f"Train steps/round~{train_steps_per_game} (clamped 8-32 from transitions)")
    print(f"Games={num_games} bootstrap={bootstrap_n} opponent={opponent_type}")

    try:
        from human_bootstrap import load_human_demo_policy

        human_demo_policy = load_human_demo_policy(refresh=True)
    except Exception as e:
        print(f"Human demo policy unavailable: {e}")
        from human_bootstrap import HumanDemoPolicy

        human_demo_policy = HumanDemoPolicy()
    human_payload = human_demo_policy.to_payload() if human_demo_policy else {}
    if human_demo_policy:
        print(
            f"Human demos: {human_demo_policy.steps} weighted steps / "
            f"{human_demo_policy.holes} holes "
            f"({len(human_demo_policy.exact)} exact keys, source={human_demo_policy.source})"
        )
    else:
        print("Human demos: none — bootstrap will use EV only")

    agent = DQNAgent(
        device=device,
        learning_rate=learning_rate,
        discount_factor=discount_factor,
        epsilon=epsilon,
        hidden_size=hidden_size,
        n_bootstrap_games=bootstrap_n,
        reward_shaping=reward_shaping,
    )
    agent.human_demo_policy = human_demo_policy
    agent.load()
    buffer = ReplayBuffer(250_000)

    training_stats: dict[str, Any] = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "scores": [],
        "opponent_scores": [],
        "qtable_states": [],
        "qtable_entries": [],
        "epsilon_values": [],
        "training_times": [],
        "loss_values": [],
        "buffer_sizes": [],
        "train_device": "gpu" if device.type != "cpu" else "cpu",
        "train_mode": "dqn_parallel",
        "num_workers": num_workers,
    }

    with open(get_output_path("training_progress.json"), "w", encoding="utf-8") as f:
        json.dump({
            "ok": True, "running": True, "checkpoints": [],
            "train_mode": "dqn_parallel",
            "train_device": training_stats["train_device"],
            "series": {
                "games": [], "avg_scores": [], "qtable_states": [],
                "epsilon": [], "win_rates": [], "losses": [], "buffer_sizes": [],
            },
            "summary": {},
        }, f)

    t0 = time.time()
    last_loss = None
    games_done = 0

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        while games_done < num_games:
            batch_n = min(chunk_size, num_games - games_done)
            # Avoid shipping weights while EV bootstrap ignores the net
            if agent.games_played < bootstrap_n:
                policy_state: dict[str, Any] = {}
            else:
                policy_state = {k: v.detach().cpu() for k, v in agent.policy.state_dict().items()}
            payloads = []
            for i in range(batch_n):
                payloads.append({
                    "policy_state": policy_state,
                    "epsilon": agent.epsilon,
                    "hidden_size": hidden_size,
                    "n_bootstrap_games": bootstrap_n,
                    "games_played": agent.games_played,
                    "discount_factor": discount_factor,
                    "opponent_type": opponent_type,
                    "reward_shaping": reward_shaping,
                    "human_demo_policy": human_payload,
                    "seed": int(time.time() * 1000) % 1_000_000_007 + games_done + i,
                })

            batch_start = time.time()
            futures = [pool.submit(_play_dqn_worker_game, p) for p in payloads]
            results = [fut.result() for fut in as_completed(futures)]

            n_transitions = 0
            for result in results:
                traj = result["trajectory"]
                scores = result["scores"]
                games_done += 1
                agent.games_played = games_done

                n_transitions += _push_traj_transitions(
                    buffer,
                    traj,
                    scores,
                    reward_shaping,
                    bootstrapping=bool(result.get("bootstrapping")),
                )

                won = _counts_as_win(scores[0], scores[1])
                tied = (scores[0] == scores[1]) and not won
                if won:
                    training_stats["wins"] += 1
                elif not tied:
                    training_stats["losses"] += 1

                training_stats["games_played"] = games_done
                training_stats["scores"].append(float(scores[0]))
                training_stats["opponent_scores"].append(float(scores[1]))
                states, entries = agent.get_q_table_size()
                training_stats["qtable_states"].append(states)
                training_stats["qtable_entries"].append(entries)
                training_stats["epsilon_values"].append(agent.epsilon)
                training_stats["training_times"].append((time.time() - batch_start) / max(1, batch_n))

                if epsilon_decay_interval and games_done % epsilon_decay_interval == 0:
                    agent.decay_epsilon(factor=epsilon_decay_factor)

            steps = _gpu_train_steps(train_steps_per_game, n_transitions, batch_size)
            last_loss = agent.optimize_steps(buffer, steps, batch_size=batch_size)
            agent.soft_update_target(tau=target_tau)

            for _ in range(batch_n):
                training_stats["loss_values"].append(None if last_loss is None else float(last_loss))
                training_stats["buffer_sizes"].append(len(buffer))

            if verbose and (
                games_done % progress_report_interval < batch_n
                or games_done >= num_games
            ):
                win_rate = training_stats["wins"] / max(1, games_done)
                avg_score = float(np.mean(training_stats["scores"]))
                states, _ = agent.get_q_table_size()
                phase = "BOOTSTRAP" if games_done < bootstrap_n else "DQN"
                gps = games_done / max(1e-6, time.time() - t0)
                training_stats["total_time"] = float(time.time() - t0)
                training_stats["games_per_sec"] = float(gps)
                loss_s = f"{last_loss:.4f}" if last_loss is not None else "n/a"
                print(
                    f"  Game {games_done}: {phase} | Win rate={win_rate:.2%}, "
                    f"Avg score={avg_score:.2f}, States={states}, Epsilon={agent.epsilon:.3f}, "
                    f"loss={loss_s}, buffer={len(buffer)}, steps={steps}, "
                    f"{gps:.1f} games/s, workers={num_workers}, device={device}"
                )
                save_training_stats_json(training_stats)
                append_progress_checkpoint(
                    game=games_done,
                    games_total=num_games,
                    phase=phase,
                    win_rate=win_rate,
                    avg_score=avg_score,
                    states=states,
                    epsilon=agent.epsilon,
                    loss=last_loss,
                    buffer_size=len(buffer),
                    train_mode="dqn_parallel",
                    train_device=training_stats["train_device"],
                )
                if games_done >= num_games or games_done % max(progress_report_interval * 4, 500) < batch_n:
                    agent.save()

    win_rate = training_stats["wins"] / max(1, num_games)
    avg_score = float(np.mean(training_stats["scores"])) if training_stats["scores"] else 0.0
    total_time = time.time() - t0
    training_stats["total_time"] = float(total_time)
    training_stats["games_per_sec"] = float(num_games / max(1e-6, total_time))
    print("\nDQN TRAINING COMPLETE")
    print(f"  Device: {device}")
    print(f"  Workers: {num_workers}")
    print(f"  Win rate: {win_rate:.2%}")
    print(f"  Avg score: {avg_score:.2f}")
    print(f"  Time: {total_time:.1f}s ({training_stats['games_per_sec']:.1f} games/s)")
    agent.save()
    save_training_stats_json(training_stats)
    append_progress_checkpoint(
        game=num_games,
        games_total=num_games,
        phase="DONE",
        win_rate=win_rate,
        avg_score=avg_score,
        states=agent.param_count(),
        epsilon=agent.epsilon,
        loss=last_loss,
        buffer_size=len(buffer),
        train_mode="dqn_parallel",
        train_device=training_stats["train_device"],
    )
    mark_progress_complete()

    with open(get_output_path("last_run_params.json"), "w", encoding="utf-8") as f:
        json.dump({
            "num_games": num_games,
            "train_device": "gpu" if device.type != "cpu" else "cpu",
            "train_mode": "dqn_parallel",
            "opponent_type": opponent_type,
            "learning_rate": learning_rate,
            "discount_factor": discount_factor,
            "epsilon": epsilon,
            "batch_size": batch_size,
            "hidden_size": hidden_size,
            "train_steps_per_game": train_steps_per_game,
            "num_workers": num_workers,
            "n_bootstrap_games": bootstrap_n,
            "use_imitation_learning": use_imitation_learning,
        }, f, indent=2)

    return agent, training_stats


def _params_from_args() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Neural DQN trainer")
    parser.add_argument("--games", type=int, default=None)
    parser.add_argument("--params-json", type=str, default=None)
    parser.add_argument("--cpu", action="store_true", help="Force CPU even if CUDA exists")
    args = parser.parse_args()
    params: dict[str, Any] = {}
    ui = args.params_json or get_output_path("ui_train_params.json")
    if os.path.exists(ui):
        with open(ui, encoding="utf-8") as f:
            params.update(json.load(f))
    if args.games is not None:
        params["num_games"] = args.games
    if args.cpu:
        params["use_gpu"] = False
    if os.environ.get("NUM_GAMES"):
        params["num_games"] = int(os.environ["NUM_GAMES"])
    if os.environ.get("USE_GPU", "1") == "0":
        params["use_gpu"] = False
    return params


if __name__ == "__main__":
    try:
        p = _params_from_args()
        # DQN prefers a slightly higher LR than tabular 0.1
        lr = float(p.get("learning_rate", 0.001))
        if lr >= 0.05:
            lr = 0.001
        train_dqn_agent(
            num_games=int(p.get("num_games", 5000)),
            opponent_type=str(p.get("opponent_type", "ev_ai")),
            verbose=True,
            use_gpu=bool(p.get("use_gpu", True)),
            learning_rate=lr,
            discount_factor=float(p.get("discount_factor", 0.9)),
            epsilon=float(p.get("epsilon", 0.2)),
            epsilon_decay_factor=float(p.get("epsilon_decay_factor", 0.995)),
            n_bootstrap_games=int(p.get("n_bootstrap_games", 500)),
            use_imitation_learning=bool(p.get("use_imitation_learning", True)),
            epsilon_decay_interval=int(p.get("epsilon_decay_interval", 100)),
            progress_report_interval=int(p.get("progress_report_interval", 250)),
            batch_size=int(p.get("batch_size", 512)),
            hidden_size=int(p.get("hidden_size", 256)),
            train_steps_per_game=int(p.get("train_steps_per_game", 16)),
            num_workers=int(p.get("num_workers", 0) or 0) or None,
            use_reward_shaping=bool(p.get("use_reward_shaping", True)),
            shape_step=float(p.get("shape_step", 0.05)),
            shape_pair=float(p.get("shape_pair", 1.5)),
            shape_high_keep=float(p.get("shape_high_keep", -0.8)),
            shape_low_keep=float(p.get("shape_low_keep", 0.3)),
            shape_midhigh_keep=float(p.get("shape_midhigh_keep", -0.4)),
            shape_flip=float(p.get("shape_flip", 0.1)),
        )
    finally:
        try:
            pid_path = get_output_path("local_train.pid")
            if os.path.exists(pid_path):
                os.remove(pid_path)
        except OSError:
            pass
