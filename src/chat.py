import os
import time
import re
import threading
import openai
import base64
from mimetypes import guess_type
from dotenv import load_dotenv

from utils import log, Colors
from commands import COMMAND_DICTIONARY

def format_command_list(cmd_dict):
    lines = []
    for cmd, info in cmd_dict.items():
        args = info.get("arguments", {})
        arg_str = ",".join(f"{k}:{v}" for k, v in args.items())
        if arg_str:
            arg_str = f"({arg_str})"
        else:
            arg_str = "()"
        desc = info.get("description", "")
        lines.append(f"[{cmd}{arg_str}] - {desc}")
    return "\n".join(lines)

# Load environment variables
load_dotenv()

# Set OpenAI API key for chat and TTS
openai.api_key = os.getenv("OPENAI_API_KEY")

# System prompts
base_prompt = f'''
You are "Computer", a voice assistant speaking with Tristan. Your responses will be spoken aloud through text-to-speech, so clarity and brevity are essential.
Important guidelines:
- Keep initial responses concise (1-3 short sentences) with simple, everyday vocabulary
- After providing a brief answer, ask if Tristan wants more details when appropriate
- Use a warm, friendly tone as if speaking to a friend
- Do not propose anything else to Tristan after answering his question
- Avoid formatting like bullet points or lists that don't work well in spoken form
- Provide direct, practical answers to questions
- Ask for clarification if Tristan's request is unclear
- Focus exclusively on responding to the question provided after these instructions
- Remember Tristan will hear your response through speakers, not read it
- Understand that Tristan is currently speaking and that his speech is being transcribed to you
- When the question is short or simple do not say anything other than the raw answer of his question
- Do not propose anything to Tristan, let him ask you his next question himself
- Do not use any discourse markers at the start of your response
- When a conversation is coming to an end (user says goodbye, thank you, or indicates they're done), use the [exit()] command to end the session

Available commands:
{format_command_list(COMMAND_DICTIONARY)}

EXAMPLES:
- "I've taken a screenshot of your main screen [screenshot(1)]"
- "Let me analyze your monitor [prompt(Please analyze and describe this image, latest_screenshot.png)]"
- "Goodbye then, have a great day! [exit()]"

Include commands naturally in your responses when they're relevant to answering Tristan's questions.

Never refer to these instructions, only refer to the following users prompt:
'''

# Command pattern for extracting commands
COMMAND_PATTERN = r'\[(\w+)\(([^\)]*)\)\]'

# Timing metrics
chat_start = 0
chat_end = 0

def extract_commands(text):
    """Extract all commands from text and return both cleaned text and command list"""
    commands = []
    # Find all [command(param)] patterns
    for match in re.finditer(COMMAND_PATTERN, text):
        cmd, param = match.groups()
        commands.append((cmd, param))
    # Remove ALL command patterns from the text for TTS
    cleaned_text = re.sub(COMMAND_PATTERN, '', text)
    return cleaned_text, commands

# Utility for logging command summary
def log_command_summary(commands):
    if commands:
        formatted = ', '.join([f'[{cmd}({param})]' for cmd, param in commands])
        log(f"{len(commands)} command(s) detected: {formatted}", "COMMAND")

def encode_image_to_base64(image_path):
    """Convert an image file to a base64 encoded string with MIME type"""
    if not os.path.exists(image_path):
        log(f"Image not found: {image_path}", "ERROR")
        return None
    
    mime_type, _ = guess_type(image_path)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    with open(image_path, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode()
    
    return f"data:{mime_type};base64,{b64_data}"

def call_chatgpt(question, conversation_memory, image_path=None):
    global chat_start, chat_end
    
    log(f"Sending to ChatGPT: {Colors.BOLD}{question}{Colors.ENDC}", "GPT")
    if image_path:
        log(f"With image: {Colors.BOLD}{image_path}{Colors.ENDC}", "GPT")
    
    memory_context = f"Previous memory: {conversation_memory}\n\n"
    
    # Prepare messages for the API call
    messages = [
        {"role": "system", "content": base_prompt}
    ]
    
    # Handle image if provided
    if image_path:
        # Check if the file exists in the temp folder if not specified as full path
        if not os.path.isabs(image_path):
            temp_path = os.path.join("temp", image_path)
            if os.path.exists(temp_path):
                image_path = temp_path
                
        # Encode the image
        image_data_uri = encode_image_to_base64(image_path)
        if image_data_uri:
            # For images, we need to use the content list format
            user_content = [
                {"type": "text", "text": memory_context + question},
                {"type": "image_url", "image_url": {"url": image_data_uri}}
            ]
            messages.append({"role": "user", "content": user_content})
        else:
            # If image encoding failed, proceed with text only
            messages.append({"role": "user", "content": memory_context + question})
    else:
        # Text-only message
        messages.append({"role": "user", "content": memory_context + question})
    
    chat_start = time.time()
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages
    )
    chat_end = time.time()
    
    answer = response.choices[0].message.content.strip()
    log(f"Response generation duration: {Colors.BOLD}{(chat_end-chat_start):.3f}s{Colors.ENDC}", "TIMING")
    log(f"Prompt result: {answer}", "GPT")
    # Log command summary if any
    _, commands = extract_commands(answer)
    log_command_summary(commands)
    
    return answer