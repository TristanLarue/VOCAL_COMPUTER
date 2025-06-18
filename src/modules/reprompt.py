import re
import os
import json
import asyncio
import base64
from utils import log
from API import send_openai_request
from commands import execute_commands_from_response_block_sync

def run(prompt=None, filenames=None, context=None, **kwargs):
    script_name = "reprompt.py"
    if not prompt:
        log(f"[reprompt.py]\n[ERROR]\nMissing required argument: prompt.", level="ERROR", script=script_name)
        return
    # --- Load baseprompt, settings, commands, memory ---
    try:
        base_dir = os.path.dirname(__file__)
        with open(os.path.join(base_dir, '../../assets/baseprompt.json'), 'r', encoding='utf-8') as f:
            baseprompt = json.load(f)
        with open(os.path.join(base_dir, '../../assets/settings.json'), 'r', encoding='utf-8') as f:
            settings = json.load(f)
        with open(os.path.join(base_dir, '../../assets/commands.json'), 'r', encoding='utf-8') as f:
            commands = json.load(f).get('commands', [])
        with open(os.path.join(base_dir, '../../assets/memory.json'), 'r', encoding='utf-8') as f:
            memory = json.load(f)
        baseprompt['settings'] = settings
        baseprompt['commands'] = commands
        baseprompt['memory'] = memory  # Load full memory.json as the memory key
        baseprompt['user_prompt'] = prompt
        if context is not None:
            baseprompt['context'] = context
        elif 'context' in baseprompt:
            del baseprompt['context']
    except Exception as e:
        log(f"[reprompt.py]\n[ERROR]\nFailed to load baseprompt/settings/commands/memory: {e}", level="ERROR", script=script_name)
        return
    # --- Prepare user_content for API ---
    user_content = []
    # Add memory/context and prompt as text
    memory_context = json.dumps(baseprompt, ensure_ascii=False)
    user_content.append({"type": "text", "text": memory_context + prompt})
    # Attach image as base64 data URI if provided
    file_list = []
    if filenames:
        if isinstance(filenames, str):
            cleaned = filenames.strip().strip('[]')
            file_list = [f.strip() for f in re.split(r'[;,|]', cleaned) if f.strip()]
        elif isinstance(filenames, list):
            file_list = filenames
    for fname in file_list:
        file_path = fname if os.path.isabs(fname) else os.path.abspath(os.path.join(base_dir, '../../temp', fname))
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                try:
                    with open(file_path, 'rb') as f:
                        img_bytes = f.read()
                    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                    mime = 'image/png' if ext == '.png' else 'image/jpeg'
                    image_data_uri = f"data:{mime};base64,{img_b64}"
                    user_content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
                except Exception as e:
                    log(f"[reprompt.py]\n[ERROR]\nFailed to encode image {file_path}: {e}", level="ERROR", script=script_name)
    # --- Call the API ---
    payload = {"model": "gpt-4.1", "messages": [{"role": "user", "content": user_content}]}
    response = send_openai_request('chat/completions', payload)
    # --- Process the response through commands.py ---
    content = None
    try:
        if response and 'choices' in response and response['choices']:
            content = response['choices'][0]['message']['content']
    except Exception as e:
        log(f"[reprompt.py]\n[ERROR]\nMalformed API response: {response}\n{e}", level="ERROR", script=script_name)
    if content:
        for line in content.split('\n'):
            if line.strip().startswith('/'):
                log(f"Executing command: {line.strip()}", "COMMAND")
        if asyncio.iscoroutinefunction(execute_commands_from_response_block_sync):
            asyncio.run(execute_commands_from_response_block_sync(content))
        else:
            execute_commands_from_response_block_sync(content)
        log("All commands executed. AI response complete.", "COMMAND")
    return content
