import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import pygame
import threading
import time
from collections import deque
from utils import log

pygame.mixer.init()

IS_ASSISTANT_SPEAKING = False  # Global flag for speech playback
NON_SPEECH_LOCK = threading.Lock()
FADEOUT_MS = 500

# --- Speech Queue System ---
speech_queue = deque()
current_speech_key = None
speech_lock = threading.Lock()
speech_worker_thread = None

# --- Main Play Function ---
def play(sound_path, is_speech=False, speech_key=None):
    global IS_ASSISTANT_SPEAKING, current_speech_key, speech_worker_thread
    if is_speech:
        with speech_lock:
            # If a new key is detected, clear queue and set new key
            if current_speech_key is None or (speech_key is not None and speech_key > current_speech_key):
                speech_queue.clear()
                current_speech_key = speech_key if speech_key is not None else time.time()
            # Only queue if the key matches the current key (ignore old/invalid keys)
            if speech_key == current_speech_key:
                speech_queue.append(sound_path)
                if not speech_worker_thread or not speech_worker_thread.is_alive():
                    speech_worker_thread = threading.Thread(target=_speech_worker, daemon=True)
                    speech_worker_thread.start()
            else:
                # Ignore speech with a lower or unrelated key
                log(f"[SOUNDS] play() ignored: speech_key {speech_key} != current_speech_key {current_speech_key}", level="DEBUG", script="SOUNDS")
    else:
        threading.Thread(target=_play_now, args=(sound_path,), daemon=True).start()

# --- Speech Worker ---
def _speech_worker():
    global IS_ASSISTANT_SPEAKING, current_speech_key
    while True:
        with speech_lock:
            if not speech_queue:
                IS_ASSISTANT_SPEAKING = False
                current_speech_key = None
                break
            sound_path = speech_queue.popleft()
        IS_ASSISTANT_SPEAKING = True
        try:
            sound = pygame.mixer.Sound(sound_path)
            channel = sound.play()
            while channel.get_busy():
                time.sleep(0.01)
            # Add a small natural pause between sentences
            time.sleep(0.18)
        except Exception:
            pass
        finally:
            IS_ASSISTANT_SPEAKING = False

# --- Immediate Play (for non-speech) ---
def _play_now(sound_path):
    with NON_SPEECH_LOCK:
        try:
            sound = pygame.mixer.Sound(sound_path)
            channel = sound.play()
        except Exception:
            pass

def is_speaking():
    global IS_ASSISTANT_SPEAKING
    return IS_ASSISTANT_SPEAKING

# --- Backwards compatibility for other scripts ---
ASSETS_PATH = os.path.join(os.path.dirname(__file__), '../assets')
OPEN_SOUND = os.path.join(ASSETS_PATH, 'open.wav')
CLOSE_SOUND = os.path.join(ASSETS_PATH, 'close.wav')
POP_SOUND = os.path.join(ASSETS_PATH, 'pop.wav')

def play_open_sound():
    play(OPEN_SOUND, is_speech=False)

def play_close_sound():
    play(CLOSE_SOUND, is_speech=False)

def play_pop_sound():
    play(POP_SOUND, is_speech=False)

def interrupt():
    global IS_ASSISTANT_SPEAKING, current_speech_key, speech_worker_thread
    try:
        with speech_lock:
            # Increment speech key as a number so no other speech of the same key can be played
            if current_speech_key is not None:
                current_speech_key += 1
            # Wipe the queue
            speech_queue.clear()
        # Fade out all currently playing speech (do not call stop immediately after fadeout)
        for i in range(pygame.mixer.get_num_channels()):
            channel = pygame.mixer.Channel(i)
            if channel.get_busy():
                channel.fadeout(FADEOUT_MS)
        IS_ASSISTANT_SPEAKING = False
        log(f"interrupt() called, queue cleared, all speech faded out.", level="DEBUG", script="SOUNDS")
    except Exception as e:
        log(f"interrupt() error: {e}", level="ERROR", script="SOUNDS")
