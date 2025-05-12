import numpy as np
import wave
import whisper
import time
import os
import threading
import collections

from utils import log, Colors

# Audio recording constants
CHUNK = 1024
FORMAT = None  # Will be set from pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Porcupine requires 16kHz
SILENCE_THRESHOLD = 500
SILENCE_CHUNKS = int(RATE / CHUNK * 2)  # ~2 seconds of silence
MAX_LISTEN_TIME = int(RATE / CHUNK * 5)  # ~5 seconds max listening time after AI speech
BUFFER_KEEP_CHUNKS = 5  # Number of silence chunks to keep before speech (for context)
RMS_HISTORY_DURATION = int(RATE / CHUNK * 1)  # ~1 seconds of RMS history for interruption detection

# Timing metrics
transcription_start = 0
transcription_end = 0

# Global state
current_rms = 0
prompt_end_time = 0
is_ai_speaking = False
continuous_recording_active = False
continuous_recording_thread = None
all_frames = []  # Main buffer to store ALL recorded frames
max_frames_stored = int(RATE / CHUNK * 60 * 5)  # Store max ~5 minutes of audio to prevent memory issues

# Initialize Whisper model
def initialize_whisper():
    """Initialize the Whisper model for transcription"""
    return whisper.load_model("tiny")

def save_wav(filename, frames, pa):
    """Save audio frames to WAV file"""
    import pyaudio  # Import here to avoid circular imports
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))  # Using FORMAT constant from pyaudio
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

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

def process_voice_query(frames, pa, audio_stream):
    """Process a voice query from recorded audio frames"""
    global whisper_model
    
    # Get the Whisper model
    whisper_model = initialize_whisper()
    
    # Save recorded audio to a temporary file
    save_wav("temp.wav", frames, pa)
    
    # Transcribe the recorded audio
    query = transcribe_audio("temp.wav", whisper_model)
    
    # Clean up temp file
    try:
        os.remove("temp.wav")
    except:
        pass
    
    # If no query was detected, continue continuous recording
    if not query:
        log("No query detected, continuing recording", "INFO")
        return
    
    # Get the current conversation memory
    from memory import get_memory
    conversation_memory = get_memory()
    
    # Import here to avoid circular dependencies
    from sounds import play_pop_sound, speak_text
    from chat import call_chatgpt
    
    # Process query with ChatGPT
    answer = call_chatgpt(query, conversation_memory)
    
    # Update memory with new conversation
    from memory import update_memory
    threading.Thread(target=update_memory, args=(query, answer), daemon=True).start()
    
    # Clean text and extract commands
    from chat import extract_commands
    clean_text, commands = extract_commands(answer)
    clean_text = clean_text.strip()  # Remove any trailing whitespace after command removal
    
    log(f"Speaking: {Colors.BOLD}{clean_text}{Colors.ENDC}", "INFO")
    if commands:
        log(f"Commands detected: {len(commands)}", "COMMAND")
    
    # Import here to avoid circular imports
    from commands import execute_command
    
    # First, speak the response regardless of commands
    if clean_text:
        speak_text(clean_text, audio_stream)
    
    # Now execute commands after speaking is done
    has_exit_command = False
    for cmd, param in commands:
        if cmd.lower() == "exit":
            has_exit_command = True
            # Save exit for last
            continue
            
        result = execute_command(cmd, param, audio_stream)
        log(f"Command result: {result}", "COMMAND")
    
    # Execute exit command last if present
    if has_exit_command:
        result = execute_command("exit", "", audio_stream)
        log(f"Command result: {result}", "COMMAND")

def get_prompt_end_time():
    """Return the time when the prompt ended"""
    return prompt_end_time

def set_ai_speaking_state(is_speaking):
    """Set the global state tracking if AI is currently speaking"""
    global is_ai_speaking
    is_ai_speaking = is_speaking
    #log(f"AI speaking state: {is_speaking}", "INFO")

def start_continuous_recording(audio_stream, pa):
    """Start continuous recording in a separate thread"""
    global continuous_recording_active, continuous_recording_thread, all_frames
    
    if continuous_recording_active:
        log("Continuous recording already active", "INFO")
        return
    
    # Reset the frames buffer
    all_frames = []
    
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
    # Import here to avoid circular imports
    from triggers import initialize_wake_word_mode, set_wake_word_active
    # Switch back to wake word detection mode
    initialize_wake_word_mode()
    # Explicitly set wake word active state
    set_wake_word_active(True)
    
    # Reset any state that might prevent wake word detection
    from sounds import play_close_sound,reset_speech_state
    play_close_sound()
    reset_speech_state()
    
    # Reset conversation memory
    from memory import reset_memory
    #reset_memory()
    log("Continuous recording stopped", "INFO")

