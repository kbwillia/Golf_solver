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

# print(api_key, flush=True)

url = "https://api.topmediai.com/v1/text2speech"
text = "Hello Friends, Great Shot!"
text = " Kyle has taken the lead with a card pairing in the last round! We're looking at next-level brilliance of the golf card game!"

speaker = "9a88ff6b-8788-11ee-a48b-e86f38d7ec1a" # jim nantz
# speaker = "5cd9f375-3a96-11ee-9fd9-8cec4b691ee9" #morgan freeman
# speaker = "bf924282-401c-11ef-8a7d-00163e0629d4" #morpheus
# speaker = "001565ad-3826-11ee-a861-00163e2ac61b" #snoop dog
# speaker = "5ccd51e7-3a96-11ee-bcfa-8cec4b691ee9" #Jennifer aniston
speaker = "5cc5dcee-3a96-11ee-96a1-8cec4b691ee9" # Eric Cartman
speaker = "f987d790-7cad-11ef-98bc-00163e0694db" #mike tyson



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

'''some voice have emotion: Angry, Cheerful, Sad, Excited, Friendly, Terrified, Shouting, Unfriendly, Whispering, Hopeful, Soulful, Pleasant, Complaining, Surprised, Uneasy, Fearful, Disgust'''

print("About to make POST request")
try:
    response = requests.post(url, json=payload, headers=headers)
    print("POST request done")
    print(response.json())

    # Parse the response and download the audio if successful
    result = response.json()
    if result.get("status") == 200 and "oss_url" in result.get("data", {}):
        audio_url = result["data"]["oss_url"]
        audio_response = requests.get(audio_url)
        with open("output.wav", "wb") as f:
            f.write(audio_response.content)
        print("Audio saved as output.wav. Play it to hear the result!")
    else:
        print("No audio URL found in response.")

except Exception as e:
    print("POST request failed:", e, flush=True)


import requests

url = "https://api.topmediai.com/v1/get_api_key_info"

headers = {"x-api-key": "6445fed100b649c59a84fc001042c6c5"}

print("About to make GET request for API key info", flush=True)
try:
    response = requests.request("GET", "https://api.topmediai.com/v1/get_api_key_info", headers=headers, timeout=10)
    print("GET request done", flush=True)
    print('get key info', response.text, flush=True)
except Exception as e:
    print("GET request failed:", e, flush=True)