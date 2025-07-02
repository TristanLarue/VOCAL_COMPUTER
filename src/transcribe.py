# transcribe.py
# Handles audio-to-text using OpenAI Whisper (tiny.en)

import os
from dotenv import load_dotenv
import tempfile
import whisper
import traceback
from utils import log

load_dotenv()

_model = None
_model_name = None

def load_whisper_model():
    global _model, _model_name
    from utils import get_settings
    settings = get_settings() or {}
    precision = settings.get('transcription-precision', 2)
    try:
        precision = int(precision)
    except Exception:
        precision = 2
    precision = max(1, min(3, precision))
    model_map = {1: 'tiny.en', 2: 'small.en', 3: 'medium.en'}
    model_name = model_map.get(precision, 'small.en')
    try:
        if _model is None or _model_name != model_name:
            _model = whisper.load_model(model_name)
            _model_name = model_name
        return _model
    except Exception as e:
        log(f"Error loading Whisper model: {e}\n{traceback.format_exc()}", "ERROR")
        return None

def transcribe_audio(audio_path):
    try:
        model = load_whisper_model()
        if not model:
            return ""
        result = model.transcribe(audio_path)
        return result.get("text", "")
    except Exception as e:
        log(f"Error transcribing audio: {e}\n{traceback.format_exc()}", "ERROR")
        return ""

async def async_transcribe(audio_path):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, transcribe_audio, audio_path)
    except Exception as e:
        log(f"Error in async_transcribe: {e}\n{traceback.format_exc()}", "ERROR")
        return ""

def preload_whisper():
    try:
        model = load_whisper_model()
        if model:
            log("Whisper model preloaded and ready.", "SYSTEM")
        else:
            log("Whisper model failed to preload.", "ERROR")
    except Exception as e:
        log(f"Error preloading Whisper model: {e}", "ERROR")
