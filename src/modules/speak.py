import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tempfile
import requests
from utils import log
from sounds import queue_speech
import threading
import time

def split_sentences_dot(text, **kwargs):
    # Split on a dot followed by a space or end of string, but not if the dot is between word characters (e.g., URLs)
    import re
    # This regex splits only on a dot that is not between two word characters and is followed by a space or end of string
    sentences = re.split(r'(?<!\w)\.(?=\s|$)', text)
    # Add the dot back to each sentence except the last if it was split
    sentences = [s.strip() + ('.' if i < len(sentences)-1 else '') for i, s in enumerate(sentences) if s.strip()]
    return sentences

def run(text=None, **kwargs):
    import time
    speech_key = time.time()
    if not text:
        log("No text provided to /speak command. Nothing will be spoken.", "ERROR")
        return
    # If text is a number, convert it back to a string
    if isinstance(text, (int, float)):
        text = str(text)
    try:
        from API import send_openai_request
        sentences = split_sentences_dot(text)
        temp_dir = os.path.join(os.path.dirname(__file__), '../../temp')
        os.makedirs(temp_dir, exist_ok=True)
        from utils import get_settings
        settings = get_settings() or {}
        voice_speed = settings.get('voice-speed', 1)
        # Clamp voice speed between 0.5 and 2
        try:
            voice_speed = float(voice_speed)
        except Exception:
            voice_speed = 1
        voice_speed = max(0.5, min(2.0, voice_speed))
        voice_name = settings.get('voice-name', 'nova')
        valid_voices = {'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'}
        if voice_name not in valid_voices:
            voice_name = 'nova'
        temp_paths = []
        for idx, sentence in enumerate(sentences):
            payload = {
                "model": "tts-1",
                "input": sentence,
                "voice": voice_name,
                "speed": voice_speed,
                "response_format": "mp3"  # Use mp3 for pygame compatibility
            }
            response = send_openai_request('audio/speech', payload, stream=True)
            if response is None:
                log(f"TTS API did not return a response for: {sentence}", "ERROR")
                continue
            temp_path = os.path.join(temp_dir, next(tempfile._get_candidate_names()) + '.mp3')
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            temp_paths.append(temp_path)
        # Queue all speech files in order, using the same speech_key
        for temp_path in temp_paths:
            queue_speech(temp_path, speech_key)
        # After all sentences have been sent, do not delete temp files here
        # Deletion is now handled in sounds.py after playback
    except Exception as e:
        log(f"Error during TTS synthesis or playback: {e}", "ERROR")

if __name__ == "__main__":
    from sounds import play_sound
    print("[SPEAK] Playing pop sound for audio check...")
    play_sound(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/pop.wav')))
    print("[SPEAK] Testing speech playback with text: 'Hello'")
    run(text="Hello")
    # Wait for speech to play (block main thread)
    import time
    time.sleep(5)
