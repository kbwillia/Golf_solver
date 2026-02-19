from supabase import create_client, Client
import os
from datetime import datetime
import uuid
from supabase import create_client, Client
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

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


def upload_game_state(game_id, game_state, timestamp=None, metadata=None):
    current_player = game_state.get("current_player")
    if current_player is None:
        print("Skipping upload: current_player is None")
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
            flattened[f"player{idx+1}_known"] = p.get("known")
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