import os
#(venv) C:\Users\kbwil\Documents\Kyle\Data_Projects\Golf>set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\kbwil\Documents\Kyle\Data_Projects\google keys\pizza-ratings-405719-e66479b9147e.json



os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\kbwil\Documents\Kyle\Data_Projects\google keys\pizza-ratings-405719-e66479b9147e.json"
import base64
from google.cloud import texttospeech
import csv

text = "Hello, friends! Welcome to the ...golf card game"
voice_name = "en-AU-Chirp-HD-D"
language_code = voice_name[:5]

def test_chirp3_voice(text, voice_name):
    """
    Test Google Cloud Text-to-Speech Chirp 3 (HD Voice) API.
    Synthesizes a short phrase and saves it as output_chirp3.mp3.
    """
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text="Hello, friends! Welcome to the ... golf card game")
    print(f' chirp3 voice called in google_chipr_api.py')

    voice = texttospeech.VoiceSelectionParams(
        # language_code="es-US",
        language_code=language_code,
        # name="es-US-Chirp3-HD-Despina",
        # name="ar-XA-Chirp3-HD-Achernar",
        name=voice_name
        # ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
        # audio_encoding="LINEAR16"
    )

    print("Requesting synthesis from Google Text-to-Speech API...")
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    output_path = "output_chirp3.mp3"
    with open(output_path, "wb") as out:
        out.write(response.audio_content)
        print(f"Audio content written to {output_path}")

    # Play the audio file immediately
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load("output_chirp3.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue
    except Exception as e:
        print(f"Could not play sound automatically: {e}")

def list_google_voices():
    client = texttospeech.TextToSpeechClient()
    voices = client.list_voices()
    output_file = "google_voices.csv"
    # Collect all possible keys for columns
    fieldnames = [
        "name",
        "language_codes",
        "ssml_gender",
        "natural_sample_rate_hertz",
        "voice_type",
        "labels",
        "supported_features"
    ]
    with open(output_file, mode="w", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for voice in voices.voices:
            row = {
                "name": voice.name,
                "language_codes": ", ".join(voice.language_codes),
                "ssml_gender": str(voice.ssml_gender),
                "natural_sample_rate_hertz": getattr(voice, "natural_sample_rate_hertz", ""),
                "voice_type": getattr(voice, "voice_type", ""),
                "labels": getattr(voice, "labels", {}),
                "supported_features": getattr(voice, "supported_features", {})
            }
            writer.writerow(row)
    print(f"Wrote {len(voices.voices)} voices to {output_file}")



def chirp3_voice(text, voice_name):
    """
    Synthesizes speech using Google Cloud TTS and returns base64-encoded audio.
    """
    client = texttospeech.TextToSpeechClient()
    language_code = voice_name[:5]

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # Encode audio to base64 string
    audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
    return audio_base64


if __name__ == "__main__":
    # list_google_voices()
    test_chirp3_voice(text, voice_name)
    chirp3_voice(text, voice_name)
