import asyncio
from utils import log

async def run(seconds=1, **kwargs):
    try:
        seconds = int(seconds)
        log(f"Waiting for {seconds} seconds...", "INFO")
        await asyncio.sleep(seconds)
    except Exception as e:
        log(f"Error in wait.py run: {e}", "ERROR")
