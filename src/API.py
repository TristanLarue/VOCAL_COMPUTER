import requests
import os
import json
from dotenv import load_dotenv
import traceback
from utils import log

load_dotenv()

def send_openai_request(endpoint, payload, headers=None, files=None, stream=False):
    """
    Generic function to send a request to any OpenAI endpoint.
    endpoint: e.g. 'chat/completions' or 'audio/speech'
    payload: dict to send as JSON
    headers: dict of headers (optional)
    files: for file uploads (optional)
    stream: if True, stream response (for TTS)
    Returns: raw response object or response.json()
    """
    try:
        url = f"https://api.openai.com/v1/{endpoint}"
        if headers is None:
            headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"}
        response = requests.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload, stream=stream)
        response.raise_for_status()
        if stream:
            return response  # caller handles streamed data
        return response.json()
    except Exception as e:
        log(f"OpenAI API request failed: {e}\n{traceback.format_exc()}", "ERROR")
        return None

def chatgpt_text_to_text(*, prompt=None, **kwargs):
    """
    Accepts either a prompt string (for simple use) or a full payload dict (for legacy compatibility).
    """
    if prompt is not None:
        payload = {
            "model": kwargs.get("model", "gpt-4.1"),
            "messages": [{"role": "user", "content": prompt}]
        }
        payload.update({k: v for k, v in kwargs.items() if k not in ("model",)})
    else:
        payload = kwargs
    return send_openai_request('chat/completions', payload)

def chatgpt_text_to_speech(text, voice="nova", speed=1.0, model="tts-1", response_format="mp3", stream=True, **kwargs):
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
    import requests
    from utils import log
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
