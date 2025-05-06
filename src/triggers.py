import os
import numpy as np
import pyaudio
import time
import pvporcupine
import threading
from dotenv import load_dotenv

from utils import log, Colors
from transcribe import record_audio

# Load environment variables
load_dotenv()

# Global state for bypass mode
bypass_active = False
bypass_end_time = 0
BYPASS_DELAY = 5  # seconds before bypass mode ends

# Pre-load sounds module
try:
    from sounds import play_bypass_start_sound, play_bypass_cancel_sound
    log("Sound module pre-loaded in triggers", "INFO")
except ImportError:
    log("Failed to pre-load sound module", "ERROR")

def initialize_wake_word(pa):
    """Initialize the wake word detection system"""
    porcupine = pvporcupine.create(
        access_key=os.getenv("PORCUPINE_ACCESS_KEY"),
        keywords=["computer"]
    )
    
    # Open audio stream with Porcupine's required parameters
    audio_stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    
    return porcupine, audio_stream

def process_wake_word(porcupine, audio_stream):
    """Process audio for wake word detection, returns (keyword_detected, bypass_active)"""
    global bypass_active, bypass_end_time
    
    # Read audio frame for wake word detection
    pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
    pcm_data = np.frombuffer(pcm, dtype=np.int16)
    
    # Check if wake word detected
    keyword_index = porcupine.process(pcm_data)
    
    # Check if bypass mode expired
    if bypass_active and time.time() > bypass_end_time:
        bypass_active = False
        #from sounds import play_bypass_cancel_sound
        #play_bypass_cancel_sound()
    
    # If wake word detected
    if keyword_index >= 0:
        log("Wake word 'Computer' detected!", "SUCCESS")
        
        # Start recording immediately
        threading.Thread(target=start_recording_flow, args=(audio_stream,), daemon=True).start()
        
        return True, bypass_active
    
    return False, bypass_active

def start_recording_flow(audio_stream):
    """Handle wake word detection and start recording immediately"""
    try:
        # Play the notification sound in a separate thread
        threading.Thread(target=play_notification_sound, daemon=True).start()
        
        # Start recording immediately
        from transcribe import record_audio
        frames = record_audio(audio_stream)
        
        # Process the voice query
        from chat import process_voice_query
        import pyaudio
        pa = pyaudio.PyAudio()  # Get a fresh PyAudio instance
        process_voice_query(frames, pa, audio_stream)
    except Exception as e:
        log(f"Error in recording flow: {e}", "ERROR")

def play_notification_sound():
    """Play the notification sound without blocking the recording flow"""
    from sounds import play_bypass_start_sound
    play_bypass_start_sound()

def set_bypass_mode(active=True, duration=BYPASS_DELAY):
    """Set the bypass mode state"""
    global bypass_active, bypass_end_time
    bypass_active = active
    if active:
        bypass_end_time = time.time() + duration