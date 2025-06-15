import os
import json
from API import send_openai_request

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
    base_prompt = (
        "You are a memory assistant. Your job is to update the ongoing conversation summary "
        "by combining the previous summary with the new user prompt and AI response. "
        "Remove unnecessary details, keep only the most relevant facts, context, and decisions. "
        "The summary must be under 300 words. Do not include filler, greetings, or repeated information. "
        "Be concise and clear. If there is no conversation to summarize, do not mention this fact—just say nothing and wait for content to summarize."
    )
    prev_summary = memory.get('summary', '') if isinstance(memory, dict) else str(memory)
    messages = [
        {"role": "system", "content": base_prompt},
        {"role": "user", "content": f"Previous summary:\n{prev_summary}\n\nNew user prompt:\n{last_user_prompt}\n\nNew AI response:\n{last_ai_answer}"}
    ]
    payload = {
        "model": "gpt-4o",
        "messages": messages
    }
    response = send_openai_request('chat/completions', payload)
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
