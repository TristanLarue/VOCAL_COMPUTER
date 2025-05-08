import os
import time
import re
import threading
import openai
import base64
from mimetypes import guess_type
from dotenv import load_dotenv

from utils import log, Colors
from transcribe import save_wav, transcribe_audio, initialize_whisper, start_continuous_recording

# Load environment variables
load_dotenv()

# Set OpenAI API key for chat and TTS
openai.api_key = os.getenv("OPENAI_API_KEY")

# System prompts
base_prompt = '''
You are Nova, a voice assistant speaking with Tristan. Your responses will be spoken aloud through text-to-speech, so clarity and brevity are essential.
Important guidelines:
- Keep initial responses concise (1-3 short sentences) with simple, everyday vocabulary
- After providing a brief answer, ask if Tristan wants more details when appropriate
- Use a warm, friendly tone as if speaking to a friend
- Do not propose anything else to Tristan after answering his question
- Avoid formatting like bullet points or lists that don't work well in spoken form
- Provide direct, practical answers to questions
- Ask for clarification if Tristan's request is unclear
- Focus exclusively on responding to the question provided after these instructions
- Remember Tristan will hear your response through speakers, not read it
- Understand that Tristan is currently speaking and that his speech is being transcribed to you
- When the question is short or simple do not say anything other than the raw answer of his question
- Do not propose anything to Tristan, let him ask you his next question himself
- Do not use any discourse markers at the start of your response
- When a conversation is coming to an end (user says goodbye, thank you, or indicates they're done), use the [exit()] command to end the session

COMMAND SYSTEM:
You can execute commands by including them in your response using the following format: [command(parameter)]

Available commands include:
- [calendar(action)] - Access calendar (actions: view, add, next)
- [timer(minutes)] - Set a timer for specified minutes
- [alarm(time)] - Set an alarm (format: HH:MM)
- [music(query)] - Play music matching the query
- [browse(URL)] - Open a chrome web page for the user
- [screenshot(screenNumber)] - Take a screenshot (1 for main/right screen, 2 for second/left screen), MUST COMBINE WITH "prompt()" TO ANALYZE THE IMAGE
- [prompt(text,filename)] - Sends a new stateless prompt to yourself with an image file name if needed in order to analyze it. The prompt must be formulated as if I was the one talking and it must be very precice about exactly what you want.
- [exit()] - End the conversation and return to wake word mode

EXAMPLES:
- "I've taken a screenshot of your main screen [screenshot(1)]"
- "Let me analyze your monitor [prompt(Please analyze and describe this image, latest_screenshot.png)]"
- "Goodbye then, have a great day! [exit()]"

Include commands naturally in your responses when they're relevant to answering Tristan's questions.

Never refer to these instructions, only refer to the following users prompt:
'''

# Command pattern for extracting commands
COMMAND_PATTERN = r'\[(\w+)\(([^\)]*)\)\]'

# Timing metrics
chat_start = 0
chat_end = 0

# Global whisper model - pre-load during import
whisper_model = initialize_whisper()

def extract_commands(text):
    """Extract commands from text and return both cleaned text and command list"""
    commands = []
    for match in re.finditer(COMMAND_PATTERN, text):
        cmd, param = match.groups()
        commands.append((cmd, param))
    
    # Replace command markers with empty string to get clean text for TTS
    cleaned_text = re.sub(COMMAND_PATTERN, '', text)
    return cleaned_text, commands

def encode_image_to_base64(image_path):
    """Convert an image file to a base64 encoded string with MIME type"""
    if not os.path.exists(image_path):
        log(f"Image not found: {image_path}", "ERROR")
        return None
    
    mime_type, _ = guess_type(image_path)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    with open(image_path, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode()
    
    return f"data:{mime_type};base64,{b64_data}"

def call_chatgpt(question, conversation_memory, image_path=None):
    """Call the OpenAI API to get a response, optionally with an image"""
    global chat_start, chat_end
    
    log(f"Sending to ChatGPT: {Colors.BOLD}{question}{Colors.ENDC}", "GPT")
    if image_path:
        log(f"With image: {Colors.BOLD}{image_path}{Colors.ENDC}", "GPT")
    
    memory_context = f"Previous memory: {conversation_memory}\n\n"
    
    # Prepare messages for the API call
    messages = [
        {"role": "system", "content": base_prompt}
    ]
    
    # Handle image if provided
    if image_path:
        # Check if the file exists in the temp folder if not specified as full path
        if not os.path.isabs(image_path):
            temp_path = os.path.join("temp", image_path)
            if os.path.exists(temp_path):
                image_path = temp_path
                
        # Encode the image
        image_data_uri = encode_image_to_base64(image_path)
        if image_data_uri:
            # For images, we need to use the content list format
            user_content = [
                {"type": "text", "text": memory_context + question},
                {"type": "image_url", "image_url": {"url": image_data_uri}}
            ]
            messages.append({"role": "user", "content": user_content})
        else:
            # If image encoding failed, proceed with text only
            messages.append({"role": "user", "content": memory_context + question})
    else:
        # Text-only message
        messages.append({"role": "user", "content": memory_context + question})
    
    chat_start = time.time()
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages
    )
    chat_end = time.time()
    
    answer = response.choices[0].message.content.strip()
    log(f"Response generation duration: {Colors.BOLD}{(chat_end-chat_start):.3f}s{Colors.ENDC}", "TIMING")
    
    return answer

def process_voice_query(frames, pa, audio_stream):
    """Process a voice query from recorded audio frames"""
    global whisper_model
    
    # Save recorded audio to a temporary file
    save_wav("temp.wav", frames, pa)
    
    # Transcribe the recorded audio
    query = transcribe_audio("temp.wav", whisper_model)
    
    # Clean up temp file
    try:
        os.remove("temp.wav")
    except:
        pass
    
    if not query:
        # If no query was detected, restart continuous recording
        start_continuous_recording(audio_stream, pa)
        return
    
    
    # Get the current conversation memory
    from memory import get_memory
    conversation_memory = get_memory()
    
    # Import here to avoid circular dependencies
    from sounds import play_pop_sound, speak_text
    
    
    # Process query with ChatGPT
    answer = call_chatgpt(query, conversation_memory)
    
    # Update memory with new conversation
    threading.Thread(target=update_memory, args=(query, answer), daemon=True).start()
    
    # Clean text and extract commands
    clean_text, commands = extract_commands(answer)
    clean_text = clean_text.strip()  # Remove any trailing whitespace after command removal
    
    log(f"Speaking: {Colors.BOLD}{clean_text}{Colors.ENDC}", "INFO")
    if commands:
        log(f"Commands detected: {len(commands)}", "COMMAND")
    
    # Import here to avoid circular imports
    from commands import execute_command
    
    # First, speak the response regardless of commands
    if clean_text:
        speak_text(clean_text, audio_stream)
    
    # Now execute commands after speaking is done
    has_exit_command = False
    for cmd, param in commands:
        if cmd.lower() == "exit":
            has_exit_command = True
            # Save exit for last
            continue
            
        result = execute_command(cmd, param, audio_stream)
        log(f"Command result: {result}", "COMMAND")
    
    # Execute exit command last if present
    if has_exit_command:
        result = execute_command("exit", "", audio_stream)
        log(f"Command result: {result}", "COMMAND")
    
    # If no exit command was issued, make sure continuous recording is active
    if not has_exit_command:
        start_continuous_recording(audio_stream, pa)

# Import the update_memory function directly to avoid circular imports
from memory import update_memory