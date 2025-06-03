import os
import importlib
from utils import log, Colors

# Command dictionary for AI prompt construction
COMMAND_DICTIONARY = {
    "screenshot": {
        "description": "Take a screenshot of a specific monitor or all monitors.",
        "arguments": {
            "param": "str (monitor number as string, or 'all' for all monitors)"
        }
    },
    "prompt": {
        "description": "Call the AI with a new prompt and optionally analyze a file.",
        "arguments": {
            "param": "str (format: 'prompt_text[,filename]')"
        }
    },
    "weather": {
        "description": "Get weather information for a location.",
        "arguments": {
            "param": "str (location)"
        }
    },
    "calendar": {
        "description": "Get calendar events or add a new event.",
        "arguments": {
            "param": "str (event details or date)"
        }
    },
    "timer": {
        "description": "Set a timer for a specified number of minutes.",
        "arguments": {
            "param": "str or int (minutes)"
        }
    },
    "alarm": {
        "description": "Set an alarm for a specific time.",
        "arguments": {
            "param": "str (time, e.g., '7:00 AM')"
        }
    },
    "music": {
        "description": "Play music or a specific song.",
        "arguments": {
            "param": "str (song name or genre)"
        }
    },
    "search": {
        "description": "Perform a web search for the given query.",
        "arguments": {
            "param": "str (search query)"
        }
    },
    "reminder": {
        "description": "Add a reminder.",
        "arguments": {
            "param": "str (reminder details)"
        }
    },
    "news": {
        "description": "Get the latest news on a topic.",
        "arguments": {
            "param": "str (topic)"
        }
    },
    "exit": {
        "description": "End the conversation and stop continuous recording.",
        "arguments": {}
    }
}

# Dynamically import all command modules from src/modules
def load_command_modules():
    commands_dir = os.path.join(os.path.dirname(__file__), "modules")
    command_modules = {}
    for filename in os.listdir(commands_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            cmd_name = filename[:-3].lower()
            module_path = f"modules.{cmd_name}"
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, "run"):
                    command_modules[cmd_name] = module.run
            except Exception as e:
                log(f"Failed to load command module {cmd_name}: {e}", "ERROR")
    return command_modules

COMMANDS = load_command_modules()

def execute_command(cmd, param, audio_stream=None):
    """Dispatch command to the appropriate module or handle exit. No logging here."""
    cmd_lower = cmd.lower()

    if cmd_lower == "exit":
        from transcribe import stop_continuous_recording
        stop_continuous_recording()
        return "Conversation ended. Waiting for wake word."

    if cmd_lower in COMMANDS:
        try:
            return COMMANDS[cmd_lower](param, audio_stream)
        except Exception as e:
            return f"Error executing command '{cmd_lower}': {e}"

    return f"Unknown command: {cmd}"