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
from utils import log, get_settings, log_finetune_example, log_cost_summary, log_command_execution
from sounds import play_sound_effect, IS_ASSISTANT_SPEAKING, interrupt_speech
import collections

load_dotenv()

# Global cost tracking
TOTAL_COST_CENTS = 0.0
TOTAL_TOKEN_COST_CENTS = 0.0
TOTAL_TTS_COST_CENTS = 0.0

PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY")
WAKE_WORD = "computer"
SILENCE_THRESHOLD = 250  # Lowered threshold for more sensitive speech detection
SILENCE_CHUNKS = int(16000 / 1024 * 3.5)  # ~3.5 seconds of silence, increased from 2 seconds
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
    global pa, stream, on_transcription_callback, IS_ASSISTANT_AWAKE
    import warnings
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")
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
        IS_ASSISTANT_AWAKE = True  # Start in awake mode
        log("Triggers setup complete", "SYSTEM")
        greet()
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
            try:
                porcupine.delete()
            except Exception as e:
                log(f"Error deleting porcupine: {e}", "ERROR", script="TRIGGERS")
            porcupine = None
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
        log("Listening for wake word 'COMPUTER'. Assistant is in sleep mode.", "TRIGGER")
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            keyword_index = porcupine.process(np.frombuffer(pcm, dtype=np.int16))
            if keyword_index >= 0:
                play_sound_effect(os.path.join(os.path.dirname(__file__), '../assets/open.wav'))
                log(f"Wake word '{WAKE_WORD}' detected. Switching to awake mode.", "TRIGGER")
                porcupine.delete()
                return "awake"
    except Exception as e:
        log(f"Sleep mode error: {e}\n{traceback.format_exc()}", "ERROR")
        return "sleep"


async def _awake_loop():
    global frames, speech_detected, last_speech_time, IS_ASSISTANT_AWAKE
    import collections
    import time
    from utils import get_settings
    buffer_size = int(SAMPLE_RATE / 1024 * 2)
    buffer_frames = collections.deque(maxlen=buffer_size)
    rms_history = collections.deque(maxlen=int(1000 / FRAME_DURATION_MS))  # Store last ~1s of RMS values
    frames = []
    speech_detected = False
    last_speech_time = time.time()
    silence_chunks = 0
    chunk_size = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
    auto_convo_end = get_settings().get('auto-conversation-end')
    while IS_ASSISTANT_AWAKE:
        try:
            pcm = stream.read(chunk_size, exception_on_overflow=False)
            volume = rms(pcm)
            rms_history.append(volume)
            avg_rms = sum(rms_history) / len(rms_history) if rms_history else 0
            now = time.time()
            # Use average RMS over last second for interruption
            if avg_rms > SILENCE_THRESHOLD:
                if IS_ASSISTANT_SPEAKING:
                    interrupt_speech(fade_out=True)
                    log(f"Ongoing AI speech interrupted by user input (avg RMS {avg_rms:.2f} > threshold {SILENCE_THRESHOLD})", "TRIGGERS")
                if not speech_detected:
                    frames = list(buffer_frames)
                    log("User speech detected. Listening for command.", "TRIGGER")
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
                log("End of user speech detected. Preparing for transcription.", "TRIGGER")
                frames_to_process = frames.copy()
                frames = []
                buffer_frames.clear()
                silence_chunks = 0
                speech_detected = False
                last_speech_time = time.time()
                asyncio.create_task(_handle_speech_end(frames_to_process))
            # Check for inactivity timeout, but only if auto-conversation-end is enabled
            auto_convo_end = get_settings().get('auto-conversation-end', False)
            if auto_convo_end:
                silence_delay = get_settings().get('silence-delay', 15)  # Default to 15 seconds
                if (time.time() - last_speech_time) > silence_delay:
                    play_sound_effect(os.path.join(os.path.dirname(__file__), '../assets/close.wav'))
                    log(f"No activity detected for {silence_delay} seconds. Returning to sleep mode.", "TRIGGERS")
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
        log(f"Transcription complete. Result: '{text}'", "TRANSCRIPTION")
        if not text or not text.strip() or len(text.strip()) < 2 or text.strip().lower() in ["uh", "um", "", "..."]:
            return
        if on_transcription_callback:
            on_transcription_callback(text)
        play_sound_effect(os.path.join(os.path.dirname(__file__), '../assets/pop.wav'))
        # Only await prompt_manager, do not create multiple tasks
        await prompt_manager(text)
    except Exception as e:
        log(f"Error during speech end handling: {e}\n{traceback.format_exc()}", "ERROR")


