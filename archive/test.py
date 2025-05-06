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
from datetime import datetime
from api_keys import openai_key
import webrtcvad
import sounddevice as sd

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
FRAME_DURATION = 160  # ms
FRAME_SIZE = int(RATE * FRAME_DURATION / 1000)  # samples per frame
BYTES_PER_SAMPLE = 2
VAD_AGGRESSIVENESS = 2
BYPASS_DELAY = 10

# System prompts
base_prompt = '''
You are Nova, a voice assistant speaking with Tristan. Your responses will be spoken aloud through text-to-speech, so clarity and brevity are essential.
Important guidelines:
- Keep initial responses concise (1-3 short sentences) with simple, everyday vocabulary
- After providing a brief answer, ask if Tristan wants more details when appropriate
- Use a warm, friendly tone as if speaking to a friend
- Avoid formatting like bullet points or lists that don't work well in spoken form
- Provide direct, practical answers to questions
- Ask for clarification if Tristan's request is unclear
- Focus exclusively on responding to the question provided after these instructions
- Remember Tristan will hear your response through speakers, not read it
- Understand that Tristan is currently speaking and that his speech is being transcribed to you
- Do not propose anything else to Tristan after answering his question

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

vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)


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


def record_and_transcribe_stream(model):
    global prompt_end_time, transcription_start, transcription_end
    buffer = bytearray()
    in_speech = False
    log("Listening (streaming)...", "AUDIO")
    while True:
        frame = sd.rec(int(FRAME_SIZE), samplerate=RATE, channels=CHANNELS, dtype='int16')
        sd.wait()
        data = frame.tobytes()
        is_speech = vad.is_speech(data, RATE)
        if is_speech:
            buffer.extend(data)
            in_speech = True
        elif in_speech:
            # end of speech
            break
    prompt_end_time = time.time()
    log("Speech ended, running transcription...", "AUDIO")
    transcription_start = time.time()
    result = model.transcribe(np.frombuffer(buffer, np.int16), fp16=False)
    transcription_end = time.time()
    text = result.get("text", "").strip()
    log(f"Transcription duration: {Colors.BOLD}{(transcription_end-transcription_start):.3f}s{Colors.ENDC}", "TIMING")
    log(f"Transcription result: {Colors.BOLD}{text}{Colors.ENDC}", "WHISPER")
    return text


def speak_text(text):
    global tts_start, tts_end
    log(f"Speaking: {Colors.BOLD}{text}{Colors.ENDC}", "INFO")
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
        # stream playback
        player = pyaudio.PyAudio()
        stream_out = player.open(format=player.get_format_from_width(2), channels=CHANNELS, rate=RATE, output=True)
        for chunk in resp.iter_content(chunk_size=4096):
            if chunk:
                stream_out.write(chunk)
        stream_out.stop_stream()
        stream_out.close()
        player.terminate()
        tts_end = time.time()
        log(f"TTS duration: {Colors.BOLD}{(tts_end-tts_start):.3f}s{Colors.ENDC}", "TIMING")
    except Exception as e:
        log(f"TTS synthesis failed: {e}", "ERROR")

# ... rest of the code remains unchanged ...

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
    threading.Thread(target=update_memory_threaded, args=(question, answer), daemon=True).start()
    return answer

# ... main loop now calls record_and_transcribe_stream instead of record_audio ...

def main():
    global bypass_active, bypass_end_time
    log("Initializing voice assistant...", "SYSTEM")
    whisper_model = whisper.load_model("tiny.en")
    log("Startup complete. Say 'okay' followed by your question.", "SYSTEM")

    while True:
        text = record_and_transcribe_stream(whisper_model)
        if not text:
            continue
        words = text.split()
        trigger = words and words[0].lower().strip(",") in ("okay", "ok")

        if bypass_active or trigger:
            query = text if bypass_active else " ".join(words[1:]).strip()
            log(f"Query: {Colors.BOLD}{query}{Colors.ENDC}", "BYPASS" if bypass_active else "SUCCESS")
            if not query:
                continue
            if bypass_active:
                play_prompt_sound()
            else:
                play_bypass_start_sound()
            answer = call_chatgpt(query)
            speak_text(answer)
            total_latency = tts_start - prompt_end_time
            log(f"Total latency from speech end to TTS start: {Colors.BOLD}{total_latency:.3f}s{Colors.ENDC}", "TIMING")
            bypass_active = True
            bypass_end_time = time.time() + BYPASS_DELAY
        else:
            log(f"No trigger word detected ('{words[0] if words else ''}'), ignoring.", "WARNING")

if __name__ == "__main__":
    main()
