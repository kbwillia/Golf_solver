from supabase import create_client, Client
import os
import re
from datetime import datetime
import uuid
from supabase import create_client, Client
from datetime import datetime

from dotenv import load_dotenv

# Load project-root .env even when launched from backend/
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)
load_dotenv(os.path.join(_ROOT_DIR, ".env"))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))  # optional backend override

url = os.getenv("SUPABASE_URL")
# Try legacy secret first, fall back to public key
key = os.getenv("SUPABASE_LEGACY_SECRET") or os.getenv("SUPABASE_PUBLIC") or os.getenv("SUPBAASE_PUBLIC")
if not key:
    raise ValueError("No Supabase API key found. Please set SUPABASE_LEGACY_SECRET or SUPABASE_PUBLIC in .env")
if not url:
    raise ValueError("No Supabase URL found. Please set SUPABASE_URL in .env")
supabase: Client = create_client(url, key)
# print(f'url: {url}')
# print(f'key: {key}')

def upload_chatbot_message(game_id, user_id, bot_name, message, sender, media=None, metadata=None):
    data = {
        "game_id": game_id,
        "user_id": user_id,
        "bot_name": bot_name,
        "message": message,
        "sender": sender,
        "timestamp": datetime.utcnow().isoformat(),
        "media": media or {},
        "metadata": metadata or {}
    }
    response = supabase.table("chatbot_messages").insert(data).execute()
    return response


def upload_llm_call_info(
    llm_call_id,
    model,
    prompt,
    response_text=None,
    prompt_tokens=None,
    completion_tokens=None,
    total_tokens=None,
    temperature=None,
    max_tokens=None,
    stream=False,
    success=True,
    error_message=None,
    response_time_ms=None,
    game_id=None,
    bot_name=None,
    user_id=None,
    endpoint=None,
    api_version=None,
    metadata=None
):
    """
    Upload detailed LLM call information for tracking usage, performance, and debugging.

    """
    data = {
        "llm_call_id": llm_call_id,
        "model": model,
        "prompt": prompt,
        "response_text": response_text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
        "success": success,
        "error_message": error_message,
        "response_time_ms": response_time_ms,
        "game_id": game_id,
        "bot_name": bot_name,
        "user_id": user_id,
        "endpoint": endpoint,
        "api_version": api_version,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }

    try:
        response = supabase.table("llm_calls").insert(data).execute()
        return response
    except Exception as e:
        print(f"Error uploading LLM call info: {e}")
        return None


def generate_llm_call_id():
    """Generate a unique LLM call ID"""
    return str(uuid.uuid4())


def get_llm_usage_analytics(start_date=None, end_date=None, model=None, bot_name=None):
    """
    Get analytics about LLM usage for monitoring and optimization.

    Args:
        start_date: Start date for analytics (ISO format)
        end_date: End date for analytics (ISO format)
        model: Filter by specific model
        bot_name: Filter by specific bot

    Returns:
        Dict with usage statistics
    """
    try:
        query = supabase.table("llm_calls").select("*")

        # Add filters
        if start_date:
            query = query.gte("timestamp", start_date)
        if end_date:
            query = query.lte("timestamp", end_date)
        if model:
            query = query.eq("model", model)
        if bot_name:
            query = query.eq("bot_name", bot_name)

        response = query.execute()
        calls = response.data

        if not calls:
            return {"total_calls": 0, "total_tokens": 0}

        # Calculate analytics
        total_calls = len(calls)
        successful_calls = len([c for c in calls if c.get("success", True)])
        failed_calls = total_calls - successful_calls

        total_tokens = sum(c.get("total_tokens", 0) for c in calls if c.get("total_tokens"))
        total_prompt_tokens = sum(c.get("prompt_tokens", 0) for c in calls if c.get("prompt_tokens"))
        total_completion_tokens = sum(c.get("completion_tokens", 0) for c in calls if c.get("completion_tokens"))

        # Average response time
        response_times = [c.get("response_time_ms") for c in calls if c.get("response_time_ms")]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Token efficiency
        avg_tokens_per_call = total_tokens / total_calls if total_calls > 0 else 0

        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "avg_tokens_per_call": avg_tokens_per_call,
            "avg_response_time_ms": avg_response_time,
            "date_range": {"start": start_date, "end": end_date},
            "filters": {"model": model, "bot_name": bot_name}
        }

    except Exception as e:
        print(f"Error getting LLM analytics: {e}")
        return None


