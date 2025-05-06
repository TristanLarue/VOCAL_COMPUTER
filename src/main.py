import os
import platform
import ctypes.util
import pyaudio
import warnings
import time
import threading
from dotenv import load_dotenv

from utils import log, Colors

# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# Load environment variables
load_dotenv()

# Suppress non-critical warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# Ensure ffmpeg is on PATH for audio handling
ffmpeg_bin = r"C:\Users\powwo\Documents\ffmpeg\bin"
os.environ["PATH"] = ffmpeg_bin + ";" + os.environ.get("PATH", "")

# On Windows, force correct C library lookup
if platform.system() == "Windows":
    orig_find = ctypes.util.find_library
    ctypes.util.find_library = lambda name: "msvcrt" if name == "c" else orig_find(name)

def main():
    log("Initializing voice assistant...", "SYSTEM")
    
    # Pre-initialize modules to avoid delays during wake word response
    log("Pre-loading modules...", "SYSTEM")
    
    # Pre-load the Whisper model
    from transcribe import initialize_whisper
    whisper_model = initialize_whisper()
    log("Whisper model loaded", "SYSTEM")
    
    # Pre-initialize sound system
    import pygame
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    log("Sound system initialized", "SYSTEM")
    
    # Initialize PyAudio
    pa = pyaudio.PyAudio()
    
    # Import and initialize wake word detection
    from triggers import initialize_wake_word
    porcupine, audio_stream = initialize_wake_word(pa)
    
    try:
        log("Startup complete. Say 'Computer' to activate.", "SYSTEM")
        
        # Pre-load sound modules to avoid import delays
        from sounds import play_prompt_sound, play_bypass_start_sound
        
        from triggers import process_wake_word
        
        while True:
            # Process wake word detection
            keyword_detected, bypass_active = process_wake_word(porcupine, audio_stream)
            
            # Note: Recording now starts immediately in process_wake_word when wake word is detected
            # No need for additional code here to start recording
                
    except Exception as e:
        log(f"Error: {e}", "ERROR")
    finally:
        # Clean up resources
        if porcupine is not None:
            porcupine.delete()
        
        if audio_stream is not None:
            audio_stream.close()
        
        pa.terminate()

if __name__ == "__main__":
    main()