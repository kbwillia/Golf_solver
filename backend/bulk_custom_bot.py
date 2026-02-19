import json
import requests
import uuid

# Path to your custom bots JSON file
with open('frontend/static/custom_bot.json', 'r') as f:
    data = json.load(f)

bots = []

# Handle 'placeholder_bots' (list)
for bot in data.get('placeholder_bots', []):
    bot = dict(bot)  # Make a copy to avoid mutating the original
    bot['ai_bot_id'] = str(uuid.uuid4())
    bots.append(bot)

# Handle 'custom_bots' (dict)
for key, bot in data.get('custom_bots', {}).items():
    bot = dict(bot)
    bot['ai_bot_id'] = str(uuid.uuid4())
    bots.append(bot)

# print(f' bots 24: {bots}')
#print 1 bot
print(f' bots 24: {bots[0]}')
# Backend endpoint for creating a custom bot
ENDPOINT = 'http://localhost:5000/api/create_custom_bot'

# print(f' bots 27: {bots}')
for bot in bots:
    required = ['ai_bot_id', 'name', 'difficulty', 'description']
    if not all(field in bot and bot[field] for field in required):
        print(f"Skipping bot (missing required fields): {bot}")
        continue
    # Build payload, including img_path if present
    payload = {k: bot[k] for k in required}

    if 'img_path' in bot and bot['img_path']:
        payload['image_path'] = bot['img_path']
    payload['ai_bot_id'] = bot['ai_bot_id']
    response = requests.post(ENDPOINT, json=payload)
    print(f"Bot: {bot.get('name', 'Unnamed')} | Status: {response.status_code} | Response: {response.text}")