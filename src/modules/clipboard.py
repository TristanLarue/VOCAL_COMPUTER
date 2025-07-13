import os
import pyperclip
from utils import log

def run(actionType=None, filename=None, text=None, **kwargs):
    script_name = "clipboard.py"
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
    os.makedirs(temp_dir, exist_ok=True)
    if actionType == "get":
        if not filename:
            log("Missing required argument: filename for get action", "ERROR", script=script_name)
            return
        try:
            clipboard_content = pyperclip.paste()
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(clipboard_content)
            return {"filename": file_path}
        except Exception as e:
            log(f"Failed to save clipboard: {e}", "ERROR", script=script_name)
    elif actionType == "set":
        if text is None:
            log("Missing required argument: text for set action", "ERROR", script=script_name)
            return
        try:
            pyperclip.copy(text)
            return {"status": "success"}
        except Exception as e:
            log(f"Failed to set clipboard: {e}", "ERROR", script=script_name)
    else:
        log("Invalid or missing actionType. Must be 'get' or 'set'", "ERROR", script=script_name)
