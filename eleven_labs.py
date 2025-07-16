import requests
from dotenv import load_dotenv
import os
import os
print("Current working directory:", os.getcwd())


# Get api key from .env file
load_dotenv()
api_key = "sk_6068ab89792bd71173f0b0cdd6a3ebba3bfe8c97347c9926"
print(api_key)
test_key = os.getenv("TEST_KEY")
print(test_key)

def generate_jim_nantz_commentary(text, voice_id="JBFqnCBsd6RMkjVDRZzb"):
    """
    Generate Jim Nantz commentary using ElevenLabs API

    Args:
        text (str): The commentary text to speak
        voice_id (str): The ElevenLabs voice ID to use

    Returns:
        bytes: Audio data that can be played
    """
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            return response.content
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"Error generating speech: {e}")
        return None

def save_jim_nantz_commentary(text, filename="jim_nantz_commentary.mp3", voice_id="JBFqnCBsd6RMkjVDRZzb"):
    """
    Generate and save Jim Nantz commentary to a file

    Args:
        text (str): The commentary text to speak
        filename (str): Output filename
        voice_id (str): The ElevenLabs voice ID to use
    """
    audio = generate_jim_nantz_commentary(text, voice_id)
    if audio:
        with open(filename, "wb") as f:
            f.write(audio)
        print(f"Commentary saved to {filename}")
    else:
        print("Failed to generate commentary")

# Test the function
if __name__ == "__main__":
    # Generate speech using the current API
    test_text = "The first move is what sets everything in motion."
    audio = generate_jim_nantz_commentary(test_text)

    if audio:
        # Save the audio file
        with open("output.mp3", "wb") as f:
            f.write(audio)
        print("Audio generated successfully!")
        os.startfile("output.mp3")
    else:
        print("Failed to generate audio")
