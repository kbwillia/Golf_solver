from supabase import create_client, Client
import os
from datetime import datetime
import os
from supabase import create_client, Client

from dotenv import load_dotenv
load_dotenv()

key = os.environ.get("SUPABASE_LEGACY_SECRET")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_LEGACY_SECRET")
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
