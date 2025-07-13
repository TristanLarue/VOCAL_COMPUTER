# VOCAL_COMPUTER

VOCAL_COMPUTER is a modular, voice-activated Python assistant designed for desktop automation, smart device control, and AI-powered conversation. It features speech recognition, text-to-speech, sound effects, memory management, and integration with services like Spotify and Smart Life (Tuya).

## Features

- **Wake Word Detection:** Listens for a wake word ("computer") to activate the assistant.
- **Speech Recognition:** Uses OpenAI Whisper for accurate audio-to-text transcription.
- **Text-to-Speech:** Converts AI or system responses to speech, with natural-sounding voice and sentence splitting.
- **Sound Effects:** Plays sound effects (e.g., pop, open, close) without interrupting speech.
- **Speech Queue:** Handles speech as a queue, ensuring ordered, non-overlapping playback.
- **Speech Interruption:** User speech can interrupt AI speech, with optional fade-out.
- **Memory Management:** Summarizes and stores conversation context for continuity.
- **Spotify Integration:** Control playback, volume, and device selection via voice.
- **Clipboard, Screenshot, and Browser Modules:** Automate common desktop tasks.
- **Smart Device Control:** (Planned) Control Smart Life/Tuya devices locally or via IFTTT.
- **Settings Management:** Change assistant settings via voice or command.
- **Extensible Modules:** Easily add new commands or integrations.

## Directory Structure

```
VOCAL_COMPUTER/
├── assets/           # Prompts, settings, sound files, memory, etc.
├── src/
│   ├── main.py       # Entry point, initializes and runs the assistant
│   ├── triggers.py   # Wake word, audio management, and main loop
│   ├── transcribe.py # Whisper-based audio transcription
│   ├── sounds.py     # Sound system (effects, speech, queue, interruption)
│   ├── memory.py     # Conversation memory summarization
│   ├── commands.py   # Command parsing and module dispatch
│   ├── utils.py      # Logging, settings, and helpers
│   └── modules/
│       ├── speak.py      # Text-to-speech and speech queueing
│       ├── spotify.py    # Spotify control
│       ├── clipboard.py  # Clipboard automation
│       ├── screenshot.py # Screenshot capture
│       ├── browse.py     # Open URLs in browser
│       ├── wait.py       # Wait/delay command
│       ├── settings.py   # Change assistant settings
│       ├── reprompt.py   # Re-ask or clarify user input
│       ├── exit.py       # Force sleep mode
│       └── smartlife.py  # (Planned) Smart Life/Tuya device control
├── temp/             # Temporary files (audio, screenshots, etc.)
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## How It Works

1. **Startup:**
   - Loads environment variables and settings.
   - Starts the speech worker and wake word detection.
2. **Wake Word:**
   - Listens for "computer" using Porcupine.
   - On detection, enters "awake" mode.
3. **User Speech:**
   - Records and transcribes user speech.
   - Passes text to the AI (OpenAI GPT-4) and/or command modules.
4. **AI/Command Response:**
   - AI response is split into sentences, converted to speech, and queued for playback.
   - Sound effects are played as needed.
   - Commands (e.g., /spotify, /screenshot) are dispatched to modules.
5. **Memory:**
   - Conversation context is summarized and stored for continuity.
6. **Shutdown:**
   - Cleans up memory and temp files if not in permanent-memory mode.

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies
- Microphone and speakers
- (Optional) Spotify, Smart Life/Tuya, or other service accounts for integrations

## Setup

1. Clone the repository.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Configure your environment variables (see `.env.example` or set up manually for OpenAI, Spotify, etc.).
4. Run the assistant:
   ```sh
   python src/main.py
   ```

## Extending
- Add new modules in `src/modules/` and register them in `assets/commands.json`.
- See existing modules for examples.

## License
MIT
