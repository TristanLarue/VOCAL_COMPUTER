import requests
import os
import json
from dotenv import load_dotenv
import traceback
from utils import log

load_dotenv()

def send_openai_request(endpoint, payload, headers=None, files=None, stream=False):
    """
    Generic function to send a request to any OpenAI endpoint.
    endpoint: e.g. 'chat/completions' or 'audio/speech'
    payload: dict to send as JSON
    headers: dict of headers (optional)
    files: for file uploads (optional)
    stream: if True, stream response (for TTS)
    Returns: raw response object or response.json()
    """
    try:
        url = f"https://api.openai.com/v1/{endpoint}"
        if headers is None:
            headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"}
        response = requests.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload, stream=stream)
        response.raise_for_status()
        if stream:
            return response  # caller handles streamed data
        return response.json()
    except Exception as e:
        log(f"OpenAI API request failed: {e}\n{traceback.format_exc()}", "ERROR")
        return None
