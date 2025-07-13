import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tempfile
from utils import log
from sounds import queue_speech
import threading
import time
import requests
import traceback
from dotenv import load_dotenv

load_dotenv()

def send_openai_request(endpoint, payload, headers=None, stream=False):
    """Send request to OpenAI API"""
    try:
        url = f"https://api.openai.com/v1/{endpoint}"
        if headers is None:
            headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"}
        response = requests.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload, stream=stream)
        response.raise_for_status()
        if stream:
            return response
        return response.json()
    except Exception as e:
        log(f"OpenAI API request failed: {e}", "ERROR", script="speak.py")
        return None

def chatgpt_text_to_speech(text, voice="nova", speed=1.0, model="gpt-4o-mini-tts", response_format="mp3", stream=True, **kwargs):
    payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "speed": speed,
        "response_format": response_format
    }
    payload.update(kwargs)
    return send_openai_request('audio/speech', payload, stream=stream)

def elevenlabs_text_to_speech(
    text,
    voice_id="EXAVITQu4vr4xnSDxMaL",
    stability=0.5,
    similarity_boost=0.8,
    style=0.7,
    speaker_boost=True,
    model_id="eleven_multilingual_v2",
    api_key=None,
    **kwargs
):
    if api_key is None:
        api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        log("ElevenLabs API key not found in environment variables. Please set ELEVENLABS_API_KEY.", "ERROR")
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": speaker_boost
        }
    }
    data.update(kwargs)
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            log(f"ElevenLabs API error {response.status_code}: {response.text}", "ERROR")
            return None
    except Exception as e:
        log(f"Error calling ElevenLabs API: {e}", "ERROR")
        return None

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
        
        # Get voice instructions for tone/style guidance
        voice_instructions = settings.get('voice-instructions', '')
        
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
        total_tts_tokens = 0  # Track total characters for TTS cost calculation
        
        for idx, sentence in enumerate(sentences):
            temp_path = os.path.join(temp_dir, next(tempfile._get_candidate_names()) + '.mp3')
            sentence_length = len(sentence)
            total_tts_tokens += sentence_length
            
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
        
        # Calculate TTS costs in cents (OpenAI TTS pricing)
        if not emotional_voice and total_tts_tokens > 0:
            try:
                # Import global cost tracking
                import sys
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                import triggers
                
                # OpenAI TTS pricing: $0.015 per 1K characters (1.5¢ per 1K characters)
                tts_cost_per_1k_chars = 1.5  # 1.5¢ per 1000 characters
                tts_cost_cents = (total_tts_tokens / 1000) * tts_cost_per_1k_chars
                
                # Update global TTS cost tracking
                triggers.TOTAL_TTS_COST_CENTS += tts_cost_cents
                triggers.TOTAL_COST_CENTS = triggers.TOTAL_TOKEN_COST_CENTS + triggers.TOTAL_TTS_COST_CENTS
                
                # Estimate audio duration (rough: ~150 words per minute, ~5 chars per word = ~750 chars/min)
                estimated_duration_minutes = total_tts_tokens / 750
                
                log(f"TTS request: {total_tts_tokens} chars ({tts_cost_cents:.4f}¢) | Est. {estimated_duration_minutes:.2f} min", "COST")
                
            except Exception as e:
                log(f"TTS cost calculation failed: {e}", "ERROR", script="speak.py")
        
        for temp_path in temp_paths:
            queue_speech(temp_path, speech_key)
    except Exception as e:
        log(f"Error during TTS synthesis or playback: {e}", "ERROR", script="speak.py")

if __name__ == "__main__":
    from sounds import play_sound
    print("[SPEAK] Playing pop sound for audio check...")
    play_sound(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/pop.wav')))
    print("[SPEAK] Testing speech playback with text: 'Hello'")
    run(text="Hello")
    # Wait for speech to play (block main thread)
    import time
    time.sleep(5)
