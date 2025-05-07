import os
import time
import threading
from utils import log, Colors

def execute_command(cmd, param, audio_stream=None):
    """Execute commands with their parameters"""
    log(f"Executing command: {Colors.BOLD}/{cmd}:{param}{Colors.ENDC}", "COMMAND")
    
    # Placeholder command implementations
    responses = {
        "weather": f"Getting weather for {param}. It's currently sunny with a temperature of 72°F.",
        "calendar": f"Accessing calendar: {param}. You have 3 events scheduled for today.",
        "timer": f"Timer set for {param} minutes.",
        "alarm": f"Alarm set for {param}.",
        "music": f"Playing music: {param}.",
        "search": f"Web search results for '{param}' found.",
        "reminder": f"Reminder added: {param}.",
        "news": f"Latest news on {param}: Three new developments reported today."
    }
    
    # Handle exit command
    if cmd.lower() == "exit":
        log("Exit command received, stopping continuous recording", "COMMAND")
        from transcribe import stop_continuous_recording
        stop_continuous_recording()
        
        # Import here to avoid circular imports
        from triggers import initialize_wake_word_mode, set_wake_word_active
        # Switch back to wake word detection mode
        initialize_wake_word_mode()
        # Explicitly set wake word active state
        set_wake_word_active(True)
        
        # Reset any state that might prevent wake word detection
        from sounds import reset_speech_state
        reset_speech_state()
        
        # Reset conversation memory
        from memory import reset_memory
        reset_memory()
        
        return "Conversation ended. Waiting for wake word."
    
    # Return the placeholder response or generic message
    return responses.get(cmd.lower(), f"Command {cmd} executed with parameter {param}")