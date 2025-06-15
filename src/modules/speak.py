import os
import tempfile
import requests
from utils import log
from sounds import play

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
        play(temp_path, is_speech=True)
        # Wait for the file to be released by pygame before deleting
        import time
        for _ in range(100):  # Wait up to 2 seconds
            try:
                os.remove(temp_path)
                break
            except PermissionError:
                time.sleep(0.02)
        else:
            log(f"Could not remove temp file (still in use): {temp_path}", "WARNING")
    except Exception as e:
        log(f"Error during TTS synthesis or playback: {e}", "ERROR")
