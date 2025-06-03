import os
from utils import log

def run(param, audio_stream=None):
    try:
        params = param.split(',', 1)
        prompt_text = params[0].strip()
        filename = params[1].strip() if len(params) > 1 else None

        log(f"Self-prompt command received: '{prompt_text}', file: {filename}", "COMMAND")

        from chat import call_chatgpt
        from memory import get_memory

        conversation_memory = get_memory()

        image_path = None
        if filename:
            temp_path = os.path.join("temp", filename)
            if os.path.exists(temp_path):
                image_path = temp_path
                log(f"Using file from temp directory: {image_path}", "COMMAND")
            elif os.path.exists(filename):
                image_path = filename
                log(f"Using file from absolute path: {image_path}", "COMMAND")
            else:
                log(f"File not found: {filename}", "ERROR")

        response = call_chatgpt(prompt_text, conversation_memory, image_path)

        from sounds import speak_text

        if audio_stream:
            log("Speaking self-prompt response", "COMMAND")
            speak_text(response, audio_stream)

        return f"Self-prompt executed: '{prompt_text}'" + (f" with file: {filename}" if filename else "")
    except Exception as e:
        log(f"Self-prompt command error: {e}", "ERROR")
        return f"Error executing self-prompt: {str(e)}"
