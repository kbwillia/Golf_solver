from dotenv import load_dotenv
load_dotenv()

import os
import sys
from supabase import create_client, Client
import requests
from postgrest.exceptions import APIError

print("=" * 60)
print("Testing Database Connection")
print("=" * 60)

# Get environment variables
url = os.environ.get("SUPABASE_URL")
# Try legacy secret first, then public key
key = os.environ.get("SUPABASE_LEGACY_SECRET") or os.environ.get("SUPABASE_SECRET")
public_key = os.environ.get("SUPBAASE_PUBLIC") or os.environ.get("SUPABASE_PUBLIC")

# Validate environment variables
if not url:
    print("ERROR: SUPABASE_URL not found in environment variables")
    exit(1)

# Note: We'll try both keys, so don't exit if one is missing

print(f"\n[OK] Supabase URL: {url}")
if key:
    print(f"[OK] Legacy Secret Key length: {len(key)} characters")
    # Check if key matches URL project
    if "itnacachbrkpyfgmsziq" in key and "guhweuzngmccjbttcmgx" in url:
        print("[WARNING] API key appears to be from old project, but URL is new project!")
    elif "guhweuzngmccjbttcmgx" in key and "guhweuzngmccjbttcmgx" in url:
        print("[OK] API key and URL appear to match")
else:
    print("[WARNING] No legacy secret key found")
    
if public_key:
    print(f"[OK] Public Key found: {public_key[:20]}...")
else:
    print("[INFO] No public key found")

# Test network connectivity first
print("\n--- Testing network connectivity ---")
try:
    test_response = requests.get(url, timeout=5)
    print(f"[OK] Network connection successful (Status: {test_response.status_code})")
except requests.exceptions.RequestException as e:
    print(f"[WARNING] Network connectivity issue: {e}")
    print("This might be a firewall or DNS issue. Continuing anyway...")

# Test connection by querying a simple table
print("\n" + "=" * 60)
print("Testing Database Connection")
print("=" * 60)

# Try to query for characters - check multiple possible table names
# Include the view that was suggested in the error message
tables_to_check = ["characters", "custom_bots", "custom_bots_view", "bots"]

# Try with legacy secret first, then public key if that fails
keys_to_try = []
if key:
    keys_to_try.append(("LEGACY_SECRET", key))
if public_key:
    keys_to_try.append(("PUBLIC_KEY", public_key))

if not keys_to_try:
    print("\n[ERROR] No API keys found to test with!")
    exit(1)

for key_name, test_key in keys_to_try:
    print(f"\n{'='*60}")
    print(f"Trying with {key_name}")
    print(f"{'='*60}")
    
    try:
        test_supabase: Client = create_client(url, test_key)
        print(f"[OK] Client created with {key_name}")
    except Exception as e:
        print(f"[ERROR] Failed to create client with {key_name}: {e}")
        continue

    for table_name in tables_to_check:
            try:
                print(f"\n--- Checking table: {table_name} ---")
                response = test_supabase.table(table_name).select("*").limit(10).execute()
            
                if response.data:
                    print(f"[OK] Found {len(response.data)} records in '{table_name}' table")
                    print(f"\nRecords:")
                    for idx, record in enumerate(response.data, 1):
                        print(f"\n  Record {idx}:")
                        for key, value in record.items():
                            print(f"    {key}: {value}")
                else:
                    print(f"  Table '{table_name}' exists but is empty")
                    
            except APIError as e:
                error_dict = e.args[0] if e.args and isinstance(e.args[0], dict) else {}
                error_msg = error_dict.get('message', str(e))
                error_code = error_dict.get('code', '')
                hint = error_dict.get('hint', '')
                
                print(f"  Error type: APIError")
                print(f"  Error code: {error_code}")
                print(f"  Error message: {error_msg}")
                if hint:
                    print(f"  Hint: {hint}")
                
                if "could not find the table" in error_msg.lower() or error_code == 'PGRST205':
                    print(f"  -> Table '{table_name}' does not exist")
                elif "invalid api key" in error_msg.lower() or error_code == '401':
                    print(f"  -> Authentication error - API key doesn't match this project")
                    print(f"     Make sure the key matches project: guhweuzngmccjbttcmgx")
                else:
                    print(f"  -> Unknown API error")
                    
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                print(f"  Error type: {error_type}")
                print(f"  Error message: {error_msg}")
                
                if "relation" in error_msg.lower() or "does not exist" in error_msg.lower() or "not found" in error_msg.lower():
                    print(f"  -> Table '{table_name}' does not exist")
                elif "getaddrinfo" in error_msg.lower() or "network" in error_msg.lower() or "connection" in error_msg.lower():
                    print(f"  -> Network/DNS error - check internet connection and firewall settings")
                elif "permission" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg.lower():
                    print(f"  -> Authentication error - API key doesn't match this project")
                    print(f"     Make sure the key matches project: guhweuzngmccjbttcmgx")
                else:
                    print(f"  -> Unknown error querying '{table_name}'")
                    import traceback
                    traceback.print_exc()

# List all available tables (if possible)
print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("\nDatabase connection test completed!")