def get_recent_llm_calls(limit=10, model=None, success_only=False):
    """
    Get recent LLM calls for debugging and monitoring.

    Args:
        limit: Number of recent calls to retrieve
        model: Filter by specific model
        success_only: Only return successful calls

    Returns:
        List of recent LLM calls
    """
    try:
        query = supabase.table("llm_calls").select("*").order("timestamp", desc=True).limit(limit)

        if model:
            query = query.eq("model", model)
        if success_only:
            query = query.eq("success", True)

        response = query.execute()
        return response.data

    except Exception as e:
        print(f"Error getting recent LLM calls: {e}")
        return None


def save_bot_to_supabase(bot):
    """Unpacks the bot class and attributes and saves to Supabase."""
    import json

    bot_data = {
        'ai_bot_id': bot.ai_bot_id,
        'name': bot.name,
        'difficulty': bot.difficulty,
        'description': bot.description,
        'emotional_state': json.dumps(bot.emotional_state),
        'proactive_config': json.dumps(bot.proactive_config),
        'response_config': json.dumps(bot.response_config),
        'gif_config': json.dumps(bot.gif_config)
    }
    if bot.image_path:
        bot_data['image_path'] = bot.image_path
    if bot.voice_id:
        bot_data['voice_id'] = bot.voice_id
    print(f"🔧 CUSTOM BOT: Saving bot to supabase:")

    response = supabase.table('custom_bots').insert(bot_data).execute()
    # if response.model_dump() possibly add error handling
    return response


def upload_human_demo(
    game_id,
    player_name,
    hole_num,
    round_num,
    state_key,
    action_key,
    action,
):
    """Insert one opt-in human demonstration step for RL bootstrap."""
    data = {
        "game_id": game_id,
        "player_name": player_name,
        "hole_num": hole_num,
        "round_num": round_num,
        "state_key": state_key,
        "action_key": action_key,
        "action": action,
        "game_finished": False,
    }
    response = supabase.table("human_demos").insert(data).execute()
    return response


def finalize_human_demos(game_id, hole_num, human_score, opponent_scores, won):
    """Mark all demo steps for a finished hole with outcome scores."""
    response = (
        supabase.table("human_demos")
        .update(
            {
                "human_score": human_score,
                "opponent_scores": opponent_scores,
                "won": won,
                "game_finished": True,
            }
        )
        .eq("game_id", game_id)
        .eq("hole_num", hole_num)
        .eq("game_finished", False)
        .execute()
    )
    return response


def fetch_human_demo_bootstrap_rows():
    """
    Rows for RL bootstrap lookup (state_key → action_key).
    Prefer finished holes; still include unfinished steps that have keys.
    """
    response = (
        supabase.table("human_demos")
        .select("game_id,hole_num,state_key,action_key,action,won,game_finished,human_score")
        .neq("game_id", "test_probe")
        .execute()
    )
    return list(response.data or [])


def fetch_human_demo_score_summary():
    """
    Hole-level human demo outcomes for the RL page (score histogram + summary)
    plus per-round action-type averages.
    """
    try:
        response = (
            supabase.table("human_demos")
            .select(
                "game_id,hole_num,human_score,won,player_name,created_at,"
                "round_num,action,action_key,state_key,game_finished"
            )
            .neq("game_id", "test_probe")
            .execute()
        )
        rows = response.data or []
    except Exception as e:
        print(f"Error fetching human demos: {e}")
        return {"available": False, "error": str(e), "used_in_bootstrap": False}

    holes = {}
    action_rows = []
    for r in rows:
        gid = r.get("game_id") or ""
        if gid == "test_probe":
            continue
        if r.get("game_finished") and r.get("human_score") is not None:
            key = (gid, r.get("hole_num"))
            if key not in holes:
                holes[key] = r
        if r.get("action") is not None or r.get("action_key"):
            action_rows.append(r)

    action_by_round = _human_action_by_round(action_rows)
    action_by_board = _human_action_by_board(action_rows)

    if not holes:
        return {
            "available": bool(
                action_by_round.get("available") or action_by_board.get("available")
            ),
            "used_in_bootstrap": True,
            "holes": 0,
            "steps": len(action_rows),
            "message": (
                None
                if action_by_round.get("available") or action_by_board.get("available")
                else "No finished human demo holes yet."
            ),
            "action_by_round": action_by_round,
            "action_by_board": action_by_board,
        }

    scores = [int(h["human_score"]) for h in holes.values() if h.get("human_score") is not None]
    wins = sum(1 for h in holes.values() if h.get("won") is True)
    n = len(scores)
    max_score = max(0, max(scores) if scores else 0)
    counts = [0] * (max_score + 1)
    for s in scores:
        if 0 <= s <= max_score:
            counts[s] += 1

    return {
        "available": True,
        "used_in_bootstrap": True,
        "holes": n,
        "steps": len(action_rows),
        "wins": wins,
        "win_rate": (wins / n) if n else None,
        "avg_score": (sum(scores) / n) if n else None,
        "best_score": min(scores) if scores else None,
        "worst_score": max(scores) if scores else None,
        "score_histogram": {
            "available": True,
            "bin_centers": list(range(0, max_score + 1)),
            "counts": counts,
            "min_score": 0,
            "max_score": max_score,
        },
        "action_by_round": action_by_round,
        "action_by_board": action_by_board,
    }


