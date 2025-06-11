# triggers.py
# Handles wake word detection, async audio frame management, inactivity timer, and pipeline to transcribe/API

import asyncio
import pvporcupine
import pyaudio
import numpy as np
import time
import os
import traceback
from dotenv import load_dotenv
from utils import log
from sounds import play_open_sound, play_close_sound, play_pop_sound
import collections

load_dotenv()

PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")
WAKE_WORD = "computer"
SILENCE_THRESHOLD = 500  # Adjust as needed
SILENCE_CHUNKS = int(16000 / 1024 * 2)  # ~2 seconds of silence, matching oldTriggerRecording
INACTIVITY_TIMEOUT = 15  # seconds
FRAME_DURATION_MS = 30
SAMPLE_RATE = 16000
CHANNELS = 1

porcupine = None
pa = None
stream = None
frames = []
speech_detected = False
last_speech_time = None
recording = False
should_exit = False
on_transcription_callback = None
IS_ASSISTANT_AWAKE = False

import asyncio


# --- SETUP & TEARDOWN ---
def setup_triggers(on_transcription):
    global pa, stream, on_transcription_callback
    try:
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=SAMPLE_RATE,
            channels=CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=512,
        )
        on_transcription_callback = on_transcription
        log("Triggers setup complete", "SYSTEM", script="TRIGGERS")
    except Exception as e:
        log(f"Error in setup_triggers: {e}\n{traceback.format_exc()}", "ERROR", script="TRIGGERS")


def stop_triggers():
    global stream, pa, porcupine
    try:
        if stream:
            stream.close()
        if pa:
            pa.terminate()
        if porcupine:
            porcupine.delete()
        log("Triggers stopped and resources released", "SYSTEM", script="TRIGGERS")
    except Exception as e:
        log(f"Error in stop_triggers: {e}\n{traceback.format_exc()}", "ERROR", script="TRIGGERS")


# --- MAIN RUN LOOP ---
def run_triggers():
    try:
        asyncio.run(_main_trigger_loop())
    except KeyboardInterrupt:
        log("Keyboard interrupt in triggers", "SYSTEM", script="TRIGGERS")
    except Exception as e:
        log(f"Error in run_triggers: {e}\n{traceback.format_exc()}", "ERROR", script="TRIGGERS")


def rms(data):
    arr = np.frombuffer(data, dtype=np.int16)
    if arr.size == 0:
        return 0.0
    mean_square = np.mean(arr.astype(np.float64) ** 2)
    if mean_square < 0 or np.isnan(mean_square):
        return 0.0
    return np.sqrt(mean_square)


async def _main_trigger_loop():
    global should_exit, IS_ASSISTANT_AWAKE
    while not should_exit:
        try:
            if not IS_ASSISTANT_AWAKE:
                mode = await _sleep_mode()
                if mode == "awake":
                    IS_ASSISTANT_AWAKE = True
            if IS_ASSISTANT_AWAKE:
                await _awake_loop()
        except Exception as e:
            log(f"Main trigger loop encountered an error: {e}\n{traceback.format_exc()}", "ERROR")
            await asyncio.sleep(1)


async def _sleep_mode():
    global porcupine
    try:
        porcupine = pvporcupine.create(
            access_key=PORCUPINE_ACCESS_KEY,
            keywords=[WAKE_WORD],
        )
        log("Listening for wake word. Assistant is in sleep mode.", "TRIGGERS")
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            keyword_index = porcupine.process(np.frombuffer(pcm, dtype=np.int16))
            if keyword_index >= 0:
                from sounds import play_open_sound
                play_open_sound()
                log(f"Wake word '{WAKE_WORD}' detected. Switching to awake mode.", "TRIGGERS")
                porcupine.delete()
                return "awake"
    except Exception as e:
        log(f"Sleep mode error: {e}\n{traceback.format_exc()}", "ERROR")
        return "sleep"


