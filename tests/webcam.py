#!/usr/bin/env python3
"""
Capture an image from the webcam and send it to ChatGPT for description
using a vision-capable ChatCompletion endpoint.

Requirements:
    - api_keys.py in the same folder with your OpenAI key as `openai_key`
    - Install dependencies: pip install openai opencv-python

Usage:
    python describe_image_chat.py
"""
import base64
from mimetypes import guess_type
from api_keys import openai_key
import openai
import cv2
import os

openai.api_key = openai_key

def capture_image(image_path: str = "capture.jpg") -> str:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Failed to capture image from webcam.")
    cv2.imwrite(image_path, frame)
    return image_path

def describe_image(image_path: str) -> str:
    mime_type, _ = guess_type(image_path)
    if not mime_type:
        mime_type = "application/octet-stream"
    with open(image_path, "rb") as img_file:
        b64 = base64.b64encode(img_file.read()).decode()
    data_uri = f"data:{mime_type};base64,{b64}"
    message = [
        {"type": "text", "text": "Please describe what is shown in this image."},
        {"type": "image_url", "image_url": {"url": data_uri}}
    ]
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message}]
    )
    return resp.choices[0].message.content.strip()

def main():
    print("Capturing image from webcam…")
    path = capture_image()
    print(f"Saved to {path}")
    print("Sending for description…")
    desc = describe_image(path)
    print("\n--- Image Description ---\n")
    print(desc)
    print("\n-------------------------\n")
    try:
        os.remove(path)
    except OSError:
        pass

if __name__ == "__main__":
    main()
