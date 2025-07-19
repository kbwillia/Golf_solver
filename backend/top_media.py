import requests
import csv
import json
import os

#use the env to get the api key
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("TOP_MEDIA")

# url = "https://api.topmediai.com/v1/voices_list"
# headers = {"x-api-key": "6445fed100b649c59a84fc001042c6c5"}
# response = requests.request("GET", url, headers=headers)

voice_id = "9a88ff6b-8788-11ee-a48b-e86f38d7ec1a"
api_key = "6445fed100b649c59a84fc001042c6c5"



url = "https://api.topmediai.com/v1/text2speech"
text = "Hello"

speaker = "9a88ff6b-8788-11ee-a48b-e86f38d7ec1a"
emotion = "Friendly"

payload = {
    "text": text,
    "speaker": speaker,
    "emotion": emotion
}
headers = {
    "x-api-key": "6445fed100b649c59a84fc001042c6c5",
    "Content-Type": "application/json"
}

response = requests.request("POST", url, json=payload, headers=headers)

print(response.text)


import requests

url = "https://api.topmediai.com/v1/get_api_key_info"

headers = {"x-api-key": "6445fed100b649c59a84fc001042c6c5"}

response = requests.request("GET", url, headers=headers)

print('get key info',response.text)
# # Parse the response and download the audio if successful
# result = response.json()
# if result.get("status") == 200 and "oss_url" in result.get("data", {}):
#     audio_url = result["data"]["oss_url"]
#     audio_response = requests.get(audio_url)
#     with open("output.wav", "wb") as f:
#         f.write(audio_response.content)
#     print("Audio saved as output.wav. Play it to hear the result!")
# else:
#     print("No audio URL found in response.")





# # Parse the JSON response
# voices_data = response.json()

# # Determine the list of voices (adjust key if needed)
# voices_list = voices_data.get("voices") or voices_data.get("data") or voices_data

# # If the voices_list is a dict, convert to list
# if isinstance(voices_list, dict):
#     voices_list = list(voices_list.values())

# # Flatten voices_list if it contains sublists
# flat_voices = []
# if isinstance(voices_list, list):
#     for v in voices_list:
#         if isinstance(v, list):
#             flat_voices.extend(v)
#         else:
#             flat_voices.append(v)
# else:
#     flat_voices = voices_list

# # Save to CSV
# if flat_voices and isinstance(flat_voices, list) and isinstance(flat_voices[0], dict):
#     keys = set()
#     for v in flat_voices:
#         keys.update(v.keys())
#     keys = list(keys)
#     with open("voices_list.csv", "w", newline='', encoding="utf-8") as f:
#         writer = csv.DictWriter(f, fieldnames=keys)
#         writer.writeheader()
#         writer.writerows(flat_voices)
#     print("Voice list saved to voices_list.csv")
# else:
#     print("No voice data found or unexpected format.")