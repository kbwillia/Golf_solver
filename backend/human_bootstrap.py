"""
Human-demo bootstrap policy for RL training.

During imitation/bootstrap, prefer a recorded human (state_key → action_key)
when the live state matches exactly or closely; otherwise fall back to EV.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_CACHE_PATH = os.path.join(_BACKEND_DIR, "RL", "output", "human_demos_bootstrap.json")

_STATE_RE_NEW = re.compile(
    r"^pub_(?P<pub>.*)_priv_(?P<priv>.*)"
    r"_dis_(?P<dis>[^_]+)_drawn_(?P<drawn>[^_]+)_round_(?P<round>\d+)$"
)
# Legacy keys included an EV advantage bucket between priv and dis
_STATE_RE_OLD = re.compile(
    r"^pub_(?P<pub>.*)_priv_(?P<priv>.*)_adv_(?P<adv>-?\d+(?:\.\d+)?)"
    r"_dis_(?P<dis>[^_]+)_drawn_(?P<drawn>[^_]+)_round_(?P<round>\d+)$"
)
_ADV_STRIP_RE = re.compile(r"_adv_-?\d+(?:\.\d+)?")


def strip_adv_from_state_key(state_key: str) -> str:
    """Normalize legacy keys that embedded EV advantage buckets."""
    return _ADV_STRIP_RE.sub("", state_key or "")


def action_key_of(action: dict) -> str:
    if action.get("type") == "draw_deck" and not action.get("keep", True):
        return f"draw_deck_flip_{action.get('flip_position', 0)}"
    return f"{action.get('type')}_{action.get('position', 0)}"


def parse_state_key(state_key: str) -> dict[str, str] | None:
    sk = state_key or ""
    m = _STATE_RE_NEW.match(sk) or _STATE_RE_OLD.match(sk)
    return m.groupdict() if m else None


def core_key_from_parts(parts: dict[str, str]) -> str:
    """Ignore adv bucket + round — same visible cards / discard / drawn."""
    return f"pub_{parts['pub']}_priv_{parts['priv']}_dis_{parts['dis']}_drawn_{parts['drawn']}"


def board_key_from_parts(parts: dict[str, str]) -> str:
    """Ignore drawn + adv + round — same hand face-up/private vs discard."""
    return f"pub_{parts['pub']}_priv_{parts['priv']}_dis_{parts['dis']}"


def match_action_key(action_key: str, legal_actions: list[dict]) -> dict | None:
    if not action_key or not legal_actions:
        return None
    for a in legal_actions:
        if action_key_of(a) == action_key:
            return a
    return None


@dataclass
class HumanDemoPolicy:
    exact: dict[str, str] = field(default_factory=dict)
    close_core: dict[str, str] = field(default_factory=dict)
    close_board: dict[str, str] = field(default_factory=dict)
    steps: int = 0
    holes: int = 0
    source: str = "empty"

    def __bool__(self) -> bool:
        return bool(self.exact or self.close_core or self.close_board)

    def to_payload(self) -> dict[str, Any]:
        return {
            "exact": self.exact,
            "close_core": self.close_core,
            "close_board": self.close_board,
            "steps": self.steps,
            "holes": self.holes,
            "source": self.source,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "HumanDemoPolicy":
        if not payload:
            return cls()
        return cls(
            exact=dict(payload.get("exact") or {}),
            close_core=dict(payload.get("close_core") or {}),
            close_board=dict(payload.get("close_board") or {}),
            steps=int(payload.get("steps") or 0),
            holes=int(payload.get("holes") or 0),
            source=str(payload.get("source") or "payload"),
        )

    def lookup_action_key(self, state_key: str) -> tuple[str | None, str]:
        """
        Return (action_key, match_tier).
        Tiers: exact | close_core | close_board | none
        """
        if not state_key:
            return None, "none"
        if state_key in self.exact:
            return self.exact[state_key], "exact"
        parts = parse_state_key(state_key)
        if not parts:
            return None, "none"
        ck = core_key_from_parts(parts)
        if ck in self.close_core:
            return self.close_core[ck], "close_core"
        bk = board_key_from_parts(parts)
        if bk in self.close_board:
            return self.close_board[bk], "close_board"
        return None, "none"

    def choose(
        self,
        state_key: str,
        legal_actions: list[dict],
    ) -> tuple[dict | None, str]:
        """Map a state to a legal human action, or (None, tier)."""
        ak, tier = self.lookup_action_key(state_key)
        if not ak:
            return None, tier
        action = match_action_key(ak, legal_actions)
        if action is None:
            return None, "illegal"
        return action, tier


def _vote(counters: dict[str, Counter]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, ctr in counters.items():
        if ctr:
            out[key] = ctr.most_common(1)[0][0]
    return out


def build_policy_from_rows(rows: list[dict[str, Any]], *, source: str = "rows") -> HumanDemoPolicy:
    exact_ctr: dict[str, Counter] = defaultdict(Counter)
    core_ctr: dict[str, Counter] = defaultdict(Counter)
    board_ctr: dict[str, Counter] = defaultdict(Counter)
    holes: set[tuple[Any, Any]] = set()

    for r in rows:
        gid = r.get("game_id") or ""
        if gid == "test_probe":
            continue
        sk = r.get("state_key")
        ak = r.get("action_key")
        if not sk or not ak or not isinstance(ak, str):
            continue
        if "_" not in ak or ak in ("ak", "action_key"):
            continue
        weight = 2 if r.get("won") is True else 1
        exact_ctr[sk][ak] += weight
        # Also index stripped key so live play (no adv_) still exact-matches old demos
        sk_norm = strip_adv_from_state_key(sk)
        if sk_norm != sk:
            exact_ctr[sk_norm][ak] += weight
        parts = parse_state_key(sk)
        if parts:
            core_ctr[core_key_from_parts(parts)][ak] += weight
            board_ctr[board_key_from_parts(parts)][ak] += weight
        holes.add((gid, r.get("hole_num")))
    return HumanDemoPolicy(
        exact=_vote(exact_ctr),
        close_core=_vote(core_ctr),
        close_board=_vote(board_ctr),
        steps=sum(sum(c.values()) for c in exact_ctr.values()),
        holes=len(holes),
        source=source,
    )


def save_policy_cache(policy: HumanDemoPolicy, path: str | None = None) -> str:
    path = path or _CACHE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(policy.to_payload(), f, indent=2)
    return path


def load_policy_cache(path: str | None = None) -> HumanDemoPolicy | None:
    path = path or _CACHE_PATH
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        policy = HumanDemoPolicy.from_payload(data)
        policy.source = f"cache:{os.path.basename(path)}"
        return policy if policy else None
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def fetch_human_demo_rows() -> list[dict[str, Any]]:
    """Pull demo rows from Supabase (finished preferred, but any keyed step works)."""
    from data_upset import fetch_human_demo_bootstrap_rows

    return fetch_human_demo_bootstrap_rows()


def load_human_demo_policy(*, refresh: bool = True) -> HumanDemoPolicy:
    """
    Load human demos for bootstrap.
    Prefer a fresh Supabase pull (and refresh local cache); fall back to cache
    (needed on RunPod where Supabase is stubbed).
    """
    if refresh:
        try:
            rows = fetch_human_demo_rows()
            if rows:
                policy = build_policy_from_rows(rows, source="supabase")
                try:
                    save_policy_cache(policy)
                except OSError as e:
                    print(f"Human demo cache write skipped: {e}")
                return policy
        except Exception as e:
            print(f"Human demo Supabase load failed (will try cache): {e}")

    cached = load_policy_cache()
    if cached:
        return cached
    return HumanDemoPolicy(source="empty")


def choose_bootstrap_action(
    *,
    encoder,
    policy: HumanDemoPolicy | None,
    player,
    game_state,
    legal_actions: list[dict],
) -> tuple[dict | None, str]:
    """
    Try human demo (exact/close), including a draw-peek state that mirrors
    how demos were recorded for draw_deck decisions. Returns (action, tier).
    """
    if not policy or not legal_actions:
        return None, "none"

    state_key = encoder.get_state_key(player, game_state)
    action, tier = policy.choose(state_key, legal_actions)
    if action is not None:
        return action, tier

    # Mirror human recording: peek deck top into drawn_card for draw decisions
    if getattr(game_state, "deck", None) and getattr(game_state, "drawn_card", None) is None:
        prev = game_state.drawn_card
        try:
            game_state.drawn_card = game_state.deck[-1]
            peeked_key = encoder.get_state_key(player, game_state)
            action, tier = policy.choose(peeked_key, legal_actions)
            if action is not None and action.get("type") == "draw_deck":
                return action, f"peek_{tier}"
        finally:
            game_state.drawn_card = prev

    return None, "none"
