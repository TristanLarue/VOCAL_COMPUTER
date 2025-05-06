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
import tempfile
import pygame
import threading
import re
import queue
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from api_keys import openai_key

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
openai.api_key = openai_key

# Audio recording constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 500
SILENCE_CHUNKS = int(RATE / CHUNK * 2)

# TTS Parameters
TTS_VOICE = "nova"
TTS_MODEL = "tts-1"
TTS_SPEED = 1.0

# System prompts (preserved as requested)
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

# Command pattern for extracting commands
COMMAND_PATTERN = r'\[/(\w+):([^\]]+)\]'

# Initialize pygame for audio playback
pygame.mixer.init()

class Colors:
    INFO = '\033[94m'
    SUCCESS = '\033[92m'
    ERROR = '\033[91m'
    WHISPER = '\033[95m'
    GPT = '\033[92m'
    TIMING = '\033[38;5;208m'
    COMMAND = '\033[38;5;219m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Global state management
class State:
    def __init__(self):
        self.conversation_memory = "No prior conversation context."
        self.voice_active = False
        self.is_speaking = False
        self.stop_speaking = threading.Event()
        self.transcription_queue = queue.Queue()
        self.response_queue = queue.Queue()

# Logging function
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = getattr(Colors, level, Colors.INFO)
    print(f"{color}[{timestamp}]{Colors.ENDC} {message}")

