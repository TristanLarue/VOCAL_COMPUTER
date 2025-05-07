import os
import numpy as np
import pyaudio
import time
import pvporcupine
import threading
from dotenv import load_dotenv

from utils import log, Colors

# Load environment variables
load_dotenv()

# Global state for wake word detection
wake_word_active = False

# Pre-load sounds module
try:
    from sounds import play_prompt_sound
except ImportError:
    log("Failed to pre-load sound module", "ERROR")

def set_wake_word_active(state):
    """Set the wake word active state"""
    global wake_word_active
    wake_word_active = state
    log(f"Wake word active state set to: {state}", "SYSTEM")

def get_wake_word_active():
    """Get the current wake word active state"""
    global wake_word_active
    return wake_word_active

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
    """Process audio for wake word detection, returns (keyword_detected, unused_flag)"""
    
    # Read audio frame for wake word detection
    pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
    pcm_data = np.frombuffer(pcm, dtype=np.int16)
    
    # Check if wake word detected
    keyword_index = porcupine.process(pcm_data)
    
    # If wake word detected
    if keyword_index >= 0:
        log("Wake word 'Computer' detected!", "SUCCESS")
        
        # Play a notification sound to indicate wake word detection
        threading.Thread(target=play_notification_sound, daemon=True).start()
        
        return True, False
    
    return False, False

def play_notification_sound():
    """Play the notification sound without blocking the recording flow"""
    from sounds import play_prompt_sound
    play_prompt_sound()
    
def initialize_wake_word_mode():
    """Switch back to wake word detection mode"""
    log("Switching back to wake word detection mode", "SYSTEM")
    
    # Set the global state to enable wake word detection
    set_wake_word_active(True)
    
    # This will be imported and used by main.py
    log("Now listening for wake word 'Computer'", "SYSTEM")