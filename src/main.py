from dotenv import load_dotenv
import os
import traceback
from utils import log

# main.py
# Entry point: initializes all modules, preloads models, and starts the async trigger loop

def preload_libraries():
    try:
        load_dotenv()
        import whisper
        import pvporcupine
        import pyaudio
        log("All libraries and modules preloaded successfully. Ready to start assistant.", "SYSTEM")
    except Exception as e:
        log(f"Failed to preload libraries: {e}\n{traceback.format_exc()}", "ERROR")

def main():
    try:
        preload_libraries()
        from triggers import setup_triggers, run_triggers, stop_triggers
        setup_triggers(None)
        log("Trigger system initialized. Awaiting wake word.", "SYSTEM")
        try:
            run_triggers()  # This blocks until program exit (ctrl+c or X)
        except KeyboardInterrupt:
            log("Keyboard interrupt received. Stopping all assistant processes.", "ERROR")
        except Exception as e:
            log(f"Exception in run_triggers: {e}\n{traceback.format_exc()}", "ERROR")
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
                    log("Memory wiped on shutdown (permanent-memory is false).", "MEMORY")
            except Exception as e:
                log(f"Error wiping memory on shutdown: {e}", "ERROR")
            log("Shutdown complete. Goodbye!", "SYSTEM")
    except Exception as e:
        log(f"Fatal error in main: {e}\n{traceback.format_exc()}", "ERROR")

if __name__ == "__main__":
    main()