def _classify_human_action(action_raw, action_key=None) -> str:
    """Map a stored demo action to take_discard / draw_keep / draw_flip."""
    if isinstance(action_raw, dict):
        typ = action_raw.get("type")
        if typ == "take_discard":
            return "take_discard"
        if typ == "draw_deck":
            if action_raw.get("keep") is True:
                return "draw_keep"
            return "draw_flip"
        if typ == "draw_flip":
            return "draw_flip"
    key = str(action_key or "")
    if "take_discard" in key:
        return "take_discard"
    if "flip" in key:
        return "draw_flip"
    if "draw_deck" in key or "draw" in key:
        return "draw_keep"
    if isinstance(action_raw, str):
        low = action_raw.lower()
        if "take_discard" in low:
            return "take_discard"
        if "draw" in low:
            if "keep': true" in low or '"keep": true' in low or "keep\": true" in low:
                return "draw_keep"
            if "flip" in low or "keep': false" in low or '"keep": false' in low:
                return "draw_flip"
            return "draw_keep"
    return "unknown"


def _human_action_by_round(rows: list) -> dict:
    """Average action-type mix per round_num across human demo steps."""
    types = ("take_discard", "draw_keep", "draw_flip")
    # round -> type -> count
    by_round: dict[int, dict[str, int]] = {}
    # hole -> type -> count (for overall avg per hole)
    by_hole: dict[tuple, dict[str, int]] = {}
    unknown = 0

    for r in rows:
        rn = r.get("round_num")
        try:
            rn = int(rn)
        except (TypeError, ValueError):
            continue
        if rn < 0:
            continue
        at = _classify_human_action(r.get("action"), r.get("action_key"))
        if at not in types:
            unknown += 1
            continue
        by_round.setdefault(rn, {t: 0 for t in types})
        by_round[rn][at] += 1
        hkey = (r.get("game_id") or "", r.get("hole_num"))
        by_hole.setdefault(hkey, {t: 0 for t in types})
        by_hole[hkey][at] += 1

    if not by_round:
        return {"available": False, "types": list(types), "rounds": []}

    rounds = sorted(by_round.keys())
    totals = {rn: sum(by_round[rn].values()) for rn in rounds}
    share = {t: [] for t in types}
    avg_counts = {t: [] for t in types}
    # holes that played at least one action in that round ≈ total actions that round
    # (1 human action / round typically) — avg count of type = count / n_actions_in_round
    for rn in rounds:
        tot = max(1, totals[rn])
        for t in types:
            c = by_round[rn][t]
            share[t].append(round(c / tot, 4))
            avg_counts[t].append(round(c / tot, 4))  # same when 1 action/round

    n_holes = max(1, len(by_hole))
    overall_avg_per_hole = {
        t: round(sum(h.get(t, 0) for h in by_hole.values()) / n_holes, 3)
        for t in types
    }

    return {
        "available": True,
        "types": list(types),
        "rounds": rounds,
        "share": share,
        "avg_counts": avg_counts,
        "overall_avg_per_hole": overall_avg_per_hole,
        "steps_classified": sum(totals.values()),
        "unknown_steps": unknown,
        "holes_with_actions": len(by_hole),
    }


_RANK_PTS = {
    "A": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 0,
    "Q": 10,
    "K": 10,
}


def _parse_demo_board(state_key: str | None) -> dict | None:
    """Parse pub/priv ranks from a demo state_key."""
    sk = state_key or ""
    if "pub_" not in sk or "_priv_" not in sk:
        return None
    try:
        pub_part = sk.split("pub_", 1)[1].split("_priv_", 1)[0]
        rest = sk.split("_priv_", 1)[1]
        priv_part = rest.split("_dis_", 1)[0]
    except (IndexError, ValueError):
        return None

    pub_ranks = re.findall(r"'([A2-9JQK]|10)'", pub_part)
    priv_ranks = re.findall(r"'([A2-9JQK]|10)'", priv_part)
    pub_pts = [_RANK_PTS.get(r, 5) for r in pub_ranks]
    priv_pts = [_RANK_PTS.get(r, 5) for r in priv_ranks]
    return {
        "n_pub": len(pub_ranks),
        "n_priv": len(priv_ranks),
        "pub_avg": (sum(pub_pts) / len(pub_pts)) if pub_pts else None,
        "priv_avg": (sum(priv_pts) / len(priv_pts)) if priv_pts else None,
        "pub_ranks": pub_ranks,
        "priv_ranks": priv_ranks,
    }