# Audio Functions
class AudioListener:
    def __init__(self, state):
        self.state = state
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=FORMAT, 
            channels=CHANNELS, 
            rate=RATE, 
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self.audio_callback
        )
        self.frames = []
        self.silence_count = 0
        self.is_recording = False
        self.transcription_start = 0
        self.transcription_end = 0
        
        # Initialize Whisper model
        self.whisper_model = whisper.load_model("tiny")
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_audio, daemon=True)
        self.processing_thread.start()
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            log(f"Stream error: {status}", "ERROR")
        
        audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio**2))
        
        # Voice activity detection
        if not self.is_recording and rms >= SILENCE_THRESHOLD:
            self.is_recording = True
            self.frames = []
            self.silence_count = 0
            log("Voice detected", "INFO")
            self.state.voice_active = True
            
            # Stop any ongoing TTS if voice is detected
            if self.state.is_speaking:
                self.state.stop_speaking.set()
                log("Stopping current AI response", "INFO")
        
        # Continue recording if active
        if self.is_recording:
            self.frames.append(in_data)
            
            # Check for silence to determine end of speech
            if rms < SILENCE_THRESHOLD:
                self.silence_count += 1
                if self.silence_count > SILENCE_CHUNKS:
                    log("Voice stopped", "INFO")
                    self.state.voice_active = False
                    self.is_recording = False
                    
                    # Process the recorded audio
                    threading.Thread(target=self.transcribe_speech, args=(self.frames[:],), daemon=True).start()
                    self.frames = []
            else:
                self.silence_count = 0
        
        return (in_data, pyaudio.paContinue)
    
    def transcribe_speech(self, frames):
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            filename = temp_file.name
            wf = wave.open(filename, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.pa.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
        
        # Transcribe
        self.transcription_start = time.time()
        try:
            result = self.whisper_model.transcribe(filename)
            text = result.get("text", "").strip()
            
            self.transcription_end = time.time()
            transcription_time = self.transcription_end - self.transcription_start
            
            log(f"Transcription result: {Colors.BOLD}{text}{Colors.ENDC}", "WHISPER")
            log(f"Voice transcription time: {Colors.BOLD}{transcription_time:.3f}s{Colors.ENDC}", "TIMING")
            
            # Check if this contains trigger word "nova"
            if "nova" in text.lower():
                # Extract query (everything after "nova")
                words = text.lower().split("nova", 1)
                if len(words) > 1:
                    query = words[1].strip()
                    if query:
                        self.state.transcription_queue.put(query)
            
        except Exception as e:
            log(f"Transcription error: {e}", "ERROR")
        
        finally:
            # Clean up temp file
            try:
                os.remove(filename)
            except:
                pass
    
    def process_audio(self):
        """Background thread to continuously process audio"""
        while True:
            time.sleep(0.1)  # Prevent CPU hogging
    
    def start(self):
        self.stream.start_stream()
        log("Audio listener started", "INFO")
    
    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
        log("Audio listener stopped", "INFO")

class ResponseProcessor:
    def __init__(self, state):
        self.state = state
        self.processing_thread = threading.Thread(target=self.process_responses, daemon=True)
        self.processing_thread.start()
        
    def process_responses(self):
        while True:
            try:
                query = self.state.transcription_queue.get(timeout=1)
                if query:
                    # Generate response from ChatGPT
                    self.generate_response(query)
                self.state.transcription_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                log(f"Response processing error: {e}", "ERROR")
    
    def generate_response(self, query):
        log(f"Query: {Colors.BOLD}{query}{Colors.ENDC}", "INFO")
        
        # Call ChatGPT
        chat_start = time.time()
        try:
            memory_context = f"Previous memory: {self.state.conversation_memory}\n\n"
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": base_prompt},
                    {"role": "user", "content": memory_context + query}
                ]
            )
            
            answer = response.choices[0].message.content.strip()
            chat_end = time.time()
            chat_time = chat_end - chat_start
            
            log(f"ChatGPT response: {Colors.BOLD}{answer}{Colors.ENDC}", "GPT")
            log(f"ChatGPT text response generation time: {Colors.BOLD}{chat_time:.3f}s{Colors.ENDC}", "TIMING")
            
            # Update memory asynchronously
            threading.Thread(target=self.update_memory, 
                            args=(query, answer), 
                            daemon=True).start()
            
            # Send to TTS processor
            self.speak_response(answer)
            
        except Exception as e:
            log(f"ChatGPT API error: {e}", "ERROR")
    
    def update_memory(self, user_question, assistant_response):
        try:
            memory_req = memory_prompt.format(
                previous_memory=self.state.conversation_memory,
                user_question=user_question,
                assistant_response=assistant_response
            )
            
            mem_resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": memory_req}]
            )
            
            self.state.conversation_memory = mem_resp.choices[0].message.content.strip()
        except Exception as e:
            log(f"Memory update error: {e}", "ERROR")
    
    def extract_commands(self, text):
        """Extract commands from text and return both cleaned text and command list"""
        commands = []
        for match in re.finditer(COMMAND_PATTERN, text):
            cmd, param = match.groups()
            commands.append((cmd, param))
        
        # Replace command markers with their parameters
        cleaned_text = re.sub(COMMAND_PATTERN, r'\2', text)
        return cleaned_text, commands
    
    def execute_command(self, cmd, param):
        """Execute a command with its parameter (placeholder implementations)"""
        log(f"Executing command: /{cmd}:{param}", "COMMAND")
        
        # Placeholder command implementations
        responses = {
            "weather": f"Getting weather for {param}.",
            "calendar": f"Accessing calendar: {param}.",
            "timer": f"Timer set for {param} minutes.",
            "alarm": f"Alarm set for {param}.",
            "music": f"Playing music: {param}.",
            "search": f"Web search results for '{param}' found.",
            "reminder": f"Reminder added: {param}.",
            "news": f"Latest news on {param}."
        }
        
        # Return the placeholder response or generic message
        return responses.get(cmd.lower(), f"Command {cmd} executed with parameter {param}")
    
    def split_into_sentences(self, text):
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
    
    def download_tts(self, sentence):
        """Return the path of a temp file that already contains the TTS audio."""
        payload = {
            "model": TTS_MODEL,
            "voice": TTS_VOICE,
            "input": sentence,
            "speed": TTS_SPEED,
            "format": "opus"
        }
        headers = {
            "Authorization": f"Bearer {openai_key}",
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

    def speak_response(self, text):
        # Reset stop flag
        self.state.stop_speaking.clear()
        self.state.is_speaking = True
        
        # Clean text and extract commands
        clean_text, commands = self.extract_commands(text)
        
        # Execute commands if any
        for cmd, param in commands:
            self.execute_command(cmd, param)
        
        # Split into sentences
        sentences = self.split_into_sentences(clean_text)
        
        tts_start = time.time()
        
        # Download all audio files in parallel first
        audio_paths = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(self.download_tts, s) for s in sentences]
            
            # Collect results
            for future in futures:
                try:
                    path = future.result()
                    audio_paths.append(path)
                except Exception as e:
                    log(f"TTS download error: {e}", "ERROR")
        
        # Play audio files sequentially, allowing interruptions
        for i, path in enumerate(audio_paths):
            if self.state.stop_speaking.is_set():
                log("Speech playback interrupted", "INFO")
                break
                
            try:
                sound = pygame.mixer.Sound(path)
                channel = sound.play()
                while channel.get_busy() and not self.state.stop_speaking.is_set():
                    pygame.time.Clock().tick(10)
                    
            except Exception as e:
                log(f"Audio playback error: {e}", "ERROR")
            finally:
                # Clean up temp file
                try:
                    os.remove(path)
                except:
                    pass
        
        # TTS completion timing
        if not self.state.stop_speaking.is_set():
            tts_end = time.time()
            tts_time = tts_end - tts_start
            log(f"ChatGPT speech response generation time: {Colors.BOLD}{tts_time:.3f}s{Colors.ENDC}", "TIMING")
        
        self.state.is_speaking = False

def main():
    log("Initializing Nova Voice Assistant...", "INFO")
    
    # Create shared state
    state = State()
    
    # Initialize components
    audio_listener = AudioListener(state)
    response_processor = ResponseProcessor(state)
    
    # Start audio listener
    audio_listener.start()
    
    log("Nova Voice Assistant is ready. Say 'Hey Nova,' followed by your question.", "INFO")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        log("Shutting down...", "INFO")
        audio_listener.stop()

if __name__ == "__main__":
    main()