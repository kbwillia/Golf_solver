import json
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client, Client

url = os.environ.get("SUPABASE_URL")
# print("url:", url)
key = os.environ.get("SUPABASE_LEGACY_SECRET")
# print("test:", test)
# print("key:", key)
print("key length:", len(key) if key else "None")
# Load your JSON file
with open('frontend/static/custom_bot.json', 'r') as f:
    bots = json.load(f)

# Set up Supabase client

supabase: Client = create_client(url, key)

# Insert placeholder bots
for bot in bots['placeholder_bots']:
    data = {
        "name": bot["name"],
        "description": bot["description"],
        "difficulty": bot["difficulty"],
        "image_url": None  # or a placeholder URL if you want
    }
    res = supabase.table('custom_bots').insert(data).execute()
    print(res)

# Insert custom bots (if any)
for key, bot in bots.get('custom_bots', {}).items():
    data = {
        "name": bot["name"],
        "description": bot["description"],
        "difficulty": bot["difficulty"],
        "image_url": None
    }
    res = supabase.table('custom_bots').insert(data).execute()
    print(res)