def _human_action_by_board(rows: list) -> dict:
    """Action mix by public face-up count × private-known count (+ avg card points)."""
    types = ("take_discard", "draw_keep", "draw_flip")
    # (n_pub, n_priv) -> type counts + point accumulators
    buckets: dict[tuple[int, int], dict] = {}
    unknown = 0
    no_state = 0

    for r in rows:
        board = _parse_demo_board(r.get("state_key"))
        if not board:
            no_state += 1
            continue
        at = _classify_human_action(r.get("action"), r.get("action_key"))
        if at not in types:
            unknown += 1
            continue
        key = (int(board["n_pub"]), int(board["n_priv"]))
        b = buckets.get(key)
        if b is None:
            b = {
                "counts": {t: 0 for t in types},
                "pub_sum": 0.0,
                "pub_n": 0,
                "priv_sum": 0.0,
                "priv_n": 0,
            }
            buckets[key] = b
        b["counts"][at] += 1
        if board["pub_avg"] is not None:
            b["pub_sum"] += float(board["pub_avg"])
            b["pub_n"] += 1
        if board["priv_avg"] is not None:
            b["priv_sum"] += float(board["priv_avg"])
            b["priv_n"] += 1

    if not buckets:
        return {
            "available": False,
            "types": list(types),
            "labels": [],
            "message": "No demos with parseable state_key (pub/priv) yet.",
        }

    keys = sorted(buckets.keys(), key=lambda k: (k[0] + k[1], k[0], k[1]))
    labels = []
    n_pub_list = []
    n_priv_list = []
    share = {t: [] for t in types}
    steps = []
    avg_pub_pts = []
    avg_priv_pts = []
    for key in keys:
        b = buckets[key]
        tot = sum(b["counts"].values())
        if tot <= 0:
            continue
        n_pub, n_priv = key
        labels.append(f"pub{n_pub} priv{n_priv}")
        n_pub_list.append(n_pub)
        n_priv_list.append(n_priv)
        steps.append(tot)
        for t in types:
            share[t].append(round(b["counts"][t] / tot, 4))
        avg_pub_pts.append(
            round(b["pub_sum"] / b["pub_n"], 2) if b["pub_n"] else None
        )
        avg_priv_pts.append(
            round(b["priv_sum"] / b["priv_n"], 2) if b["priv_n"] else None
        )

    return {
        "available": bool(labels),
        "types": list(types),
        "labels": labels,
        "n_pub": n_pub_list,
        "n_priv": n_priv_list,
        "share": share,
        "steps": steps,
        "avg_pub_pts": avg_pub_pts,
        "avg_priv_pts": avg_priv_pts,
        "steps_classified": sum(steps),
        "unknown_steps": unknown,
        "missing_state_key": no_state,
    }


def upload_game_state(game_id, game_state, timestamp=None, metadata=None):
    # get_game_state returns 'current_turn', not 'current_player'
    current_player = game_state.get("current_turn") or game_state.get("current_player")
    if current_player is None:
        print("Skipping upload: current_turn/current_player is None")
        return None

    players = game_state.get("players", [])
    # Support up to 4 players (expand as needed)
    flattened = {}
    for idx in range(4):
        if idx < len(players):
            p = players[idx]
            flattened[f"player{idx+1}_name"] = p.get("name")
            flattened[f"player{idx+1}_agent_type"] = p.get("agent_type")
            flattened[f"player{idx+1}_grid"] = p.get("grid")
            # 'known' field may not be in player_data from get_game_state, so use None if missing
            flattened[f"player{idx+1}_known"] = p.get("known", None)
        else:
            flattened[f"player{idx+1}_name"] = None
            flattened[f"player{idx+1}_agent_type"] = None
            flattened[f"player{idx+1}_grid"] = None
            flattened[f"player{idx+1}_known"] = None

    data = {
        "game_id": game_id,
        "round_num": game_state.get("round"),
        "current_player": current_player,
        **flattened,
        "discard_pile": game_state.get("discard_pile"),
        "deck_size": game_state.get("deck_size"),
        "action_history": game_state.get("action_history"),
        "scores": game_state.get("scores"),
        "winner": game_state.get("winner"),
        "game_over": game_state.get("game_over"),
        "timestamp": timestamp or datetime.utcnow().isoformat(),
    }
    response = supabase.table("game_states").insert(data).execute()
    return response

    return response


