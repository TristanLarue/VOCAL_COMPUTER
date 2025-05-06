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
BYPASS_DELAY = 10

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
- When the answer is short or simple do not say anything other than the raw answer of his question
- Do not propose anything to Tristan, let him ask you his next question himself
- Do not use any discourse markers at the start of your response

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


def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = getattr(Colors, level, Colors.INFO)
    print(f"{color}[{timestamp}] [{level}]{Colors.ENDC} {message}")


def play_prompt_sound():
    try:
        pygame.mixer.music.load("prompting.wav")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing prompt sound: {e}", "ERROR")


def play_bypass_start_sound():
    try:
        pygame.mixer.music.load("bypass_start.wav")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing bypass start sound: {e}", "ERROR")


def play_bypass_cancel_sound():
    try:
        pygame.mixer.music.load("bypass_cancel.wav")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing bypass cancel sound: {e}", "ERROR")

def play_nova_start_sound():
    try:
        folder = r"C:\Users\trist\OneDrive\Desktop\AI_VOCAL\nova_start_sounds"
        files = [f for f in os.listdir(folder) if f.lower().endswith(".wav")]
        if not files:
            raise FileNotFoundError("No .wav files found in nova_start_sounds")
        choice = random.choice(files)
        path = os.path.join(folder, choice)
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing nova start sound: {e}", "ERROR")

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
        if rms < SILENCE_THRESHOLD:
            silence_count += 1
            if silence_count > SILENCE_CHUNKS:
                break
        else:
            silence_count = 0
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


def speak_text(text):
    global tts_start, tts_end
    log(f"Speaking: {Colors.BOLD}{text}{Colors.ENDC}", "INFO")
    play_nova_start_sound()
    payload = {
    "model": "tts-1",
    "voice": "nova",
    "input": text,
    "format": "opus"
}

    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json"
    }
    try:
        tts_start = time.time()
        resp = requests.post("https://api.openai.com/v1/audio/speech", json=payload, headers=headers, stream=True)
        if resp.status_code != 200:
            log(f"OpenAI TTS API error: {resp.status_code} - {resp.text}", "ERROR")
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk: tmp.write(chunk)
            tmp_path = tmp.name
        tts_end = time.time()
        log(f"TTS duration: {Colors.BOLD}{(tts_end-tts_start):.3f}s{Colors.ENDC}", "TIMING")
        sound = pygame.mixer.Sound(tmp_path)
        os.remove(tmp_path)
        channel = sound.play()
        while channel.get_busy(): pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"TTS synthesis failed: {e}", "ERROR")


def call_chatgpt(question):
    global chat_start, chat_end, conversation_memory, tts_start
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


def main():
    global bypass_active, bypass_end_time
    log("Initializing voice assistant...", "SYSTEM")
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    whisper_model = whisper.load_model("tiny")
    log("Startup complete. Say 'okay' followed by your question.", "SYSTEM")

    while True:
        data = stream.read(CHUNK)
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio**2))

        if bypass_active and time.time() > bypass_end_time:
            bypass_active = False
            log("Bypass expired", "BYPASS")
            play_bypass_cancel_sound()

        if rms >= SILENCE_THRESHOLD:
            log("Voice detected, capturing...", "AUDIO")
            frames = [data] + record_audio(stream)
            save_wav("temp.wav", frames, pa)

            text = transcribe_audio("temp.wav", whisper_model)
            os.remove("temp.wav")
            if not text:
                continue

            words = text.split()
            trigger = words and words[0].lower().strip(",") in ("okay", "ok")

            if bypass_active or trigger:
                query = text if bypass_active else " ".join(words[1:]).strip()
                level = "BYPASS" if bypass_active else "SUCCESS"
                log(f"Query: {Colors.BOLD}{query}{Colors.ENDC}", level)

                if not query:
                    continue

                if bypass_active:
                    play_prompt_sound()
                else:
                    play_bypass_start_sound()

                answer = call_chatgpt(query)
                speak_text(answer)

                # Total latency from end of speech capture to TTS start
                total_latency = tts_start - prompt_end_time
                log(f"Total latency from speech end to TTS start: {Colors.BOLD}{total_latency:.3f}s{Colors.ENDC}", "TIMING")

                bypass_active = True
                bypass_end_time = time.time() + BYPASS_DELAY
                log(f"Bypass active for {BYPASS_DELAY} seconds", "BYPASS")
            else:
                log(f"No trigger word detected ('{words[0] if words else ''}'), ignoring.", "WARNING")

if __name__ == "__main__":
    main()