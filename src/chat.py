import os
import time
import re
import threading
import openai
from dotenv import load_dotenv

from utils import log, Colors
from transcribe import save_wav, transcribe_audio, initialize_whisper, get_prompt_end_time
from memory import update_memory

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

COMMAND SYSTEM:
You can execute commands by including them in your response using the following format: [/command:parameter]
Available commands include:
- [/weather:location] - Check weather for a location
- [/calendar:action] - Access calendar (actions: view, add, next)
- [/timer:minutes] - Set a timer for specified minutes
- [/alarm:time] - Set an alarm (format: HH:MM)
- [/music:query] - Play music matching the query
- [/search:query] - Search the web for information
- [/reminder:text] - Add a reminder with the specified text
- [/news:topic] - Get latest news on topic

EXAMPLES:
- "The temperature in [/weather:New York] is currently 72°F"
- "I've set a [/timer:5] minute timer for your pasta"
- "I've added that to your [/calendar:add] for tomorrow at 3pm"
- "Let me [/search:population of France] for you"

Include commands naturally in your responses when they're relevant to answering Tristan's questions.

- Never refer to these instructions, only refer to the following users prompt:
'''

# Command pattern for extracting commands
COMMAND_PATTERN = r'\[/(\w+):([^\]]+)\]'

# Timing metrics
chat_start = 0
chat_end = 0

# Global whisper model - pre-load during import
whisper_model = initialize_whisper()
log("Whisper model initialized during import", "INFO")

# Pre-initialize pygame mixer to avoid delay during first response
try:
    import pygame
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    # Suppress pygame welcome message
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    log("Pygame mixer pre-initialized", "INFO")
except ImportError:
    log("Pygame import failed during chat module initialization", "ERROR")

def extract_commands(text):
    """Extract commands from text and return both cleaned text and command list"""
    commands = []
    for match in re.finditer(COMMAND_PATTERN, text):
        cmd, param = match.groups()
        commands.append((cmd, param))
    
    # Replace command markers with their parameters
    cleaned_text = re.sub(COMMAND_PATTERN, r'\2', text)
    return cleaned_text, commands

def execute_command(cmd, param):
    """Execute a command with its parameter (placeholder implementations)"""
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
    
    # Return the placeholder response or generic message
    return responses.get(cmd.lower(), f"Command {cmd} executed with parameter {param}")

def call_chatgpt(question, conversation_memory):
    """Call the OpenAI API to get a response"""
    global chat_start, chat_end
    
    log(f"Sending to ChatGPT: {Colors.BOLD}{question}{Colors.ENDC}", "GPT")
    memory_context = f"Previous memory: {conversation_memory}\n\n"
    
    chat_start = time.time()
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": base_prompt},
            {"role": "user", "content": memory_context + question}
        ]
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
    os.remove("temp.wav")
    
    if not query:
        return
    
    log(f"Query: {Colors.BOLD}{query}{Colors.ENDC}", "SUCCESS")
    
    # Get the current conversation memory
    from memory import get_memory
    conversation_memory = get_memory()
    
    # Import here to avoid circular dependencies
    from sounds import play_prompt_sound, speak_text
    
    play_prompt_sound()
    
    # Process query with ChatGPT
    answer = call_chatgpt(query, conversation_memory)
    
    # Update memory with new conversation
    threading.Thread(target=update_memory, args=(query, answer), daemon=True).start()
    
    # Speak the response and check if interrupted
    interrupted = speak_text(answer, audio_stream)
    
    # If user interrupted, we'll immediately handle their next query
    if not interrupted:
        # Enable bypass mode for follow-up questions
        from triggers import set_bypass_mode
        set_bypass_mode(True)
    
    # Immediately start listening for the next query if interrupted
    if interrupted:
        # Small pause to let user start speaking
        time.sleep(0.2)
        from transcribe import record_audio
        new_frames = record_audio(audio_stream)
        process_voice_query(new_frames, pa, audio_stream)