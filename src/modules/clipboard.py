import os
import pyperclip
from utils import log

def run(actionType=None, filename=None, text=None, **kwargs):
    script_name = "clipboard.py"
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
    os.makedirs(temp_dir, exist_ok=True)
    if actionType == "get":
        if not filename:
            log(f"[clipboard.py]\n[ERROR]\nMissing required argument: filename for get action.", level="ERROR", script=script_name)
            return
        try:
            clipboard_content = pyperclip.paste()
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(clipboard_content)
            log(f"[clipboard.py] Clipboard content saved to {file_path}", level="INFO", script=script_name)
            return {"filename": file_path}
        except Exception as e:
            log(f"[clipboard.py]\n[ERROR]\nFailed to save clipboard: {e}", level="ERROR", script=script_name)
    elif actionType == "set":
        if text is None:
            log(f"[clipboard.py]\n[ERROR]\nMissing required argument: text for set action.", level="ERROR", script=script_name)
            return
        try:
            pyperclip.copy(text)
            log(f"[clipboard.py] Clipboard updated successfully.", level="INFO", script=script_name)
            return {"status": "success"}
        except Exception as e:
            log(f"[clipboard.py]\n[ERROR]\nFailed to set clipboard: {e}", level="ERROR", script=script_name)
    else:
        log(f"[clipboard.py]\n[ERROR]\nInvalid or missing actionType. Must be 'get' or 'set'.", level="ERROR", script=script_name)
