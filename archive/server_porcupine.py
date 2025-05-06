import os
import platform
import ctypes.util
import numpy as np
import pyaudio
import wave
import whisper
import openai
import requests
import warnings
import time
import random
import tempfile
import pygame
import threading
import re
import queue
import pvporcupine
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dotenv import load_dotenv
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

# Set OpenAI API key for chat and TTS
openai.api_key = os.getenv("OPENAI_API_KEY")

# Audio recording constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Porcupine requires 16kHz
SILENCE_THRESHOLD = 500
SILENCE_CHUNKS = int(RATE / CHUNK * 2)
BYPASS_DELAY = 5
current_rms = 0

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

memory_prompt = '''
You are a memory assistant for an AI voice assistant named Nova. Your job is to maintain a short, compressed memory of conversations between Nova and Tristan.

Read the previous memory, the most recent user question, and Nova's response. Then create a new, updated memory that:
1. Is extremely concise (maximum 300 words)
2. Prioritizes important facts, preferences, and context
3. Removes redundant or low-value information
4. Maintains temporal order of key events
5. Formats in simple paragraph form

Previous memory: {previous_memory}

Recent interaction:
User: {user_question}
Nova: {assistant_response}

Provide ONLY the new compressed memory paragraph with no additional text or explanation:
'''

# Initialize pygame for audio playback
pygame.mixer.init()

class Colors:
    HEADER = '\033[95m'
    INFO = '\033[94m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    AUDIO = '\033[96m'
    WHISPER = '\033[95m'
    GPT = '\033[92m'
    BYPASS = '\033[93m'
    SYSTEM = '\033[97m'
    TIMING = '\033[38;5;208m'
    COMMAND = '\033[38;5;219m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Global state
bypass_active = False
bypass_end_time = 0
conversation_memory = "No prior conversation context."
prompt_end_time = 0

# Timing metrics
transcription_start = transcription_end = 0
chat_start = chat_end = 0
tts_start = tts_end = 0

# TTS Parameters for faster generation
TTS_VOICE = "nova"
TTS_MODEL = "tts-1"
TTS_SPEED = 1.0  # 1.0 is normal speed

# Command pattern for extracting commands
COMMAND_PATTERN = r'\[/(\w+):([^\]]+)\]'

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = getattr(Colors, level, Colors.INFO)
    print(f"{color}[{timestamp}] [{level}]{Colors.ENDC} {message}")

def play_sound(filename):
    try:
        filepath = os.path.join("assets", filename)
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing sound {filename}: {e}", "ERROR")

def play_prompt_sound():
    play_sound("prompting.wav")

def play_bypass_start_sound():
    play_sound("bypass_start.wav")

def play_bypass_cancel_sound():
    play_sound("bypass_cancel.wav")

def record_audio(stream):
    global prompt_end_time
    frames = []
    silence_count = 0
    log("Recording started...", "AUDIO")
    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio**2))
        current_rms = round(rms)
        if rms < SILENCE_THRESHOLD:
            silence_count += 1
            if silence_count > SILENCE_CHUNKS:
                break
        else:
            silence_count = 0
    current_rms = 0
    prompt_end_time = time.time()
    log(f"Recording finished ({len(frames)} frames)", "AUDIO")
    return frames

def save_wav(filename, frames, pa):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pa.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    log(f"Saved audio to {filename}", "AUDIO")

def transcribe_audio(filename, model):
    global transcription_start, transcription_end
    log("Transcribing audio...", "WHISPER")
    transcription_start = time.time()
    result = model.transcribe(filename)
    transcription_end = time.time()
    text = result.get("text", "").strip()
    log(f"Transcription duration: {Colors.BOLD}{(transcription_end-transcription_start):.3f}s{Colors.ENDC}", "TIMING")
    log(f"Transcription result: {Colors.BOLD}{text}{Colors.ENDC}", "WHISPER")
    return text

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

def download_tts(sentence):
    """Return the path of a temp file that already contains the TTS audio."""
    payload = {
        "model": TTS_MODEL,
        "voice": TTS_VOICE,
        "input": sentence,
        "speed": TTS_SPEED,
        "format": "opus"
    }
    headers = {
        "Authorization": f"Bearer {os.getenv("OPENAI_API_KEY")}",
        "Content-Type": "application/json"
    }

    resp = requests.post(
        "https://api.openai.com/v1/audio/speech",
        json=payload,
        headers=headers,
        stream=True,
        timeout=30
    )
    resp.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".opus")
    for chunk in resp.iter_content(chunk_size=8192):
        if chunk:
            tmp.write(chunk)
    tmp.close()
    return tmp.name

def play_audio(path, audio_stream):
    """Play audio file while listening for interruptions, then delete it."""
    sound = pygame.mixer.Sound(path)
    ch = sound.play()
    
    while ch.get_busy():
        # Check for potential interruption while playing
        pcm = audio_stream.read(CHUNK, exception_on_overflow=False)
        audio = np.frombuffer(pcm, dtype=np.int16)
        rms = np.sqrt(np.mean(audio**2))
        
        # If loud sound detected, stop playback and start recording
        if rms > SILENCE_THRESHOLD:
            ch.stop()
            pygame.mixer.stop()
            return True  # Signal that interruption occurred
            
        pygame.time.Clock().tick(10)
    
    os.remove(path)
    return False  # No interruption

def split_into_sentences(text):
    """Split text into sentences for parallel TTS processing"""
    # Handle common sentence-ending punctuation and keep the punctuation
    pattern = r'(?<=[.!?])\s+'
    sentences = re.split(pattern, text)
    
    # Make sure sentences aren't too long - split long sentences
    result = []
    for sentence in sentences:
        if len(sentence) > 100:  # If sentence is very long
            # Split by commas, semicolons, etc.
            parts = re.split(r'(?<=[,;:])\s+', sentence)
            result.extend(parts)
        else:
            result.append(sentence)
    
    return result

