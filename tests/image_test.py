#!/usr/bin/env python3
"""
Send a local image (default dog.jpg) to the ChatGPT API for description using a vision-capable ChatCompletion endpoint.

Requirements:
    - api_keys.py in the same folder with your OpenAI key as `openai_key`
    - Install OpenAI Python client: `pip install openai`

Usage:
    python describe_image_chat.py            # uses dog.jpg
    python describe_image_chat.py image.jpg  # uses provided image
"""
import sys
import base64
from mimetypes import guess_type
from api_keys import openai_key
import openai

# Load your OpenAI API key
openai.api_key = openai_key

def describe_image(image_path: str) -> str:
    """
    Encode the image as a base64 data URI and send it to the ChatGPT API to get a description.
    """
    # Determine MIME type
    mime_type, _ = guess_type(image_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    # Read and encode the image
    with open(image_path, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode()

    data_uri = f"data:{mime_type};base64,{b64_data}"

    # Construct the message payload
    message_content = [
        {"type": "text",      "text": "Please describe what is shown in this image."},
        {"type": "image_url", "image_url": {"url": data_uri}}
    ]

    # Call the vision-capable ChatCompletion endpoint
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message_content}]
    )

    # Return the model's description
    return response.choices[0].message.content.strip()


def main():
    # Determine image path: default to dog.jpg if none provided
    if len(sys.argv) > 2:
        print("Usage: python describe_image_chat.py [path/to/image.jpg]")
        sys.exit(1)
    image_path = sys.argv[1] if len(sys.argv) == 2 else "dog.jpg"

    description = describe_image(image_path)
    print("\n--- Image Description ---\n")
    print(description)
    print("\n-------------------------\n")

if __name__ == "__main__":
    main()
