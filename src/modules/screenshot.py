import mss
import os
from utils import log
from PIL import Image

def run(monitorId=None, filename=None, **kwargs):
    """Entry point for the screenshot command. Accepts monitorId and filename as direct arguments or from kwargs."""
    script_name = "screenshot.py"
    # Accept both direct arguments and kwargs for compatibility
    if monitorId is None:
        monitor_id = kwargs.get('monitorId')
    else:
        monitor_id = monitorId
    if filename is None:
        filename_val = kwargs.get('filename')
    else:
        filename_val = filename
    if monitor_id is None or filename_val is None:
        log(f"[screenshot.py]\n[ERROR]\nMissing required arguments: monitorId and filename.", level="ERROR", script=script_name)
        return
    try:
        monitor_id_int = int(monitor_id)
    except ValueError:
        log(f"[screenshot.py]\n[ERROR]\nmonitorId must be an integer.", level="ERROR", script=script_name)
        return
    # Ensure screenshot is saved in /temp directory
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
    os.makedirs(temp_dir, exist_ok=True)
    filename_only = os.path.basename(filename_val)
    full_path = os.path.join(temp_dir, filename_only)
    with mss.mss() as sct:
        monitors = sct.monitors
        # monitorId=0: main (right, first), monitorId=1: secondary (left, second)
        if monitor_id_int < 0 or monitor_id_int > 1 or monitor_id_int >= len(monitors)-1:
            log(f"[screenshot.py]\n[ERROR]\nmonitorId {monitor_id_int} is out of range. Use 0 for main (right, first), 1 for secondary (left, second).", level="ERROR", script=script_name)
            return
        # mss.monitors[1] is the first physical monitor, [2] is the second, etc.
        # So, monitorId=0 -> monitors[1], monitorId=1 -> monitors[2]
        monitor = monitors[monitor_id_int + 1]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        img.save(full_path)
        return {
            'monitorId': monitor_id,
            'filename': full_path
        }