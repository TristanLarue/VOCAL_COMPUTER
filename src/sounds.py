import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import pygame
import threading
import time
from collections import deque

pygame.mixer.init()

SOUND_QUEUE = deque()
QUEUE_LOCK = threading.Lock()
CURRENT_CHANNEL = None
FADEOUT_MS = 500

ASSETS_PATH = os.path.join(os.path.dirname(__file__), '../assets')

OPEN_SOUND = os.path.join(ASSETS_PATH, 'open.wav')
CLOSE_SOUND = os.path.join(ASSETS_PATH, 'close.wav')
POP_SOUND = os.path.join(ASSETS_PATH, 'pop.wav')

STOP_EVENT = threading.Event()

IS_ASSISTANT_SPEAKING = False  # Global flag for speech playback
SPEECH_LOCK = threading.Lock()  # Lock to ensure only one speech at a time


def _sound_worker():
    global CURRENT_CHANNEL, IS_ASSISTANT_SPEAKING
    while not STOP_EVENT.is_set():
        if SOUND_QUEUE:
            with QUEUE_LOCK:
                sound_path, is_speech = SOUND_QUEUE.popleft()
            try:
                if is_speech:
                    # Only allow one speech at a time
                    acquired = SPEECH_LOCK.acquire(blocking=False)
                    if not acquired:
                        continue  # Skip this speech, another is playing
                    IS_ASSISTANT_SPEAKING = True
                sound = pygame.mixer.Sound(sound_path)
                CURRENT_CHANNEL = sound.play()
                while CURRENT_CHANNEL.get_busy() and not STOP_EVENT.is_set():
                    time.sleep(0.01)
                if is_speech:
                    IS_ASSISTANT_SPEAKING = False
                    SPEECH_LOCK.release()
            except Exception as e:
                if is_speech and SPEECH_LOCK.locked():
                    IS_ASSISTANT_SPEAKING = False
                    SPEECH_LOCK.release()
                pass
        else:
            time.sleep(0.01)

SOUND_THREAD = threading.Thread(target=_sound_worker, daemon=True)
SOUND_THREAD.start()

def queue_sound(sound_path, is_speech=False):
    with QUEUE_LOCK:
        SOUND_QUEUE.append((sound_path, is_speech))

def force_play_sound(sound_path, is_speech=False):
    global IS_ASSISTANT_SPEAKING
    if is_speech:
        # Only interrupt if currently speaking
        if not IS_ASSISTANT_SPEAKING:
            return
        interrupt_sounds()
        try:
            acquired = SPEECH_LOCK.acquire(blocking=False)
            if not acquired:
                return
            IS_ASSISTANT_SPEAKING = True
            sound = pygame.mixer.Sound(sound_path)
            sound.play()
            while sound.get_num_channels() > 0:
                time.sleep(0.01)
            IS_ASSISTANT_SPEAKING = False
            SPEECH_LOCK.release()
        except Exception:
            if SPEECH_LOCK.locked():
                IS_ASSISTANT_SPEAKING = False
                SPEECH_LOCK.release()
            pass
    else:
        interrupt_sounds()
        try:
            sound = pygame.mixer.Sound(sound_path)
            sound.play()
        except Exception:
            pass

def interrupt_sounds():
    global CURRENT_CHANNEL, IS_ASSISTANT_SPEAKING
    if IS_ASSISTANT_SPEAKING and CURRENT_CHANNEL and CURRENT_CHANNEL.get_busy():
        STOP_EVENT.set()
        CURRENT_CHANNEL.fadeout(FADEOUT_MS)
        pygame.mixer.stop()
        with QUEUE_LOCK:
            SOUND_QUEUE.clear()
        IS_ASSISTANT_SPEAKING = False
        time.sleep(FADEOUT_MS / 1000.0)
        STOP_EVENT.clear()
        global SOUND_THREAD
        if not SOUND_THREAD.is_alive():
            SOUND_THREAD = threading.Thread(target=_sound_worker, daemon=True)
            SOUND_THREAD.start()


def play_open_sound():
    force_play_sound(OPEN_SOUND, is_speech=False)

def play_close_sound():
    force_play_sound(CLOSE_SOUND, is_speech=False)

def play_pop_sound():
    force_play_sound(POP_SOUND, is_speech=False)
