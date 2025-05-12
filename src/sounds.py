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
from transcribe import get_prompt_end_time, SILENCE_THRESHOLD, set_ai_speaking_state

# Initialize pygame for audio playback - use a smaller buffer for faster response
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Suppress pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# TTS Parameters
TTS_VOICE = "nova"
TTS_MODEL = "tts-1"
TTS_SPEED = 1.0  # 1.0 is normal speed

# Fade out duration in milliseconds
FADE_OUT_DURATION = 500  # 0.5 seconds

# Timing metrics
tts_start = 0
tts_end = 0

# Global state for speech control
current_speech_channel = None
speech_interrupted = threading.Event()

def reset_speech_state():
    """Reset all speech-related state variables"""
    global current_speech_channel, speech_interrupted
    speech_interrupted.set()  # Ensure any pending speech is stopped
    
    if current_speech_channel and current_speech_channel.get_busy():
        current_speech_channel.fadeout(FADE_OUT_DURATION)  # Fade out instead of stopping
        # Wait a moment for fade to begin but don't block completely
        time.sleep(0.1) 
    
    current_speech_channel = None
    speech_interrupted.clear()  # Reset for future use
    
    # Make sure AI is marked as not speaking
    set_ai_speaking_state(False)
    
    log("Speech state has been reset", "INFO")

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

def play_pop_sound():
    """Play sound to indicate the system is processing - non-blocking"""
    play_sound("pop.wav", blocking=False)

def play_open_sound():
    """Play sound to indicate the system is processing - non-blocking"""
    play_sound("open.wav", blocking=False)

def play_close_sound():
    """Play sound to indicate the system is processing - non-blocking"""
    play_sound("close.wav", blocking=False)

def stop_current_speech():
    """Fade out the currently playing speech instead of stopping abruptly"""
    global current_speech_channel, speech_interrupted
    
    # Signal that speech has been interrupted
    speech_interrupted.set()
    
    # Fade out the current speech channel, if it exists
    if current_speech_channel and current_speech_channel.get_busy():
        log(f"Fading out speech over {FADE_OUT_DURATION}ms", "INFO")
        current_speech_channel.fadeout(FADE_OUT_DURATION)  # Fade out over specified duration
        
        # Short wait to let fade begin but don't block completely
        time.sleep(0.1)
    else:
        log("No active speech to fade out", "INFO")
    
    # Set AI speaking state to false when speech is stopped
    set_ai_speaking_state(False)

def download_tts(sentence):
    """Download text-to-speech audio and return the path to the temp file"""
    try:
        # Make sure the sentence isn't empty
        if not sentence.strip():
            log("Empty sentence provided to TTS, skipping", "WARNING")
            return None
            
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
    global current_speech_channel, speech_interrupted
    
    try:
        sound = pygame.mixer.Sound(path)
        ch = sound.play()
        current_speech_channel = ch
        
        # Reset the interrupted flag
        speech_interrupted.clear()
        
        # Set the AI speaking state to true before playing
        set_ai_speaking_state(True)
        
        interrupted = False
        while ch.get_busy() and not speech_interrupted.is_set():
            # Check for potential interruption while playing - handled by continuous recording
            pygame.time.Clock().tick(10)
        
        # Check if we were interrupted
        interrupted = speech_interrupted.is_set()
        
        # If interrupted, make sure we wait for fadeout to complete
        if interrupted:
            # Give a small delay to let any fade-out complete naturally
            time.sleep(FADE_OUT_DURATION / 1000 * 0.8)  # 80% of fade duration
        
        # Clean up
        os.remove(path)
        return interrupted
    except Exception as e:
        log(f"Audio playback error: {e}", "ERROR")
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
        return False
    finally:
        # Make sure AI speaking state is set to false when done
        set_ai_speaking_state(False)

def split_into_sentences(text):
    """Split text into sentences for parallel TTS processing"""
    # Skip if text is empty
    if not text or not text.strip():
        return []
        
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
    global tts_start, tts_end, speech_interrupted
    from transcribe import is_ai_speaking
    if is_ai_speaking:
        stop_current_speech()
    # Don't attempt to speak empty text
    if not text or not text.strip():
        log("Skipping TTS for empty text", "INFO")
        return False
    
    tts_start = time.time()
    
    # Split into sentences
    sentences = split_into_sentences(text)
    log(f"Split response into {len(sentences)} sentences", "INFO")
    
    # If no valid sentences, skip
    if not sentences:
        return False

    # Reset interrupted flag before starting new speech
    speech_interrupted.clear()

    # Parallel download + sequential playback with interruption checking
    interrupted = False
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(download_tts, s) for s in sentences]

        for i, fut in enumerate(futures):
            if interrupted or speech_interrupted.is_set():
                break
                
            path = fut.result()
            if path is None:
                continue
                
            if i == 0:
                log(f"Total latency from speech end to TTS start {(tts_start - get_prompt_end_time()):.3f}s", "TIMING")
                
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
    return False  # No interruption occurred