def continuous_recording_loop(audio_stream, pa):
    """Continuously record audio and process when speech detected"""
    global continuous_recording_active, is_ai_speaking, prompt_end_time, all_frames
    
    # Initialize variables for recording management
    silence_count = 0
    speech_detected = False
    
    # Buffer to keep recent audio for context (2 seconds of audio before speech)
    buffer_size = int(RATE / CHUNK * 2)  # ~2 seconds of audio chunks
    buffer_frames = collections.deque(maxlen=buffer_size)
    
    # Variables for RMS average calculation
    rms_history = collections.deque(maxlen=RMS_HISTORY_DURATION)
    
    # Variables for auto-closing conversation
    inactivity_counter = 0
    ai_finished_speaking_time = 0
    waiting_for_ai_response = False
    
    # Define the inactivity timeout (15 seconds)
    INACTIVITY_TIMEOUT = int(RATE / CHUNK * 15)  # ~15 seconds of inactivity
    
    log("Continuous recording loop started", "AUDIO")
    
    while continuous_recording_active:
        # Always get audio chunk - continuous recording never stops
        try:
            data = audio_stream.read(CHUNK, exception_on_overflow=False)
            
            # Process audio for activity detection
            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(audio**2))
            current_rms = round(rms)
            
            # Store RMS value in history
            rms_history.append(rms)
            
            # Track when AI stops speaking to start inactivity timer
            if is_ai_speaking:
                # Reset inactivity counters while AI is speaking
                inactivity_counter = 0
                ai_finished_speaking_time = 0
                waiting_for_ai_response = False
                # Only check for interruption if we have enough RMS history
                if len(rms_history) >= int(RATE / CHUNK * 0.5):  # At least 0.5 seconds of history
                    # Calculate average RMS over the last 2 seconds (or whatever we have)
                    avg_rms = sum(rms_history) / len(rms_history)
                    
                    # If average RMS exceeds threshold, consider it an interruption
                    if avg_rms > SILENCE_THRESHOLD * 1.2:  # Slightly lower threshold for average
                        log(f"Interruption detected - average RMS over last 2s: {avg_rms:.2f}", "INFO")
                        
                        # Start keeping frames for the interruption
                        speech_detected = True
                        silence_count = 0
                        waiting_for_ai_response = False  # No longer waiting for AI response
                        
                        # Add current frame and buffer frames to all_frames
                        all_frames = list(buffer_frames)
                        all_frames.append(data)
                        
                        # Launch stop_current_speech asynchronously to fade out
                        from sounds import stop_current_speech
                        threading.Thread(target=stop_current_speech, daemon=True).start()
                        
                        # Clear RMS history after interruption
                        rms_history.clear()
                    else:
                        # Still update buffer frames during AI speech when no interruption
                        buffer_frames.append(data)
                else:
                    # Update buffer frames when not enough RMS history
                    buffer_frames.append(data)
                    
            # If AI is not speaking, look for new user speech
            else:
                if not speech_detected:
                    # If speech hasn't been detected yet, only keep the last 2 seconds
                    buffer_frames.append(data)
                    
                    if rms > SILENCE_THRESHOLD:
                        # New speech detected! Start keeping all frames
                        speech_detected = True
                        silence_count = 0
                        # Reset inactivity timer when user starts speaking
                        inactivity_counter = 0
                        ai_finished_speaking_time = 0
                        waiting_for_ai_response = False
                        
                        # Transfer buffer frames to all_frames for processing
                        all_frames = list(buffer_frames)
                        log("New speech detected in continuous recording", "AUDIO")
                else:
                    # Speech already detected, keep recording everything
                    all_frames.append(data)
                    
                    if rms > SILENCE_THRESHOLD:
                        # Reset silence counter since we heard something
                        silence_count = 0
                    else:
                        # Count silence after speech
                        silence_count += 1
                        
                        # If we've had enough silence after speech, process it
                        if silence_count > SILENCE_CHUNKS:
                            log("Speech followed by silence - processing query", "AUDIO")
                            prompt_end_time = time.time()
                            
                            # Process the recorded frames
                            frames_to_process = all_frames.copy()
                            
                            # Launch process_voice_query asynchronously
                            threading.Thread(
                                target=process_voice_query, 
                                args=(frames_to_process, pa, audio_stream),
                                daemon=True
                            ).start()
                            
                            # Reset state
                            speech_detected = False
                            silence_count = 0
                            all_frames = []  # Wipe all frames after processing
                            buffer_frames.clear()  # Also clear buffer frames
                            rms_history.clear()  # Clear RMS history
                            
                            # Mark that we're waiting for AI response
                            waiting_for_ai_response = True
                
                # Check if we need to start/continue inactivity counting
                if not speech_detected and not is_ai_speaking and not waiting_for_ai_response:
                    # If AI has just finished speaking, mark the time
                    if ai_finished_speaking_time == 0:
                        ai_finished_speaking_time = time.time()
                        log("AI finished speaking - starting inactivity timer", "INFO")
                    
                    # Count inactivity
                    inactivity_counter += 1
                    
                    # Check if we've reached the timeout
                    if inactivity_counter >= INACTIVITY_TIMEOUT:
                        log("Inactivity timeout reached (15 seconds) - closing conversation", "INFO")
                        stop_continuous_recording()
                        break
                else:
                    # Reset inactivity counter if there's any activity
                    if inactivity_counter > 0:
                        log("Activity detected - resetting inactivity timer", "INFO")
                    inactivity_counter = 0
                    ai_finished_speaking_time = 0
                
        except Exception as e:
            log(f"Error in continuous recording: {e}", "ERROR")