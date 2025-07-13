import os
import json
import requests
import traceback
from dotenv import load_dotenv
from utils import log

load_dotenv()

def send_openai_request(endpoint, payload, headers=None, stream=False):
    """Send request to OpenAI API"""
    try:
        url = f"https://api.openai.com/v1/{endpoint}"
        if headers is None:
            headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"}
        response = requests.post(url, headers={**headers, "Content-Type": "application/json"}, json=payload, stream=stream)
        response.raise_for_status()
        if stream:
            return response
        return response.json()
    except Exception as e:
        log(f"OpenAI API request failed: {e}\n{traceback.format_exc()}", "ERROR")
        return None

def chatgpt_text_to_text(*, prompt=None, **kwargs):
    """Send text to ChatGPT and get response"""
    if prompt is not None:
        payload = {
            "model": kwargs.get("model", "gpt-4.1"),
            "messages": [{"role": "user", "content": prompt}]
        }
        payload.update({k: v for k, v in kwargs.items() if k not in ("model",)})
    else:
        payload = kwargs
    return send_openai_request('chat/completions', payload)

memory_prompt = '''
You are a memory assistant for an AI voice assistant named "Computer". Your job is to maintain a short, compressed memory of conversations between Computer and Tristan.

Read the previous memory, the most recent user question, and Computer's response. Then create a new, updated memory that:
1. Is extremely concise (maximum 300 words)
2. Prioritizes important facts, preferences, and context
3. Removes redundant or low-value information
4. Maintains temporal order of key events
5. Formats in simple paragraph form
6. Always includes the exact last query and response at the end for perfect context

Previous memory: {previous_memory}

Recent interaction:
User: {user_question}
Computer: {assistant_response}

Provide ONLY the new compressed memory paragraph with no additional text or explanation. Always end the memory with the exact last exchange:
'''

def summarize_memory(memory, last_user_prompt, last_ai_answer):
    """
    Summarize the conversation memory using OpenAI API, keeping it concise and under 300 words.
    Args:
        memory (dict): The current memory/context dict (should contain 'summary' key).
        last_user_prompt (str): The latest user prompt.
        last_ai_answer (str): The latest AI response.
    Returns:
        dict: The summarized memory as a JSON object with a single key 'summary'.
    """
    prev_summary = memory.get('summary', '') if isinstance(memory, dict) else str(memory)
    formatted_prompt = memory_prompt.format(
        previous_memory=prev_summary,
        user_question=last_user_prompt,
        assistant_response=last_ai_answer
    )
    messages = [
        {"role": "system", "content": formatted_prompt}
    ]
    payload = {
        "model": "gpt-4.1",
        "messages": messages
    }
    response = chatgpt_text_to_text(**payload)
    if response and 'choices' in response and response['choices']:
        summary = response['choices'][0]['message']['content'].strip()
        return {
            "summary": summary
        }
    return {
        "summary": ""
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python memory.py <memory> <last_user_prompt> <last_ai_answer>")
        exit(1)
    memory = sys.argv[1]
    last_user_prompt = sys.argv[2]
    last_ai_answer = sys.argv[3]
    summary = summarize_memory(memory, last_user_prompt, last_ai_answer)
    if summary:
        print("--- Summarized Memory ---\n")
        print(summary)
    else:
        print("Failed to summarize memory.")
