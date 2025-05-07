import numpy as np
import wave
import whisper
import time
import os
import threading

from utils import log, Colors

# Audio recording constants
CHUNK = 1024
FORMAT = None  # Will be set from pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Porcupine requires 16kHz
SILENCE_THRESHOLD = 500
SILENCE_CHUNKS = int(RATE / CHUNK * 2)  # ~2 seconds of silence
MAX_LISTEN_TIME = int(RATE / CHUNK * 5)  # ~5 seconds max listening time after AI speech

# Timing metrics
transcription_start = 0
transcription_end = 0

# Global state
current_rms = 0
prompt_end_time = 0
is_ai_speaking = False
continuous_recording_active = False
continuous_recording_thread = None
recording_frames = []

# Initialize Whisper model
def initialize_whisper():
    """Initialize the Whisper model for transcription"""
    return whisper.load_model("tiny")

def record_audio(stream):
    """Record audio until silence is detected"""
    global prompt_end_time, current_rms
    frames = []
    silence_count = 0
    log("Recording started...", "AUDIO")
    
    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio**2))
        current_rms = round(rms)
        
        if rms < SILENCE_THRESHOLD:
            silence_count += 1
            if silence_count > SILENCE_CHUNKS:
                break
        else:
            silence_count = 0
    
    current_rms = 0
    prompt_end_time = time.time()
    log(f"Recording finished ({len(frames)} frames)", "AUDIO")
    return frames

def save_wav(filename, frames, pa):
    """Save audio frames to WAV file"""
    import pyaudio  # Import here to avoid circular imports
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))  # Using FORMAT constant from pyaudio
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    log(f"Saved audio to {filename}", "AUDIO")

def transcribe_audio(filename, model=None):
    """Transcribe audio using Whisper"""
    global transcription_start, transcription_end
    
    if model is None:
        model = initialize_whisper()
    
    log("Transcribing audio...", "WHISPER")
    transcription_start = time.time()
    result = model.transcribe(filename)
    transcription_end = time.time()
    
    text = result.get("text", "").strip()
    log(f"Transcription duration: {Colors.BOLD}{(transcription_end-transcription_start):.3f}s{Colors.ENDC}", "TIMING")
    log(f"Transcription result: {Colors.BOLD}{text}{Colors.ENDC}", "WHISPER")
    
    return text

def get_prompt_end_time():
    """Return the time when the prompt ended"""
    return prompt_end_time

def set_ai_speaking_state(is_speaking):
    """Set the global state tracking if AI is currently speaking"""
    global is_ai_speaking
    is_ai_speaking = is_speaking
    log(f"AI speaking state: {is_speaking}", "INFO")

def start_continuous_recording(audio_stream, pa):
    """Start continuous recording in a separate thread"""
    global continuous_recording_active, continuous_recording_thread
    
    if continuous_recording_active:
        log("Continuous recording already active", "INFO")
        return
    
    continuous_recording_active = True
    continuous_recording_thread = threading.Thread(
        target=continuous_recording_loop,
        args=(audio_stream, pa),
        daemon=True
    )
    continuous_recording_thread.start()
    log("Continuous recording started", "INFO")

def stop_continuous_recording():
    """Stop the continuous recording thread"""
    global continuous_recording_active
    continuous_recording_active = False
    log("Continuous recording stopped", "INFO")

def continuous_recording_loop(audio_stream, pa):
    """Continuously record audio and process when speech detected"""
    global continuous_recording_active, recording_frames, is_ai_speaking
    
    # Get Whisper model
    whisper_model = initialize_whisper()
    
    # Import here to avoid circular imports
    from chat import process_voice_query
    
    silence_count = 0
    speech_detected = False
    post_speech_count = 0
    current_frames = []
    
    log("Continuous recording loop started", "AUDIO")
    
    while continuous_recording_active:
        # Get audio chunk
        data = audio_stream.read(CHUNK, exception_on_overflow=False)
        current_frames.append(data)
        
        # Process audio for activity detection
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio**2))
        
        # If AI is speaking, check for interruption
        if is_ai_speaking:
            if rms > SILENCE_THRESHOLD * 1.2:  # Higher threshold for interruption
                # User is speaking while AI is speaking - this is an interruption
                log(f"User interruption detected while AI speaking (RMS: {rms})", "INFO")
                from sounds import stop_current_speech
                stop_current_speech()
                
                # Wait a moment to collect a bit more of the interruption
                time.sleep(0.3)
                
                # Add a few more frames to get the start of the interruption
                for _ in range(3):
                    try:
                        additional_data = audio_stream.read(CHUNK, exception_on_overflow=False)
                        current_frames.append(additional_data)
                    except:
                        pass
                
                # Process the interruption
                log("Processing interruption", "AUDIO")
                process_voice_query(current_frames, pa, audio_stream)
                
                # Reset frames and continue recording
                current_frames = []
                speech_detected = False
                silence_count = 0
                
        # If AI is not speaking, look for new user speech
        else:
            if rms > SILENCE_THRESHOLD:
                # Reset silence counter since we heard something
                silence_count = 0
                
                # If this is new speech, mark it
                if not speech_detected:
                    speech_detected = True
                    log("New speech detected in continuous recording", "AUDIO")
            
            elif speech_detected:
                # Count silence after speech
                silence_count += 1
                
                # If we've had enough silence after speech, process it
                if silence_count > SILENCE_CHUNKS:
                    log("Speech followed by silence - processing query", "AUDIO")
                    
                    # Process this as a new query
                    process_voice_query(current_frames, pa, audio_stream)
                    
                    # Reset for next recording
                    current_frames = []
                    speech_detected = False
                    silence_count = 0
            
            # If AI has finished speaking, count up to max listening time
            elif post_speech_count < MAX_LISTEN_TIME:
                post_speech_count += 1
                
                # If we've waited the max time with no new speech, trim the buffer
                if post_speech_count >= MAX_LISTEN_TIME:
                    # Keep a small buffer for context
                    buffer_size = SILENCE_CHUNKS * CHUNK
                    if len(current_frames) > buffer_size:
                        current_frames = current_frames[-buffer_size:]
                    post_speech_count = 0
                    
        # Prevent buffer from growing too large during silence
        if not speech_detected and len(current_frames) > MAX_LISTEN_TIME * CHUNK:
            # Keep only the most recent audio
            current_frames = current_frames[-SILENCE_CHUNKS * CHUNK:]
            
        # Small sleep to reduce CPU usage
        time.sleep(0.01)