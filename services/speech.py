import os
from openai import OpenAI
from pathlib import Path
from core.config import settings

client = OpenAI(api_key=settings.openai_api_key)
speech_file_path = Path(__file__).parent.parent / "temp_audio.mp3"

def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribes an audio file using OpenAI's Whisper model.
    :param audio_file_path: The path to the audio file (e.g., .mp3, .wav).
    :return: The transcribed text as a string.
    """
    print(f"--- Transcribing audio file: {audio_file_path} ---")
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        print("--- Transcription successful ---")
        return transcript
    except Exception as e:
        print(f"Error during transcription: {e}")
        return f"Error: Could not transcribe audio. Details: {e}"


def text_to_speech(text: str) -> Path:
    """
    Converts a string of text into a spoken audio file using OpenAI's TTS model.
    :param text: The text to be converted to speech.
    :return: The Path object pointing to the created MP3 file.
    """
    print(f"--- Generating speech for text: '{text}' ---")
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy", 
            input=text
        )

        response.stream_to_file(speech_file_path)
        print(f"--- Speech file created at: {speech_file_path} ---")
        return speech_file_path
    except Exception as e:
        print(f"Error during text-to-speech conversion: {e}")
        raise