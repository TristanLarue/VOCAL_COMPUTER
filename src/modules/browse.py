import webbrowser
from utils import log

def run(url=None, **kwargs):
    script_name = "browse.py"
    if not url:
        log(f"[browse.py]\n[ERROR]\nMissing required argument: url.", level="ERROR", script=script_name)
        return
    try:
        webbrowser.open(url)
        log(f"[browse.py] Opened URL: {url}", level="INFO", script=script_name)
    except Exception as e:
        log(f"[browse.py]\n[ERROR]\nFailed to open URL {url}: {e}", level="ERROR", script=script_name)