def speak_text(text, audio_stream):
    """Stream TTS by splitting text into sentences and processing them in parallel"""
    global tts_start, tts_end
    
    # Clean text and extract commands
    clean_text, commands = extract_commands(text)
    
    log(f"Speaking: {Colors.BOLD}{clean_text}{Colors.ENDC}", "INFO")
    if commands:
        log(f"Commands detected: {len(commands)}", "COMMAND")
    
    # Execute commands if any
    for cmd, param in commands:
        result = execute_command(cmd, param)
        log(f"Command result: {result}", "COMMAND")
    
    tts_start = time.time()
    
    # Split into sentences
    sentences = split_into_sentences(clean_text)
    log(f"Split response into {len(sentences)} sentences", "INFO")

    # Parallel download + sequential playback with interruption checking
    interrupted = False
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download_tts, s) for s in sentences]

        for i, fut in enumerate(futures):
            if interrupted:
                break
                
            path = fut.result()
            if i == 0:
                log(f"Total latency from speech end to TTS start {(tts_start - prompt_end_time):.3f}s", "TIMING")
                
            # Play audio and check for interruption
            interrupted = play_audio(path, audio_stream)
            
            if interrupted:
                # Cancel remaining sentence playback
                log("Speech interrupted by user", "INFO")
                # Clean up downloaded files that won't be played
                for remaining in futures[i+1:]:
                    if remaining.done():
                        try:
                            os.remove(remaining.result())
                        except:
                            pass
                return True  # Signal that interruption occurred
    
    tts_end = time.time()
    log(f"All audio ready and spoken in {(tts_end - tts_start):.3f}s", "TIMING")
    return False  # No interruption occurred

def call_chatgpt(question):
    global chat_start, chat_end, conversation_memory
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
    # Update memory asynchronously
    threading.Thread(target=update_memory_threaded, args=(question, answer), daemon=True).start()
    return answer

def update_memory_threaded(user_question, assistant_response):
    global conversation_memory
    try:
        memory_req = memory_prompt.format(
            previous_memory=conversation_memory,
            user_question=user_question,
            assistant_response=assistant_response
        )
        mem_resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": memory_req}]
        )
        conversation_memory = mem_resp.choices[0].message.content.strip()
    except Exception as e:
        log(f"Memory update error: {e}", "ERROR")

def process_voice_query(frames, pa, whisper_model, audio_stream):
    global bypass_active, bypass_end_time
    
    # Save recorded audio to a temporary file
    save_wav("temp.wav", frames, pa)
    
    # Transcribe the recorded audio
    query = transcribe_audio("temp.wav", whisper_model)
    os.remove("temp.wav")
    
    if not query:
        return
    
    log(f"Query: {Colors.BOLD}{query}{Colors.ENDC}", "SUCCESS")
    
    if bypass_active:
        play_prompt_sound()
    
    # Process query with ChatGPT and speak response
    answer = call_chatgpt(query)
    interrupted = speak_text(answer, audio_stream)
    
    # If user interrupted, we'll immediately handle their next query
    if not interrupted:
        # Enable bypass mode for follow-up questions
        bypass_active = True
        bypass_end_time = time.time() + BYPASS_DELAY
        
    # Immediately start listening for the next query if interrupted
    if interrupted:
        # Small pause to let user start speaking
        time.sleep(0.2)
        new_frames = record_audio(audio_stream)
        process_voice_query(new_frames, pa, whisper_model, audio_stream)

def main():
    global bypass_active, bypass_end_time
    
    log("Initializing voice assistant...", "SYSTEM")
    
    # Initialize PyAudio
    pa = pyaudio.PyAudio()
    
    # Initialize Whisper for transcription (not wake word detection)
    whisper_model = whisper.load_model("tiny")
    
    # Initialize Porcupine for wake word detection
    porcupine = None
    try:
        # Create Porcupine instance to detect "computer" wake word
        porcupine = pvporcupine.create(
            access_key=os.getenv("PORCUPINE_ACCESS_KEY"),
            keywords=["computer"]
        )
        
        # Open audio stream with Porcupine's required parameters
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )
        
        log("Startup complete. Say 'Computer' to activate.", "SYSTEM")
        
        while True:
            # Read audio frame for wake word detection
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_data = np.frombuffer(pcm, dtype=np.int16)
            
            # Check if wake word detected
            keyword_index = porcupine.process(pcm_data)
            
            # Check if bypass mode expired
            if bypass_active and time.time() > bypass_end_time:
                bypass_active = False
                play_bypass_cancel_sound()
            
            # If wake word detected or in bypass mode
            if keyword_index >= 0 or bypass_active:
                if keyword_index >= 0:
                    log("Wake word 'Computer' detected!", "SUCCESS")
                    play_bypass_start_sound()
                
                # Start recording audio for query
                frames = record_audio(audio_stream)
                
                # Process the voice query in a separate thread to keep the main loop responsive
                threading.Thread(
                    target=process_voice_query, 
                    args=(frames, pa, whisper_model, audio_stream), 
                    daemon=True
                ).start()
                
    except Exception as e:
        log(f"Error: {e}", "ERROR")
    finally:
        # Clean up resources
        if porcupine is not None:
            porcupine.delete()
        
        if 'audio_stream' in locals() and audio_stream is not None:
            audio_stream.close()
        
        pa.terminate()

if __name__ == "__main__":
    main()