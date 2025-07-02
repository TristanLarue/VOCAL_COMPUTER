from dotenv import load_dotenv
import os
import traceback
from utils import log
from sounds import start_speech_worker
import threading

SCRIPT_NAME = "main.py"
# main.py
# Entry point: initializes all modules, preloads models, and starts the async trigger loop

def preload_libraries():
    try:
        load_dotenv()
        log("All libraries and modules preloaded successfully. Ready to start assistant.", "SYSTEM", script=SCRIPT_NAME)
    except Exception as e:
        log(f"Failed to preload libraries: {e}\n{traceback.format_exc()}", "ERROR", script=SCRIPT_NAME)

def main():
    try:
        preload_libraries()
        # Preload Whisper model for faster first transcription
        from transcribe import preload_whisper
        preload_whisper()
        # Start the async speech worker
        start_speech_worker()
        from triggers import setup_triggers, run_triggers, stop_triggers
        setup_triggers(None)
        log("Trigger system initialized. Awaiting wake word.", "SYSTEM", script=SCRIPT_NAME)
        try:
            run_triggers()  # This blocks until program exit (ctrl+c or X)
        except KeyboardInterrupt:
            log("Keyboard interrupt received. Stopping all assistant processes.", "ERROR", script=SCRIPT_NAME)
        except Exception as e:
            log(f"Exception in run_triggers: {e}\n{traceback.format_exc()}", "ERROR", script=SCRIPT_NAME)
        finally:
            stop_triggers()
            # --- Wipe memory if permanent-memory is false ---
            try:
                import json
                from utils import get_settings
                settings = get_settings()
                memory_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/memory.json'))
                if settings and not settings.get('permanent-memory', False):
                    with open(memory_path, 'w', encoding='utf-8') as f:
                        json.dump({"summary": ""}, f, indent=2)
                    log("Memory wiped on shutdown (permanent-memory is false).", "MEMORY", script=SCRIPT_NAME)
            except Exception as e:
                log(f"Error wiping memory on shutdown: {e}", "ERROR", script=SCRIPT_NAME)
            # Clean up temp folder on shutdown only if permanent-memory is false
            try:
                if settings and not settings.get('permanent-memory', False):
                    import shutil
                    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../temp'))
                    for filename in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    log("Temp folder cleaned on shutdown.", "SYSTEM", script=SCRIPT_NAME)
            except Exception as e:
                log(f"Error cleaning temp folder: {e}", "ERROR", script=SCRIPT_NAME)
            log("Shutdown complete. Goodbye!", "SYSTEM", script=SCRIPT_NAME)
    except Exception as e:
        log(f"Fatal error in main: {e}\n{traceback.format_exc()}", "ERROR", script=SCRIPT_NAME)

if __name__ == "__main__":
    main()
