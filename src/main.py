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
    
    # --- BEGIN: Terminal input thread for manual prompt ---
    def terminal_input_loop(audio_stream, pa):
        from chat import call_chatgpt, extract_commands
        from memory import get_memory, update_memory
        from sounds import speak_text
        from transcribe import set_ai_speaking_state
        from commands import execute_command
        while True:
            try:
                user_input = input(f"{Colors.BOLD}{Colors.BYPASS}[Type prompt]:{Colors.ENDC} ")
                if not user_input.strip():
                    continue
                log(f"Manual prompt: {user_input}", "BYPASS")
                conversation_memory = get_memory()
                answer = call_chatgpt(user_input, conversation_memory)
                update_memory(user_input, answer)
                clean_text, commands = extract_commands(answer)
                clean_text = clean_text.strip()
                log(f"Speaking: {clean_text}", "BYPASS")
                set_ai_speaking_state(True)
                if clean_text:
                    speak_text(clean_text, audio_stream)
                set_ai_speaking_state(False)
                for cmd, param in commands:
                    result = execute_command(cmd, param, audio_stream)
                    log(f"Command [{cmd}({param})] result: {result}", "COMMAND")
            except Exception as e:
                log(f"Terminal input error: {e}", "ERROR")
    # --- END: Terminal input thread for manual prompt ---

    try:
        log("Startup complete. Say 'Computer' to activate.", "SYSTEM")
        
        # Load essential modules
        from triggers import process_wake_word
        from sounds import play_open_sound
        
        # Start terminal input thread (non-blocking)
        threading.Thread(target=terminal_input_loop, args=(audio_stream, pa), daemon=True).start()
        while True:
            # Check if we should be in wake word mode
            if get_wake_word_active():
                # Process wake word detection
                keyword_detected, _ = process_wake_word(porcupine, audio_stream)
                
                # If wake word detected, immediately start continuous recording mode
                if keyword_detected:
                    # Update wake word state
                    set_wake_word_active(False)
                    
                    # Play the wake sound
                    play_open_sound()
                    
                    # Go directly to continuous recording mode
                    start_continuous_recording(audio_stream, pa)
                    log("Started continuous recording mode", "SYSTEM")
            
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
        from transcribe import stop_continuous_recording,continuous_recording_active
        if continuous_recording_active:
            stop_continuous_recording()
        if porcupine is not None:
            porcupine.delete()
        
        if audio_stream is not None:
            audio_stream.close()
        
        pa.terminate()
        log("System shutdown complete", "SYSTEM")

if __name__ == "__main__":
    main()