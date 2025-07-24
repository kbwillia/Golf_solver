from supabase import create_client, Client
import os
from datetime import datetime

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_LEGACY_SECRET")
supabase: Client = create_client(url, key)

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

def create_chatbot_messages_table():
    # Supabase Python client does not support DDL, so you must run the SQL in the Supabase SQL editor.
    # This function is a placeholder for documentation or future use.
    print("Please run the following SQL in your Supabase SQL editor:")
    print("""<PASTE THE SQL SCHEMA ABOVE HERE>""")