async def prompt_manager(user_text):
    try:
        import requests
        import json, os
        from dotenv import load_dotenv
        load_dotenv()
        
        def send_openai_request(endpoint, payload, headers=None, stream=False):
            """Send request to OpenAI API"""
            try:
                url = f"https://api.openai.com/v1/{endpoint}"
                if headers is None:
                    headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"}
                response = requests.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload, stream=stream)
                response.raise_for_status()
                if stream:
                    return response
                return response.json()
            except Exception as e:
                log(f"OpenAI API request failed: {e}", "ERROR", script="triggers.py")
                return None

        def chatgpt_text_to_text(*, prompt=None, **kwargs):
            """Send text to ChatGPT and get response"""
            if prompt is not None:
                payload = {
                    "model": kwargs.get("model", "gpt-4.1"),
                    "messages": [{"role": "user", "content": prompt}]
                }
                payload.update({k: v for k, v in kwargs.items() if k not in ("model",)})
            else:
                payload = kwargs
            return send_openai_request('chat/completions', payload)
        
        # Load baseprompt, settings, commands, and memory
        with open(os.path.join(os.path.dirname(__file__), '../assets/baseprompt.json'), 'r', encoding='utf-8') as f:
            baseprompt = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), '../assets/settings.json'), 'r', encoding='utf-8') as f:
            settings = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), '../assets/commands.json'), 'r', encoding='utf-8') as f:
            commands = json.load(f).get('commands', [])
        with open(os.path.join(os.path.dirname(__file__), '../assets/memory.json'), 'r', encoding='utf-8') as f:
            memory = json.load(f)
        baseprompt['settings'] = settings
        baseprompt['commands'] = commands
        baseprompt['memory'] = memory  # Load full memory.json as the memory key
        baseprompt['user_prompt'] = user_text
        import time
        baseprompt['unix_time'] = int(time.time())
        # Add temp_folder file list
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../temp'))
        try:
            temp_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        except Exception:
            temp_files = []
        baseprompt['temp_folder'] = temp_files
        # Remove any context logic here; context is only for reprompt
        prompt = json.dumps(baseprompt, ensure_ascii=False)
        
        # Calculate token costs before sending request
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model("gpt-4")
            input_tokens = len(encoding.encode(prompt))
            
            # Cost calculation (as of 2024/2025 pricing) - converted to cents
            input_cost_per_million = 200.0  # 200¢ per million input tokens ($2.00)
            output_cost_per_million = 800.0  # 800¢ per million output tokens ($8.00)
            
            input_cost_cents = (input_tokens / 1_000_000) * input_cost_per_million
            
            log(f"API request: {input_tokens:,} input tokens ({input_cost_cents:.4f}¢)", "COST")
            
        except Exception as e:
            log(f"Token estimation failed: {e}", "ERROR", script="triggers.py")
            input_tokens = 0
            input_cost_cents = 0.0
        
        payload = {
            "model": "gpt-4.1",
            "messages": [{"role": "user", "content": prompt}]
        }
        log("Sending request to OpenAI API", "API")
        response = chatgpt_text_to_text(prompt=prompt)
        content = None
        try:
            if response and 'choices' in response and response['choices']:
                content = response['choices'][0]['message']['content']
                
                # Calculate output token cost and update global tracking
                global TOTAL_COST_CENTS, TOTAL_TOKEN_COST_CENTS
                try:
                    output_tokens = len(encoding.encode(content))
                    output_cost_cents = (output_tokens / 1_000_000) * output_cost_per_million
                    total_request_cost = input_cost_cents + output_cost_cents
                    
                    log(f"API response: {output_tokens:,} output tokens ({output_cost_cents:.4f}¢)", "COST")
                    
                    # Update global trackers
                    TOTAL_TOKEN_COST_CENTS += total_request_cost
                    TOTAL_COST_CENTS = TOTAL_TOKEN_COST_CENTS + TOTAL_TTS_COST_CENTS
                    
                    # Log cost summary
                    log_cost_summary(TOTAL_COST_CENTS, TOTAL_TOKEN_COST_CENTS, TOTAL_TTS_COST_CENTS)
                    
                except Exception as e:
                    log(f"Output token calculation failed: {e}", "ERROR", script="triggers.py")
                    
        except Exception as e:
            log(f"Malformed API response: {response}", "ERROR", script="triggers.py")
        if content:
            # Log user/assistant pair for fine-tuning
            log_finetune_example(user_text, content)
            # Summarize memory immediately (async, non-blocking)
            try:
                import asyncio
                from memory import summarize_memory
                async def summarize_and_save():
                    import json, os
                    mem_path = os.path.join(os.path.dirname(__file__), '../assets/memory.json')
                    with open(mem_path, 'r', encoding='utf-8') as f:
                        old_mem = json.load(f)
                    summary_obj = await asyncio.to_thread(summarize_memory, old_mem, user_text, content)
                    if summary_obj:
                        with open(mem_path, 'w', encoding='utf-8') as f:
                            json.dump(summary_obj, f, indent=2, ensure_ascii=False)
                asyncio.create_task(summarize_and_save())
                log("Memory summarization started", "CONTEXT")
            except Exception as e:
                log(f"Error starting memory summarization: {e}", "ERROR", script="triggers.py")
            # Use new JSON command processing
            from commands import execute_commands_from_json_response_async
            await execute_commands_from_json_response_async(content)
    except Exception as e:
        log(f"Error in prompt_manager: {e}", "ERROR", script="triggers.py")


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
        log(f"Error saving frames to wav: {e}", "ERROR", script="triggers.py")
        return None


async def _inactivity_timer():
    """Timer function that waits for the configured silence delay"""
    silence_delay = get_settings().get('silence-delay', 15)  # Default to 15 seconds
    await asyncio.sleep(silence_delay)


def force_sleep_mode():
    global IS_ASSISTANT_AWAKE
    IS_ASSISTANT_AWAKE = False


def greet():
    from modules.speak import run as speak_run
    import datetime
    now = datetime.datetime.now()
    hour = now.hour
    if hour < 12:
        time_of_day = "morning"
    elif hour < 18:
        time_of_day = "afternoon"
    else:
        time_of_day = "evening"
    
    greeting = f"Good {time_of_day}, Tristan. All systems are operational."
    speak_run(text=greeting)
