import os
import tempfile
import requests
from utils import log
from sounds import force_play_sound

def run(text=None, **kwargs):
    if not text:
        log("No text provided to /speak command. Nothing will be spoken.", "ERROR")
        return
    try:
        from API import send_openai_request
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": "nova"
        }
        response = send_openai_request('audio/speech', payload, stream=True)
        if response is None:
            log("TTS API did not return a response. Speech will not be played.", "ERROR")
            return
        # Ensure temp directory exists
        temp_dir = os.path.join(os.path.dirname(__file__), '../../temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, next(tempfile._get_candidate_names()) + '.mp3')
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        log(f"TTS audio generated and saved to temporary file: {temp_path}", "TTS")
        force_play_sound(temp_path, is_speech=True)
        os.remove(temp_path)
        log("Temporary TTS audio file removed after playback.", "TTS")
    except Exception as e:
        log(f"Error during TTS synthesis or playback: {e}", "ERROR")