def upload_rl_training_run(meta: dict, *, upsert: bool = True):
    """
    Persist an archived RL training run summary to Supabase.
    Called from the local machine after CPU training or after pulling GPU/RunPod results.
    """
    summary = meta.get("summary") or {}
    params = meta.get("params") or {}
    run_id = meta.get("id") or meta.get("run_id")
    if not run_id:
        raise ValueError("upload_rl_training_run requires meta['id']")

    row = {
        "run_id": str(run_id),
        "source": meta.get("source"),
        "train_device": params.get("train_device") or summary.get("train_device"),
        "train_mode": params.get("train_mode") or summary.get("train_mode"),
        "games_played": summary.get("games_played"),
        "games_planned": summary.get("num_games_planned") or params.get("num_games"),
        "wins": summary.get("wins"),
        "ties": summary.get("ties"),
        "win_rate": summary.get("win_rate"),
        "avg_score": summary.get("avg_score"),
        "avg_opponent_score": summary.get("avg_opponent_score"),
        "best_score": summary.get("best_score"),
        "worst_score": summary.get("worst_score"),
        "early_avg_score": summary.get("early_avg_score"),
        "late_avg_score": summary.get("late_avg_score"),
        "improvement": summary.get("improvement"),
        "final_states": summary.get("final_states"),
        "final_entries": summary.get("final_entries"),
        "final_epsilon": summary.get("final_epsilon"),
        "learning_rate": summary.get("learning_rate") or params.get("learning_rate"),
        "epsilon": summary.get("epsilon") or params.get("epsilon"),
        "n_bootstrap_games": summary.get("n_bootstrap_games") or params.get("n_bootstrap_games"),
        "opponent_type": summary.get("opponent_type") or params.get("opponent_type"),
        "num_workers": params.get("num_workers"),
        "batch_size": params.get("batch_size"),
        "hidden_size": params.get("hidden_size"),
        "params": params,
        "summary": summary,
    }
    try:
        table = supabase.table("rl_training_runs")
        if upsert:
            response = table.upsert(row, on_conflict="run_id").execute()
        else:
            response = table.insert(row).execute()
        print(f"Uploaded RL run to Supabase: {run_id}")
        return response
    except Exception as e:
        print(f"Error uploading RL training run: {e}")
        return None


if __name__ == "__main__":
    # Single test data row that matches the golf game codebase patterns
    test_llm_call = {
        "llm_call_id": "golf_bot_response_001",
        "model": "llama3.1-8b",
        "prompt": "You are Jim Nantz, the famous golf commentator. A player just made an amazing shot from the rough to within 3 feet of the hole. Provide enthusiastic commentary about this shot.",
        "response_text": "OH MY GOODNESS! What an absolutely spectacular shot from the rough! The player has just pulled off a miracle, threading the needle through the trees and landing it within 3 feet. This is the kind of shot that makes golf the beautiful game it is. The crowd is going absolutely wild!",
        "prompt_tokens": 45,
        "completion_tokens": 67,
        "total_tokens": 112,
        "temperature": 0.7,
        "max_tokens": 150,
        "stream": False,
        "success": True,
        "response_time_ms": 2340,
        "game_id": "golf_game_2024_001",
        "bot_name": "Jim Nantz",
        "user_id": "player_kyle",
        "endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "api_version": "v1",
        "metadata": {"event_type": "commentary", "shot_quality": "amazing"}
    }

    # Insert test data
    try:
        result = supabase.table("llm_calls").upsert(test_llm_call).execute()
        print(f"✅ Inserted: {test_llm_call['llm_call_id']}")
    except Exception as e:
        print(f"❌ Error inserting {test_llm_call['llm_call_id']}: {e}")

    # Test analytics function
    print("\n📊 Testing Analytics Function:")
    analytics = get_llm_usage_analytics()
    if analytics:
        print(f"Total calls: {analytics['total_calls']}")
        print(f"Success rate: {analytics['success_rate']:.2%}")
        print(f"Total tokens: {analytics['total_tokens']}")
        print(f"Avg tokens per call: {analytics['avg_tokens_per_call']:.1f}")

    # Test recent calls function
    print("\n🔍 Recent LLM Calls:")
    recent_calls = get_recent_llm_calls(limit=3)
    if recent_calls:
        for call in recent_calls:
            print(f"- {call['llm_call_id']}: {call['model']} ({call['total_tokens']} tokens)")