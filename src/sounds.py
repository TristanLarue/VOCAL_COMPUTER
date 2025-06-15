import os
import pygame
import threading
import time

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
pygame.mixer.init()

IS_ASSISTANT_SPEAKING = False  # Global flag for speech playback

NON_SPEECH_LOCK = threading.Lock()

FADEOUT_MS = 500

# --- Main Play Function ---
def play(sound_path, is_speech=False):
    """
    Play an audio file. If is_speech=True, interrupt any current speech and play immediately.
    If is_speech=False, play immediately (do not interrupt speech or other non-speech sounds).
    """
    global IS_ASSISTANT_SPEAKING
    if is_speech:
        interrupt()  # Interrupt any current speech
        threading.Thread(target=_play_blocking, args=(sound_path,), daemon=True).start()
    else:
        threading.Thread(target=_play_now, args=(sound_path,), daemon=True).start()

# --- Blocking Play (for speech) ---
def _play_blocking(sound_path):
    global IS_ASSISTANT_SPEAKING
    try:
        IS_ASSISTANT_SPEAKING = True
        sound = pygame.mixer.Sound(sound_path)
        channel = sound.play()
        while channel.get_busy():
            time.sleep(0.01)
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
            # Optionally fade out any non-speech sound after a short time
            # time.sleep(1.0)
            # channel.fadeout(FADEOUT_MS)
        except Exception:
            pass

# --- Utility for compatibility ---
def is_speaking():
    global IS_ASSISTANT_SPEAKING
    return IS_ASSISTANT_SPEAKING

# --- Backwards compatibility for other scripts ---
# These can be replaced in other scripts with play(path, is_speech=True/False)
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
    """
    Interrupts all current speech: fades out the current speech playback only.
    """
    global IS_ASSISTANT_SPEAKING
    try:
        # Fade out any currently playing speech (but not non-speech sounds)
        for channel in [pygame.mixer.Channel(i) for i in range(pygame.mixer.get_num_channels())]:
            if channel.get_busy():
                channel.fadeout(FADEOUT_MS)
        IS_ASSISTANT_SPEAKING = False
    except Exception:
        pass
