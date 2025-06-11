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

def load_whisper_model():
    global _model
    try:
        if _model is None:
            _model = whisper.load_model("tiny.en")
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
