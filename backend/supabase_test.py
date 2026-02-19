

from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client, Client

url = os.environ.get("SUPABASE_URL")
# print("url:", url)
key = os.environ.get("SUPABASE_LEGACY_SECRET")
test = os.environ.get("TEST")
# print("test:", test)
# print("key:", key)
print("key length:", len(key) if key else "None")

# SUPABASE_LEGACY_SECRET='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml0bmFjYWNoYnJrcHlmZ21zemlxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NjgxMTQ0MywiZXhwIjoyMDYyMzg3NDQzfQ.anx2ToTI7f3LV1vw7scNki_FToqJnntryriOMTQcMos'

# SUPABASE_URL="https://itnacachbrkpyfgmsziq.supabase.co"

supabase: Client = create_client(url, key)


# Insert example
data = {"username": "kyle2", "email": "kyle2@example.com"}
supabase.table("users").insert(data).execute()

# Select example
response = supabase.table("users").select("*").execute()
print(response.data)
