import openai
import os
from dotenv import load_dotenv

from utils import log, Colors

# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Global memory storage
conversation_memory = "No prior conversation context."

# Memory system prompt
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

def update_memory(user_question, assistant_response):
    """Update the conversation memory with new dialogue"""
    global conversation_memory
    
    try:
        memory_req = memory_prompt.format(
            previous_memory=conversation_memory,
            user_question=user_question,
            assistant_response=assistant_response
        )
        
        mem_resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": memory_req}]
        )
        
        conversation_memory = mem_resp.choices[0].message.content.strip()
        log("Memory updated successfully", "INFO")
        
    except Exception as e:
        log(f"Memory update error: {e}", "ERROR")

def get_memory():
    """Return the current conversation memory"""
    return conversation_memory

def reset_memory():
    """Reset the conversation memory to initial state"""
    global conversation_memory
    conversation_memory = "No prior conversation context."
    log("Memory has been reset", "INFO")