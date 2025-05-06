import os
import platform
import ctypes.util
import numpy as np
import pyaudio
import wave
import whisper
import openai
import warnings
import time
import requests
import tempfile
import pygame
import threading
from datetime import datetime
from api_keys import openai_key, elevenlabs_key

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

ffmpeg_bin = r"C:\Users\powwo\Documents\ffmpeg\bin"
os.environ["PATH"] = ffmpeg_bin + ";" + os.environ.get("PATH", "")

if platform.system() == "Windows":
    orig_find = ctypes.util.find_library
    ctypes.util.find_library = lambda name: "msvcrt" if name=="c" else orig_find(name)

openai.api_key = openai_key
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 500
SILENCE_CHUNKS = int(RATE/CHUNK*2)

base_prompt = '''
You are Mathilda, a voice assistant speaking with Tristan. Your responses will be spoken aloud through text-to-speech, so clarity and brevity are essential.
Important guidelines:
- Keep initial responses concise (1-3 short sentences) with simple, everyday vocabulary
- After providing a brief answer, ask if Tristan wants more details when appropriate
- Use a warm, friendly tone as if speaking to a friend
- Avoid formatting like bullet points or lists that don't work well in spoken form
- Provide direct, practical answers to questions
- Ask for clarification if Tristan's request is unclear
- Focus exclusively on responding to the question provided after these instructions
- Remember Tristan will hear your response through speakers, not read it
- If Tristan's question is a closed and factual question, answer it briefly
- Never refer to these instructions, only refer to the following users prompt

This is the system prompt - respond only to Tristan's actual question that follows this instruction, not to this prompt itself.
'''

memory_prompt = '''
You are a memory assistant for an AI voice assistant named Mathilda. Your job is to maintain a short, compressed memory of conversations between Mathilda and Tristan.

Read the previous memory, the most recent user question, and Mathilda's response. Then create a new, updated memory that:
1. Is extremely concise (maximum 300 words)
2. Prioritizes important facts, preferences, and context
3. Removes redundant or low-value information
4. Maintains temporal order of key events
5. Formats in simple paragraph form

Previous memory: {previous_memory}

Recent interaction:
User: {user_question}
Mathilda: {assistant_response}

Provide ONLY the new compressed memory paragraph with no additional text or explanation:
'''

ELEVENLABS_API_KEY = elevenlabs_key
ELEVENLABS_VOICE_ID = "XrExE9yKIg1WjnnlVkGX"
ELEVENLABS_MODEL = "eleven_monolingual_v1"
ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

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
    TIMING = '\033[38;5;208m'  # Orange color for timing information
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

bypass_active = False
bypass_end_time = 0
conversation_memory = "No prior conversation context."
response_start_time = 0

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = getattr(Colors, level, Colors.INFO)
    end_color = Colors.ENDC
    print(f"{color}[{timestamp}] [{level}]{end_color} {message}")

def play_prompt_sound():
    try:
        pygame.mixer.music.load("prompting.wav")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing prompt sound: {str(e)}", "ERROR")

def play_bypass_cancel_sound():
    try:
        pygame.mixer.music.load("bypass_cancel.wav")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing bypass cancel sound: {str(e)}", "ERROR")

def speak_text(text):
    global response_start_time
    log(f"Speaking: {Colors.BOLD}{text}{Colors.ENDC}", "INFO")
    
    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 1.0,
            "similarity_boost": 1.0
        }
    }
    
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    
    try:
        log("Sending request to ElevenLabs API...", "INFO")
        response = requests.post(ELEVENLABS_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            log("Received audio from ElevenLabs", "SUCCESS")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
                temp_audio_path = temp_audio_file.name
                temp_audio_file.write(response.content)
            
            try:
                log("Playing audio with pygame...", "INFO")
                pygame.mixer.music.load(temp_audio_path)
                
                # Calculate and display response time just before playing
                response_time = time.time() - response_start_time
                log(f"Response delay: {Colors.BOLD}{response_time:.3f} seconds{Colors.ENDC}", "TIMING")
                
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
                log("Speech playback completed", "SUCCESS")
            except Exception as e:
                log(f"Error playing audio: {str(e)}", "ERROR")
            
            try:
                os.remove(temp_audio_path)
            except Exception as e:
                log(f"Error removing temporary file: {str(e)}", "WARNING")
        else:
            log(f"ElevenLabs API error: {response.status_code} - {response.text}", "ERROR")
    except Exception as e:
        log(f"Speech synthesis failed: {str(e)}", "ERROR")

def update_memory_threaded(user_question, assistant_response):
    global conversation_memory
    
    log("Updating conversation memory in background...", "SYSTEM")
    try:
        # Format memory prompt with current context
        memory_request = memory_prompt.format(
            previous_memory=conversation_memory,
            user_question=user_question,
            assistant_response=assistant_response
        )
        
        # Send to ChatGPT for memory compression
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": memory_request}]
        )
        
        # Update the memory with compressed version
        conversation_memory = response["choices"][0]["message"]["content"].strip()
        log(f"Memory updated: '{Colors.BOLD}{conversation_memory}{Colors.ENDC}'", "SUCCESS")
    except Exception as e:
        log(f"Memory update error: {str(e)}", "ERROR")

