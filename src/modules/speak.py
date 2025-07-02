import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tempfile
import requests
from utils import log
from sounds import queue_speech
import threading
import time
from API import chatgpt_text_to_speech, elevenlabs_text_to_speech

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
        sentences = split_sentences_dot(text)
        temp_dir = os.path.join(os.path.dirname(__file__), '../../temp')
        os.makedirs(temp_dir, exist_ok=True)
        from utils import get_settings
        settings = get_settings() or {}
        voice_speed = settings.get('voice-speed', 1)
        try:
            voice_speed = float(voice_speed)
        except Exception:
            voice_speed = 1
        voice_speed = max(0.5, min(2.0, voice_speed))
        voice_name = settings.get('voice-name', 'nova')
        valid_voices = {'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'}
        if voice_name not in valid_voices:
            voice_name = 'nova'
        emotional_voice = settings.get('emotional-voice', False)
        # ElevenLabs voice parameters (allow override via kwargs/settings)
        elevenlabs_voice_id = settings.get('elevenlabs-voice-id', 'EXAVITQu4vr4xnSDxMaL')
        stability = float(settings.get('elevenlabs-stability', 0.5))
        similarity_boost = float(settings.get('elevenlabs-similarity-boost', 0.8))
        style = float(settings.get('elevenlabs-style', 0.7))
        speaker_boost = bool(settings.get('elevenlabs-speaker-boost', True))
        model_id = settings.get('elevenlabs-model-id', 'eleven_multilingual_v2')
        temp_paths = []
        for idx, sentence in enumerate(sentences):
            temp_path = os.path.join(temp_dir, next(tempfile._get_candidate_names()) + '.mp3')
            if emotional_voice:
                log(f"Using ElevenLabs TTS for emotional voice: '{sentence[:50]}...'")
                audio_content = elevenlabs_text_to_speech(
                    sentence,
                    voice_id=elevenlabs_voice_id,
                    stability=stability,
                    similarity_boost=similarity_boost,
                    style=style,
                    speaker_boost=speaker_boost,
                    model_id=model_id
                )
                if audio_content:
                    with open(temp_path, 'wb') as f:
                        f.write(audio_content)
                    temp_paths.append(temp_path)
                else:
                    log(f"ElevenLabs TTS failed for sentence: {sentence}. Falling back to OpenAI TTS.", "ERROR")
                    response = chatgpt_text_to_speech(sentence, voice=voice_name, speed=voice_speed)
                    if response:
                        with open(temp_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        temp_paths.append(temp_path)
            else:
                response = chatgpt_text_to_speech(sentence, voice=voice_name, speed=voice_speed)
                if response is None:
                    log(f"TTS API did not return a response for: {sentence}", "ERROR")
                    continue
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                temp_paths.append(temp_path)
        for temp_path in temp_paths:
            queue_speech(temp_path, speech_key)
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
