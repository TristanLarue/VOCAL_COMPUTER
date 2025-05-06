import os
import platform
import ctypes.util
import struct
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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pvporcupine
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

# Audio settings\N{#}
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 500
SILENCE_CHUNKS = int(RATE / CHUNK * 2)

# Initialize pygame for audio playback\pygame.mixer.init()

# Load wake-word detector (Porcupine) for "computer"
porcupine = pvporcupine.create(
    access_key=os.getenv("PORCUPINE_ACCESS_KEY"),
    keywords=["computer"],
    sensitivities=[0.6]
)
pa = pyaudio.PyAudio()
porcupine_stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length
)

# Load Whisper for transcription
whisper_model = whisper.load_model("tiny")

# Logging utility
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

# Play a random Nova start sound
def play_nova_start_sound():
    try:
        folder = r"C:\Users\trist\OneDrive\Desktop\AI_VOCAL\nova_start_sounds"
        files = [f for f in os.listdir(folder) if f.lower().endswith(".wav")]
        choice = random.choice(files)
        pygame.mixer.music.load(os.path.join(folder, choice))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing Nova start sound: {e}", "ERROR")

# Record until silence
def record_audio(stream):
    frames = []
    silence_count = 0
    log("Recording...", "AUDIO")
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
    log("Finished recording", "AUDIO")
    return frames

# Save frames to WAV
def save_wav(filename, frames, pa):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pa.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    log(f"Wrote {filename}", "AUDIO")

# Transcribe with Whisper
def transcribe_audio(filename):
    log("Transcribing...", "WHISPER")
    result = whisper_model.transcribe(filename)
    text = result.get("text", "").strip()
    log(f"Transcription: {text}", "WHISPER")
    return text

# Query ChatGPT
def call_chatgpt(question):
    log(f"Query to GPT: {question}", "GPT")
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are Nova, a friendly assistant."},
            {"role": "user", "content": question}
        ]
    )
    answer = response.choices[0].message.content.strip()
    return answer

# TTS and playback (unchanged from existing)
def speak_text(text):
    # Simplified: print for now
    print("Nova:", text)

# Main loop: wait for "computer", record, transcribe, chat, speak

def main():
    record_stream = pa.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    log("Assistant ready. Say 'computer' to start.", "SYSTEM")

    while True:
        # Listen for wake word
        pcm_data = porcupine_stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm_data)
        if porcupine.process(pcm) < 0:
            continue

        log("Wake word 'computer' detected", "SUCCESS")
        play_nova_start_sound()

        # Record user speech
        frames = record_audio(record_stream)
        save_wav("user.wav", frames, pa)

        # Transcribe and handle
        text = transcribe_audio("user.wav")
        os.remove("user.wav")
        if not text:
            continue

        answer = call_chatgpt(text)
        speak_text(answer)

if __name__ == "__main__":
    main()
