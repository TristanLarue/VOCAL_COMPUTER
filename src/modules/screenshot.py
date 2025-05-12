import os
import time
from datetime import datetime
from mss import mss
from utils import log, Colors
import numpy as np
from PIL import Image

# Define the temporary directory for screenshots
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")

def ensure_screenshot_dir():
    """Ensure the screenshots directory exists"""
    if not os.path.exists(SCREENSHOT_DIR):
        try:
            os.makedirs(SCREENSHOT_DIR)
            log(f"Created screenshot directory: {SCREENSHOT_DIR}", "INFO")
        except Exception as e:
            log(f"Error creating screenshot directory: {e}", "ERROR")
            return False
    return True

def list_monitors():
    """List all available monitors with details"""
    with mss() as sct:
        for i, monitor in enumerate(sct.monitors[1:], 1):  # Skip the "all monitors" entry
            log(f"Monitor {i}: {monitor['width']}x{monitor['height']} at position ({monitor['left']}, {monitor['top']})", "INFO")
        return len(sct.monitors) - 1  # Return the number of monitors (minus the "all monitors" entry)

def capture_screen(monitor_number=1, filename=None):
    """
    Capture a screenshot of the specified monitor
    
    Args:
        monitor_number (int): The monitor number (1-based index)
        filename (str, optional): Custom filename, if None generates a timestamp-based name
        
    Returns:
        str: Path to the saved screenshot or None if failed
    """
    # Make sure the screenshot directory exists
    if not ensure_screenshot_dir():
        return None
        
    try:
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = "latest_screenshot.png"
            #filename = f"screenshot_{monitor_number}_{timestamp}.png"
        
        # Create full path
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        
        with mss() as sct:
            # Check if the monitor number is valid
            if monitor_number < 1 or monitor_number >= len(sct.monitors):
                log(f"Invalid monitor number {monitor_number}. Valid range: 1-{len(sct.monitors)-1}", "ERROR")
                return None
                
            # Capture the specified monitor (add 1 because index 0 is the "all monitors" entry)
            monitor = sct.monitors[monitor_number]
            screenshot = sct.grab(monitor)
            
            # Save to file
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            img.save(filepath)
            
            log(f"Screenshot saved to {filepath}", "SUCCESS")
            return filepath
            
    except Exception as e:
        log(f"Screenshot error: {e}", "ERROR")
        return None
        
def capture_all_screens(filename=None):
    """
    Capture a screenshot of all monitors combined
    
    Args:
        filename (str, optional): Custom filename, if None generates a timestamp-based name
        
    Returns:
        str: Path to the saved screenshot or None if failed
    """
    # Make sure the screenshot directory exists
    if not ensure_screenshot_dir():
        return None
        
    try:
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_all_{timestamp}.png"
        
        # Create full path
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        
        with mss() as sct:
            # Capture all monitors (index 0 is the "all monitors" entry)
            screenshot = sct.grab(sct.monitors[0])
            
            # Save to file
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            img.save(filepath)
            
            log(f"Screenshot of all monitors saved to {filepath}", "SUCCESS")
            return filepath
            
    except Exception as e:
        log(f"Screenshot error: {e}", "ERROR")
        return None

# Test the functionality if run directly
if __name__ == "__main__":
    print("Testing screenshot module...")
    num_monitors = list_monitors()
    print(f"Found {num_monitors} monitors")
    
    # Take a screenshot of the primary monitor
    primary_path = capture_screen(1)
    secondary_path = capture_screen(2)
    # Take a screenshot of all monitors
    all_path = capture_all_screens()
    
    print(f"Screenshots saved to: {primary_path}/n{secondary_path}{all_path}")