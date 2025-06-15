import os
import tempfile
import requests
from utils import log
from sounds import play
import threading
import time

def split_sentences_dot(text):
    # Split only on period (dot), keep the dot with the sentence
    import re
    sentences = re.findall(r'[^.]+\.|[^.]+$', text)
    return [s.strip() for s in sentences if s.strip()]

def run(text=None, **kwargs):
    if not text:
        log("No text provided to /speak command. Nothing will be spoken.", "ERROR")
        return
    try:
        from API import send_openai_request
        sentences = split_sentences_dot(text)
        temp_dir = os.path.join(os.path.dirname(__file__), '../../temp')
        os.makedirs(temp_dir, exist_ok=True)
        speech_key = time.time()

        def process_sentences():
            temp_paths = []
            for idx, sentence in enumerate(sentences):
                payload = {
                    "model": "tts-1",
                    "input": sentence,
                    "voice": "nova"
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
                # Send to sounds.py as soon as it's ready (async)
                threading.Thread(target=play, args=(temp_path,), kwargs={"is_speech": True, "speech_key": speech_key}, daemon=True).start()
            # After all sentences have been sent, wait for assistant to finish speaking, then delete all temp files
            from sounds import is_speaking
            def delete_when_done(paths):
                while is_speaking():
                    time.sleep(0)
                for path in paths:
                    for _ in range(30):  # Try up to 30 times
                        try:
                            if os.path.exists(path):
                                os.remove(path)
                            break
                        except PermissionError:
                            time.sleep(0.2)
                        except Exception as e:
                            log(f"Failed to delete temp audio file {path}: {e}", "ERROR")
                            break
            threading.Thread(target=delete_when_done, args=(temp_paths,), daemon=True).start()

        threading.Thread(target=process_sentences, daemon=True).start()
    except Exception as e:
        log(f"Error during TTS synthesis or playback: {e}", "ERROR")
