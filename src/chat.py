import os
import time
import re
import threading
import openai
from dotenv import load_dotenv

from utils import log, Colors
from transcribe import save_wav, transcribe_audio, initialize_whisper, get_prompt_end_time, start_continuous_recording

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
- When a conversation is coming to an end (user says goodbye, thank you, or indicates they're done), use the [/exit:None] command to end the session

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
- [/exit:None] - End the conversation and return to wake word mode

EXAMPLES:
- "The temperature in [/weather:New York] is currently 72°F"
- "I've set a [/timer:5] minute timer for your pasta"
- "I've added that to your [/calendar:add] for tomorrow at 3pm"
- "Let me [/search:population of France] for you"
- "Goodbye then, have a great day! [/exit:None]"

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
    
    # Clean up temp file
    try:
        os.remove("temp.wav")
    except:
        pass
    
    if not query:
        # If no query was detected, restart continuous recording
        start_continuous_recording(audio_stream, pa)
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
    
    # Import here to avoid circular imports
    from commands import execute_command
    
    # Clean text and extract commands
    clean_text, commands = extract_commands(answer)
    
    log(f"Speaking: {Colors.BOLD}{clean_text}{Colors.ENDC}", "INFO")
    if commands:
        log(f"Commands detected: {len(commands)}", "COMMAND")
    
    # Execute commands if any
    for cmd, param in commands:
        result = execute_command(cmd, param, audio_stream)
        log(f"Command result: {result}", "COMMAND")
        
        # If this is an exit command, we should stop TTS immediately
        if cmd.lower() == "exit":
            return True  # Signal interruption to stop further processing

    # Speak the response and check if interrupted
    interrupted = speak_text(clean_text, audio_stream)
    
    # After speech has finished (or if interrupted), make sure continuous recording is active
    start_continuous_recording(audio_stream, pa)

# Import the update_memory function directly to avoid circular imports
from memory import update_memory