import numpy as np
import wave
import whisper
import time
import os

from utils import log, Colors

# Audio recording constants
CHUNK = 1024
FORMAT = None  # Will be set from pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Porcupine requires 16kHz
SILENCE_THRESHOLD = 500
SILENCE_CHUNKS = int(RATE / CHUNK * 2)

# Timing metrics
transcription_start = 0
transcription_end = 0

# Global state
current_rms = 0
prompt_end_time = 0

# Initialize Whisper model
def initialize_whisper():
    """Initialize the Whisper model for transcription"""
    return whisper.load_model("tiny")

def record_audio(stream):
    """Record audio until silence is detected"""
    global prompt_end_time, current_rms
    frames = []
    silence_count = 0
    log("Recording started...", "AUDIO")
    
    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio**2))
        current_rms = round(rms)
        
        if rms < SILENCE_THRESHOLD:
            silence_count += 1
            if silence_count > SILENCE_CHUNKS:
                break
        else:
            silence_count = 0
    
    current_rms = 0
    prompt_end_time = time.time()
    log(f"Recording finished ({len(frames)} frames)", "AUDIO")
    return frames

def save_wav(filename, frames, pa):
    """Save audio frames to WAV file"""
    import pyaudio  # Import here to avoid circular imports
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))  # Using FORMAT constant from pyaudio
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    log(f"Saved audio to {filename}", "AUDIO")

def transcribe_audio(filename, model=None):
    """Transcribe audio using Whisper"""
    global transcription_start, transcription_end
    
    if model is None:
        model = initialize_whisper()
    
    log("Transcribing audio...", "WHISPER")
    transcription_start = time.time()
    result = model.transcribe(filename)
    transcription_end = time.time()
    
    text = result.get("text", "").strip()
    log(f"Transcription duration: {Colors.BOLD}{(transcription_end-transcription_start):.3f}s{Colors.ENDC}", "TIMING")
    log(f"Transcription result: {Colors.BOLD}{text}{Colors.ENDC}", "WHISPER")
    
    return text

def get_prompt_end_time():
    """Return the time when the prompt ended"""
    return prompt_end_time