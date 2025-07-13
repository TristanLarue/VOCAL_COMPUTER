# screenshot.py - V2
# Enhanced screenshot capture with multiple monitor support
# Simplified interface with consistent keywords

import os
import json
import time
from datetime import datetime
from PIL import ImageGrab
from utils import log

def run(action="capture", return_data=False, **kwargs):
    """
    Unified screenshot interface
    Actions: capture, take, screen, snap, grab
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['capture', 'take', 'screen', 'snap', 'grab', 'shot']:
            return handle_capture_screenshot(return_data, **kwargs)
        else:
            # Default to capture
            return handle_capture_screenshot(return_data, **kwargs)
            
    except Exception as e:
        error_msg = f"Error in screenshot module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_capture_screenshot(return_data, **kwargs):
    """Handle screenshot capture"""
    try:
        # Get parameters
        monitor_id = kwargs.get('monitor') or kwargs.get('monitor_id') or kwargs.get('display', 0)
        filename = kwargs.get('filename') or kwargs.get('name') or f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        # Ensure filename has .png extension
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        # Set up temp directory
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        filepath = os.path.join(temp_dir, filename)
        
        # Capture screenshot
        try:
            # Get all monitors
            monitors = get_monitor_info()
            
            if isinstance(monitor_id, str) and monitor_id.isdigit():
                monitor_id = int(monitor_id)
            elif not isinstance(monitor_id, int):
                monitor_id = 0
            
            # Capture based on monitor
            if monitor_id == 0 or len(monitors) <= monitor_id:
                # Capture all screens
                screenshot = ImageGrab.grab()
            else:
                # Capture specific monitor (if available)
                monitor = monitors[monitor_id] if monitor_id < len(monitors) else monitors[0]
                screenshot = ImageGrab.grab(bbox=monitor['bbox'])
            
            # Save screenshot
            screenshot.save(filepath, 'PNG')
            
            # Get image info
            width, height = screenshot.size
            file_size = os.path.getsize(filepath)
            
            success_msg = f"Screenshot captured: {filename} ({width}x{height})"
            return create_response(True, success_msg, return_data, {
                'filename': filename,
                'filepath': filepath,
                'width': width,
                'height': height,
                'file_size': file_size,
                'monitor_id': monitor_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error capturing screenshot: {str(e)}"
            log(error_msg, "ERROR")
            return create_response(False, error_msg, return_data)
        
    except Exception as e:
        error_msg = f"Error in screenshot capture: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def get_monitor_info():
    """Get information about available monitors"""
    try:
        # Try to get monitor info using tkinter
        try:
            import tkinter as tk
            root = tk.Tk()
            monitors = []
            
            # Get primary monitor
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            
            monitors.append({
                'id': 0,
                'width': screen_width,
                'height': screen_height,
                'bbox': (0, 0, screen_width, screen_height),
                'primary': True
            })
            
            root.destroy()
            return monitors
            
        except Exception:
            # Fallback: assume single monitor
            return [{
                'id': 0,
                'width': 1920,
                'height': 1080,
                'bbox': (0, 0, 1920, 1080),
                'primary': True
            }]
            
    except Exception as e:
        log(f"Error getting monitor info: {str(e)}", "ERROR")
        return [{
            'id': 0,
            'width': 1920,
            'height': 1080,
            'bbox': (0, 0, 1920, 1080),
            'primary': True
        }]

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    if return_data:
        return {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'screenshot'
        }
    else:
        # File-based response for complex analysis
        result_filename = f"screenshot_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_data = {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'screenshot',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(os.path.join(temp_dir, result_filename), 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2)
        
        log(message, "COMMAND")
        return f"Screenshot operation completed. Data saved to {result_filename}"
