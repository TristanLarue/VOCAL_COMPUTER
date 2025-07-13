import webbrowser
from utils import log

def run(url=None, **kwargs):
    script_name = "browse.py"
    if not url:
        log("Missing required argument: url", "ERROR", script=script_name)
        return
    try:
        webbrowser.open(url)
    except Exception as e:
        log(f"Failed to open URL {url}: {e}", "ERROR", script=script_name)