async def _awake_loop():
    global frames, speech_detected, last_speech_time, IS_ASSISTANT_AWAKE
    from sounds import IS_ASSISTANT_SPEAKING
    buffer_size = int(SAMPLE_RATE / 1024 * 2)
    buffer_frames = collections.deque(maxlen=buffer_size)
    frames = []
    speech_detected = False
    last_speech_time = time.time()
    fp16_warning_muted = False
    silence_chunks = 0
    chunk_size = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
    while IS_ASSISTANT_AWAKE:
        try:
            pcm = stream.read(chunk_size, exception_on_overflow=False)
            volume = rms(pcm)
            now = time.time()
            if not fp16_warning_muted:
                import warnings
                warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")
                fp16_warning_muted = True
            if volume > SILENCE_THRESHOLD:
                if not speech_detected:
                    if IS_ASSISTANT_SPEAKING:
                        from sounds import interrupt_sounds
                        interrupt_sounds()
                        log("Ongoing AI speech interrupted by user input.", "TRIGGERS")
                    frames = list(buffer_frames)
                    log("User speech detected. Listening for command.", "TRIGGERS")
                frames.append(pcm)
                speech_detected = True
                last_speech_time = now
                silence_chunks = 0
            else:
                if speech_detected:
                    frames.append(pcm)
                    silence_chunks += 1
                else:
                    buffer_frames.append(pcm)
            if speech_detected and silence_chunks > SILENCE_CHUNKS:
                log("End of user speech detected. Preparing for transcription.", "TRIGGERS")
                frames_to_process = frames.copy()
                frames = []
                buffer_frames.clear()
                silence_chunks = 0
                speech_detected = False
                last_speech_time = time.time()
                asyncio.create_task(_handle_speech_end(frames_to_process))
            if (time.time() - last_speech_time) > INACTIVITY_TIMEOUT:
                from sounds import play_close_sound
                play_close_sound()
                log("No activity detected. Returning to sleep mode.", "TRIGGERS")
                IS_ASSISTANT_AWAKE = False
                break
            await asyncio.sleep(0.01)
        except Exception as e:
            log(f"Awake loop error: {e}\n{traceback.format_exc()}", "ERROR")
            await asyncio.sleep(1)


async def _handle_speech_end(frames):
    if not frames:
        return
    try:
        audio_path = _save_frames_to_wav(frames)
        from transcribe import async_transcribe
        text = await async_transcribe(audio_path)
        log(f"Transcription complete. Result: '{text}'", "WHISPER")
        if not text or not text.strip() or len(text.strip()) < 2 or text.strip().lower() in ["uh", "um", "", "..."]:
            return
        if on_transcription_callback:
            on_transcription_callback(text)
        from sounds import play_pop_sound
        play_pop_sound()
        asyncio.create_task(prompt_manager(text))
    except Exception as e:
        log(f"Error during speech end handling: {e}\n{traceback.format_exc()}", "ERROR")


async def prompt_manager(user_text):
    try:
        from API import send_openai_request
        import json, os
        with open(os.path.join(os.path.dirname(__file__), '../assets/baseprompt.json'), 'r', encoding='utf-8') as f:
            baseprompt = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), '../assets/settings.json'), 'r', encoding='utf-8') as f:
            settings = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), '../assets/commands.json'), 'r', encoding='utf-8') as f:
            commands = json.load(f).get('commands', [])
        baseprompt['settings'] = settings
        baseprompt['commands'] = commands
        baseprompt['user_prompt'] = user_text
        prompt = json.dumps(baseprompt, ensure_ascii=False)
        payload = {
            "model": "gpt-4-1106-preview",
            "messages": [{"role": "user", "content": prompt}]
        }
        log(f"Sending user prompt to ChatGPT. Awaiting response...", "GPT")
        response = send_openai_request('chat/completions', payload)
        content = None
        try:
            if response and 'choices' in response and response['choices']:
                content = response['choices'][0]['message']['content']
        except Exception as e:
            log(f"Malformed API response: {response}\n{e}", "ERROR")
        if content:
            from commands import execute_commands_from_response_block_sync
            for line in content.split('\n'):
                if line.strip().startswith('/'):
                    log(f"Executing command: {line.strip()}", "COMMAND")
            await execute_commands_from_response_block_sync(content)
            log("All commands executed. AI response complete.", "COMMAND")
    except Exception as e:
        log(f"Error in prompt_manager: {e}\n{traceback.format_exc()}", "ERROR")


def _save_frames_to_wav(frames):
    import wave
    import tempfile
    try:
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        wf = wave.open(temp_wav.name, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        return temp_wav.name
    except Exception as e:
        log(f"Error saving frames to wav: {e}\n{traceback.format_exc()}", "ERROR", script="TRIGGERS")
        return None


async def _inactivity_timer():
    await asyncio.sleep(INACTIVITY_TIMEOUT)


def force_sleep_mode():
    global IS_ASSISTANT_AWAKE
    IS_ASSISTANT_AWAKE = False
