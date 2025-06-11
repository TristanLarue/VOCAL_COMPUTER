import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from API import send_openai_request

if __name__ == "__main__":
    prompt = "Say hello in a creative way."
    response = send_openai_request(prompt)
    print(response)
