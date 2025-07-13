import sys
import os
from contextlib import redirect_stdout, redirect_stderr

# Suppress pygame welcome and version messages
with open(os.devnull, 'w') as devnull, redirect_stdout(devnull), redirect_stderr(devnull):
    import pygame
    pygame.mixer.init()

import threading
import asyncio
import time
from collections import deque

# Global variables
IS_ASSISTANT_SPEAKING = False
speech_channel = None
highest_speech_key = 0
speech_path_queue = deque()

SOUND_EFFECT_CHANNEL = pygame.mixer.Channel(0)
SPEECH_CHANNEL_INDEX = 1

# Play sound effect immediately, never interrupted
def play_sound_effect(path):
    sound = pygame.mixer.Sound(path)
    SOUND_EFFECT_CHANNEL.play(sound)

# Speech gateway: manages queue and timestamp logic
def queue_speech(path, timestamp):
    global highest_speech_key, speech_path_queue
    if timestamp < highest_speech_key:
        return  # Block old speech
    elif timestamp == highest_speech_key:
        speech_path_queue.append((path, timestamp))
    else:
        highest_speech_key = timestamp
        speech_path_queue.append((path, timestamp))

# Async worker for speech playback
async def speech_worker():
    global IS_ASSISTANT_SPEAKING, speech_channel, speech_path_queue
    while True:
        if speech_path_queue:
            path, _ = speech_path_queue.popleft()
            IS_ASSISTANT_SPEAKING = True
            speech_channel = pygame.mixer.Channel(SPEECH_CHANNEL_INDEX)
            sound = pygame.mixer.Sound(path)
            speech_channel.play(sound)
            # Delete the file after playing
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Failed to delete speech file {path}: {e}")
            while speech_channel.get_busy():
                await asyncio.sleep(0.1)
            # Add a small wait to sound more natural
            await asyncio.sleep(0.3)
            IS_ASSISTANT_SPEAKING = False
            speech_channel = None
        else:
            await asyncio.sleep(0.1)

# Start the async worker in a background thread
def start_speech_worker():
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_until_complete, args=(speech_worker(),), daemon=True)
    t.start()

def interrupt_speech(fade_out: bool):
    global highest_speech_key, speech_path_queue, speech_channel, IS_ASSISTANT_SPEAKING
    highest_speech_key += 1
    speech_path_queue.clear()
    if speech_channel is not None:
        if fade_out:
            speech_channel.fadeout(500)
        else:
            speech_channel.stop()
        # Immediately update the speaking flag
        IS_ASSISTANT_SPEAKING = False
        speech_channel = None
