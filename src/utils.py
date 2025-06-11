from datetime import datetime

class Colors:
    """ANSI color codes for console output"""
    HEADER = '\033[95m'
    INFO = '\033[94m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    AUDIO = '\033[96m'
    WHISPER = '\033[95m'
    GPT = '\033[92m'
    BYPASS = '\033[93m'
    SYSTEM = '\033[97m'
    TIMING = '\033[38;5;208m'
    COMMAND = '\033[38;5;219m'
    TRIGGERS = '\033[38;5;214m'
    API = '\033[38;5;39m'
    SOUNDS = '\033[38;5;45m'
    MODULES = '\033[38;5;129m'
    MAIN = '\033[38;5;33m'
    PROMPT = '\033[38;5;207m'
    TTS = '\033[38;5;213m'
    EXIT = '\033[38;5;196m'
    SCREENSHOT = '\033[38;5;51m'
    WAIT = '\033[38;5;190m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log(message, level="INFO", script=None):
    """Format and print a log message with timestamp and color"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    # Map log level or script to color
    color = getattr(Colors, level, None)
    if not color and script:
        color = getattr(Colors, str(script).upper(), Colors.INFO)
    if not color:
        color = Colors.INFO
    script_tag = f"[{script}]" if script else ""
    print(f"{color}[{timestamp}] [{level}]{script_tag}{Colors.ENDC} {message}")