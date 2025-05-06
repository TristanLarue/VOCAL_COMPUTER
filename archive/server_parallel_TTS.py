#!/usr/bin/env python3
"""
Capture an image from the webcam and send it to ChatGPT for description using a vision-capable ChatCompletion endpoint.

Requirements:
    - api_keys.py in the same folder with your OpenAI key as `openai_key`
    - Install dependencies:
        pip install openai opencv-python

Usage:
    python describe_image_chat.py
"""
import base64
from mimetypes import guess_type
from api_keys import openai_key
import openai
import os

# Ensure OpenCV is available
try:
    import cv2
except ImportError:
    raise ImportError("opencv-python not installed. Install with: pip install opencv-python")

# Load your OpenAI API key
openai.api_key = openai_key

def capture_image(image_path: str = "capture.jpg") -> str:
    """
    Capture a single frame from the default webcam and save to disk.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Ensure a webcam is connected and opencv-python is installed.")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Failed to capture image from webcam.")
    cv2.imwrite(image_path, frame)
    return image_path


def describe_image(image_path: str) -> str:
    """
    Encode the image as a base64 data URI and send it to the ChatGPT API to get a description.
    """
    mime_type, _ = guess_type(image_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    with open(image_path, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode()

    data_uri = f"data:{mime_type};base64,{b64_data}"

    message_content = [
        {"type": "text", "text": "Please describe what is shown in this image."},
        {"type": "image_url", "image_url": {"url": data_uri}}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message_content}]
    )
    return response.choices[0].message.content.strip()


def main():
    print("Capturing image from webcam...")
    image_path = capture_image()
    print(f"Image saved to {image_path}")

    print("Sending image for description...")
    description = describe_image(image_path)

    print("\n--- Image Description ---\n")
    print(description)
    print("\n-------------------------\n")

    # Optional: remove the captured file
    try:
        os.remove(image_path)
    except OSError:
        pass

if __name__ == "__main__":
    main()
