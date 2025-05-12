import os
import time
import threading
from utils import log, Colors

def execute_command(cmd, param, audio_stream=None):
    """Execute commands with their parameters"""
    log(f"Executing command: {Colors.BOLD}/{cmd}({param}){Colors.ENDC}", "COMMAND")
    
    # Screenshot command
    if cmd.lower() == "screenshot":
        try:
            # Import the screenshot module
            from modules.screenshot import capture_screen, capture_all_screens, list_monitors
            
            # Parse the parameter to determine which monitor to capture
            if param.lower() == "all":
                filepath = capture_all_screens()
                return f"Screenshot of all monitors saved to {filepath}"
            else:
                # Try to convert param to int for specific monitor, default to 1
                try:
                    monitor_num = int(param) if param else 1
                except ValueError:
                    monitor_num = 1
                
                filepath = capture_screen(monitor_num)
                return f"Screenshot of monitor {monitor_num} saved to {filepath}"
        except Exception as e:
            log(f"Screenshot command error: {e}", "ERROR")
            return "I couldn't take a screenshot due to an error."
    
    # Handle prompt command - allows AI to call itself with a new prompt and analyze files
    if cmd.lower() == "prompt":
        try:
            # Parse parameters - format is "prompt_text,filename"
            params = param.split(',', 1)
            prompt_text = params[0].strip()
            filename = params[1].strip() if len(params) > 1 else None
            
            log(f"Self-prompt command received: '{prompt_text}', file: {filename}", "COMMAND")
            
            # Import chat functionality
            from chat import call_chatgpt
            from memory import get_memory
            
            # Get current memory
            conversation_memory = get_memory()
            
            # Prepare the file path if provided
            image_path = None
            if filename:
                # Check if file exists in temp directory
                temp_path = os.path.join("temp", filename)
                if os.path.exists(temp_path):
                    image_path = temp_path
                    log(f"Using file from temp directory: {image_path}", "COMMAND")
                else:
                    # Check if file exists as absolute path
                    if os.path.exists(filename):
                        image_path = filename
                        log(f"Using file from absolute path: {image_path}", "COMMAND")
                    else:
                        log(f"File not found: {filename}", "ERROR")
            
            # Call the AI with the new prompt and optional image
            response = call_chatgpt(prompt_text, conversation_memory, image_path)
            
            # Import the speak function to read out the response
            from sounds import speak_text
            
            # Speak the response
            if audio_stream:
                log("Speaking self-prompt response", "COMMAND")
                speak_text(response, audio_stream)
            
            return f"Self-prompt executed: '{prompt_text}'" + (f" with file: {filename}" if filename else "")
        except Exception as e:
            log(f"Self-prompt command error: {e}", "ERROR")
            return f"Error executing self-prompt: {str(e)}"
    
    # Handle exit command
    if cmd.lower() == "exit":
        log("Exit command received, stopping continuous recording", "COMMAND")
        from transcribe import stop_continuous_recording
        stop_continuous_recording()
        return "Conversation ended. Waiting for wake word."
    
    # Placeholder command implementations
    responses = {
        "weather": f"Weather information for {param}: Currently sunny with a temperature of 72°F.",
        "calendar": f"Calendar: {param}. You have 3 events scheduled for today.",
        "timer": f"Timer set for {param} minutes.",
        "alarm": f"Alarm set for {param}.",
        "music": f"Playing music: {param}.",
        "search": f"Web search results for '{param}' found.",
        "reminder": f"Reminder added: {param}.",
        "news": f"Latest news on {param}: Three new developments reported today."
    }
    
    # Return the placeholder response or generic message
    return responses.get(cmd.lower(), f"Command {cmd} executed with parameter {param}")