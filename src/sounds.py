import os
import time
import pygame
import numpy as np
import re
import requests
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

from utils import log, Colors
from transcribe import get_prompt_end_time, SILENCE_THRESHOLD

# Initialize pygame for audio playback - use a smaller buffer for faster response
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# TTS Parameters
TTS_VOICE = "nova"
TTS_MODEL = "tts-1"
TTS_SPEED = 1.0  # 1.0 is normal speed

# Timing metrics
tts_start = 0
tts_end = 0

def play_sound(filename, blocking=False):
    """Play a sound file from the assets directory"""
    try:
        filepath = os.path.join("assets", filename)
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        
        if blocking:
            # Wait for the sound to finish if blocking is requested
            while pygame.mixer.music.get_busy(): 
                pygame.time.Clock().tick(10)
    except Exception as e:
        log(f"Error playing sound {filename}: {e}", "ERROR")

def play_prompt_sound():
    """Play sound to indicate the system is processing - non-blocking"""
    play_sound("prompting.wav", blocking=False)

def play_bypass_start_sound():
    """Play sound to indicate bypass mode started - non-blocking"""
    play_sound("bypass_start.wav", blocking=False)

def play_bypass_cancel_sound():
    """Play sound to indicate bypass mode ended - non-blocking"""
    play_sound("bypass_cancel.wav", blocking=False)

def download_tts(sentence):
    """Download text-to-speech audio and return the path to the temp file"""
    try:
        payload = {
            "model": TTS_MODEL,
            "voice": TTS_VOICE,
            "input": sentence,
            "speed": TTS_SPEED,
            "format": "opus"
        }
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
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
    except Exception as e:
        log(f"TTS download error: {e}", "ERROR")
        return None

def play_audio(path, audio_stream):
    """Play audio file while listening for interruptions, then delete it"""
    try:
        sound = pygame.mixer.Sound(path)
        ch = sound.play()
        
        while ch.get_busy():
            # Check for potential interruption while playing
            pcm = audio_stream.read(1024, exception_on_overflow=False)
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
    except Exception as e:
        log(f"Audio playback error: {e}", "ERROR")
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
        return False

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
    
    # Import here to avoid circular imports
    from chat import extract_commands, execute_command
    
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
    prompt_end_time = get_prompt_end_time()
    
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
            if path is None:
                continue
                
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