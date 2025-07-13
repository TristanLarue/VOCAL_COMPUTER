from datetime import datetime
import json
import os

class Colors:
    """ANSI color codes for console output"""
    # New logging categories
    SYSTEM = '\033[1m\033[97m'      # white bold
    TRIGGER = '\033[38;5;208m'      # orange
    TRANSCRIPTION = '\033[95m'      # purple
    API = '\033[94m'                # blue
    COMMAND = '\033[38;5;219m'      # pink
    CONTEXT = '\033[90m'            # gray
    ERROR = '\033[1m\033[91m'       # red bold
    COST = '\033[93m'               # yellow
    
    # Legacy colors (kept for compatibility)
    HEADER = '\033[95m'
    INFO = '\033[94m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    AUDIO = '\033[96m'
    WHISPER = '\033[95m'
    GPT = '\033[92m'
    BYPASS = '\033[93m'
    TIMING = '\033[38;5;208m'
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

def log(message, level="SYSTEM", script=None):
    """Format and print a log message with timestamp and color"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Get color for the level
    color = getattr(Colors, level, Colors.INFO)
    
    # Only show script name for ERROR logs
    if level == "ERROR" and script:
        script_tag = f"[{script}]"
    else:
        script_tag = ""
    
    print(f"{color}[{timestamp}] [{level}]{script_tag}{Colors.ENDC} {message}")

def log_cost_summary(total_cost, token_cost, tts_cost):
    """Log the cost summary after AI prompts"""
    message = f"TOTAL CURRENT COST: {total_cost:.4f}¢ / TTT Tokens Cost: {token_cost:.4f}¢ / TTS Tokens Cost: {tts_cost:.4f}¢"
    log(message, "COST")

def log_command_execution(module_name, args):
    """Log command execution in a readable format"""
    # Format arguments in a readable way
    if args:
        arg_str = ", ".join([f"{k}={v}" for k, v in args.items() if v is not None])
        message = f"Executing {module_name}({arg_str})"
    else:
        message = f"Executing {module_name}()"
    log(message, "COMMAND")

def get_settings():
    """Return the settings as a dict mapping setting-id to value, for compatibility with old code."""
    try:
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/settings.json'))
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_list = json.load(f)
        # Convert to dict: {setting-id: value}
        return {s['setting-id']: s['value'] for s in settings_list if 'setting-id' in s and 'value' in s}
    except Exception as e:
        log(f"Error reading all settings: {e}", "ERROR")
        return None

def log_finetune_example(user_prompt, assistant_response):
    """
    Appends a training example to log.jsonl in OpenAI fine-tuning format.
    Each line: {"messages": [{"role": "user", "content": ...}, {"role": "assistant", "content": ...}]}
    """
    import json
    import os
    log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../log.jsonl'))
    entry = {
        "messages": [
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ]
    }
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def update_tts_cost(cost_cents):
    """Update global TTS cost tracking"""
    try:
        import triggers
        triggers.TOTAL_TTS_COST_CENTS += cost_cents
        triggers.TOTAL_COST_CENTS = triggers.TOTAL_TOKEN_COST_CENTS + triggers.TOTAL_TTS_COST_CENTS
    except Exception as e:
        log(f"Error updating TTS cost: {e}", "ERROR", script="utils.py")
