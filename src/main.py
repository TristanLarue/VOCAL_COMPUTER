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
    from triggers import initialize_wake_word, set_wake_word_active, get_wake_word_active
    porcupine, audio_stream = initialize_wake_word(pa)
    
    # Explicitly set wake word mode active at startup
    set_wake_word_active(True)
    
    # Import the continuous recording module
    from transcribe import start_continuous_recording
    
    try:
        log("Startup complete. Say 'Computer' to activate.", "SYSTEM")
        
        # Load essential modules
        from triggers import process_wake_word
        from transcribe import record_audio
        from chat import process_voice_query
        
        while True:
            # Check if we should be in wake word mode
            if get_wake_word_active():
                # Process wake word detection
                keyword_detected, _ = process_wake_word(porcupine, audio_stream)
                
                # If wake word detected, start recording and switch to continuous mode
                if keyword_detected:
                    # Update wake word state
                    set_wake_word_active(False)
                    
                    # Record initial query
                    log("Recording initial query...", "AUDIO")
                    frames = record_audio(audio_stream)
                    
                    # Process the voice query
                    process_voice_query(frames, pa, audio_stream)
                    
                    # Switch to continuous recording mode
                    start_continuous_recording(audio_stream, pa)
                    log("Switched to continuous recording mode", "SYSTEM")
            
            else:
                # In continuous mode, just sleep as the continuous recording thread handles everything
                time.sleep(0.1)
            
            # Add a short sleep to prevent 100% CPU usage
            time.sleep(0.01)
                
    except KeyboardInterrupt:
        log("Shutting down on keyboard interrupt", "SYSTEM")
    except Exception as e:
        log(f"Error: {e}", "ERROR")
    finally:
        # Clean up resources
        if porcupine is not None:
            porcupine.delete()
        
        if audio_stream is not None:
            audio_stream.close()
        
        pa.terminate()
        log("System shutdown complete", "SYSTEM")

if __name__ == "__main__":
    main()