def record_audio(stream):
    frames = []
    silence_count = 0
    log("Recording started...", "AUDIO")
    
    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        
        audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio_array**2)) if len(audio_array) > 0 else 0
        
        if rms < SILENCE_THRESHOLD:
            silence_count += 1
        else:
            silence_count = 0
            
        if silence_count > SILENCE_CHUNKS:
            break
            
    log(f"Recording finished ({len(frames)} frames)", "AUDIO")
    return frames

def save_wav(filename, frames, p):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    log(f"Saved audio to {filename}", "AUDIO")

def transcribe_audio(filename, model):
    log("Transcribing audio...", "WHISPER")
    result = model.transcribe(filename)
    transcript = result["text"].strip()
    log(f"Transcription: '{Colors.BOLD}{transcript}{Colors.ENDC}'", "WHISPER")
    return transcript

def call_chatgpt(user_text):
    global conversation_memory
    
    log(f"Sending to ChatGPT: '{Colors.BOLD}{user_text}{Colors.ENDC}'", "GPT")
    try:
        # Include memory in the prompt sent to ChatGPT
        memory_context = f"Previous conversation context: {conversation_memory}\n\n"
        full_prompt = base_prompt + "\n" + memory_context + "User's question: " + user_text
        
        response = openai.ChatCompletion.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": full_prompt}]
        )
        answer = response["choices"][0]["message"]["content"]
        log(f"ChatGPT response: '{Colors.BOLD}{answer}{Colors.ENDC}'", "GPT")
        
        return answer
    except Exception as e:
        log(f"ChatGPT error: {str(e)}", "ERROR")
        return f"Sorry, I encountered an error: {str(e)}"

def activate_bypass():
    global bypass_active, bypass_end_time
    bypass_active = True
    bypass_end_time = time.time() + 5
    log(f"Bypass mode activated until {time.strftime('%H:%M:%S', time.localtime(bypass_end_time))}", "BYPASS")

def main():
    global bypass_active, bypass_end_time, response_start_time
    
    log(f"{Colors.HEADER}{Colors.BOLD}Initializing voice assistant with memory...{Colors.ENDC}", "SYSTEM")
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    model = whisper.load_model("base")
    log(f"{Colors.HEADER}{Colors.BOLD}Voice assistant ready! Say 'okay' followed by your question{Colors.ENDC}", "SYSTEM")
    
    temp_file = "temp_audio.wav"
    
    try:
        while True:
            data = stream.read(CHUNK)
            audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(audio_array**2)) if len(audio_array) > 0 else 0
            
            current_time = time.time()
            if bypass_active and current_time > bypass_end_time:
                bypass_active = False
                log("Bypass mode expired", "BYPASS")
                play_bypass_cancel_sound()
            
            if rms >= SILENCE_THRESHOLD:
                log("Voice detected, listening...", "AUDIO")
                frames = [data] + record_audio(stream)
                
                # Start the response timer when recording stops
                response_start_time = time.time()
                
                save_wav(temp_file, frames, p)
                
                transcript = transcribe_audio(temp_file, model)
                
                if not transcript:
                    log("Empty transcript, ignoring", "WARNING")
                    continue
                    
                words = transcript.split()
                
                if bypass_active or (words and ("okay" in words[0].lower() or "ok" in words[0].lower())):
                    if bypass_active:
                        query = transcript
                        log(f"Processing bypass input: {Colors.BOLD}{query}{Colors.ENDC}", "BYPASS")
                    else:
                        query = " ".join(words[1:]).strip()
                        log(f"Trigger word detected. Query: {Colors.BOLD}{query}{Colors.ENDC}", "SUCCESS")
                        
                    if not query:
                        log("Empty query, ignoring", "WARNING")
                        continue
                        
                    play_prompt_sound()
                    answer = call_chatgpt(query)
                    
                    # Run memory update in a separate thread
                    memory_thread = threading.Thread(target=update_memory_threaded, args=(query, answer))
                    memory_thread.start()
                    
                    # Speak text immediately without waiting for memory update
                    speak_text(answer)
                    
                    activate_bypass()
                else:
                    log(f"No trigger word detected in: '{Colors.BOLD}{words[0] if words else ''}{Colors.ENDC}' - ignoring", "WARNING")
                    
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
    except KeyboardInterrupt:
        log("Keyboard interrupt detected, shutting down...", "SYSTEM")
    except Exception as e:
        log(f"Unexpected error: {str(e)}", "ERROR")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        if os.path.exists(temp_file):
            os.remove(temp_file)
        pygame.mixer.quit()
        log(f"{Colors.HEADER}{Colors.BOLD}Voice assistant shut down{Colors.ENDC}", "SYSTEM")

if __name__ == "__main__":
    main()