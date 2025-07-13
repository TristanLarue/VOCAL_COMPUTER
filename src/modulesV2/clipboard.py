# clipboard.py - V2
# Enhanced clipboard management with read/write capabilities
# Simplified interface with consistent keywords

import pyperclip
import os
import json
from datetime import datetime
from utils import log

def run(action="get", return_data=False, **kwargs):
    """
    Strict clipboard interface - exact keywords only
    Actions: get, set, clear, append
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function - strict keywords only
        if action == 'get':
            return handle_get_clipboard(return_data, **kwargs)
        elif action == 'set':
            return handle_set_clipboard(return_data, **kwargs)
        elif action == 'clear':
            return handle_clear_clipboard(return_data, **kwargs)
        elif action == 'append':
            return handle_append_clipboard(return_data, **kwargs)
        else:
            error_msg = f"Unknown action: {action}. Use: get, set, clear, append"
            return create_response(False, error_msg, return_data)
            
    except Exception as e:
        error_msg = f"Error in clipboard module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_get_clipboard(return_data, **kwargs):
    """Handle clipboard reading - no arguments needed"""
    try:
        # Get clipboard content
        content = pyperclip.paste()
        
        if not content:
            return create_response(True, "Clipboard is empty", return_data, {
                'content': '',
                'length': 0,
                'is_empty': True
            })
        
        return create_response(True, f"Retrieved clipboard content ({len(content)} characters)", return_data, {
            'content': content,
            'length': len(content),
            'is_empty': False
        })
        
    except Exception as e:
        error_msg = f"Error reading clipboard: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_set_clipboard(return_data, **kwargs):
    """Handle clipboard writing - strict single argument"""
    try:
        text = kwargs.get('text')
        
        if text is None:
            return create_response(False, "Text is required", return_data)
        
        # Convert to string if needed
        text = str(text)
        
        # Set clipboard content
        pyperclip.copy(text)
        
        return create_response(True, f"Copied to clipboard ({len(text)} characters)", return_data, {
            'content': text,
            'length': len(text)
        })
        
    except Exception as e:
        error_msg = f"Error writing to clipboard: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_clear_clipboard(return_data, **kwargs):
    """Handle clipboard clearing - no arguments needed"""
    try:
        # Clear clipboard by setting empty string
        pyperclip.copy('')
        
        return create_response(True, "Clipboard cleared", return_data, {
            'content': '',
            'length': 0,
            'is_empty': True
        })
        
    except Exception as e:
        error_msg = f"Error clearing clipboard: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_append_clipboard(return_data, **kwargs):
    """Handle clipboard appending - strict single argument"""
    try:
        text = kwargs.get('text')
        
        if text is None:
            return create_response(False, "Text is required", return_data)
        
        # Get current clipboard content
        current_content = pyperclip.paste()
        
        # Append new text
        new_content = current_content + str(text)
        
        # Set clipboard content
        pyperclip.copy(new_content)
        
        return create_response(True, f"Appended to clipboard ({len(new_content)} characters total)", return_data, {
            'content': new_content,
            'length': len(new_content),
            'appended_text': str(text)
        })
        
    except Exception as e:
        error_msg = f"Error appending to clipboard: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'module': 'clipboard'
    }
    
    if data:
        response.update(data)
    
    if return_data:
        return response
    else:
        # Save to file
        filename = f"clipboard_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_to_temp(response, filename)
        return message

def save_to_temp(data, filename):
    """Save data to temp folder"""
    try:
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        log(f"Clipboard data saved to {filename}", "INFO")
        
    except Exception as e:
        log(f"Error saving to temp: {e}", "ERROR")
        return f"Clipboard operation completed. Data saved to {filename}"
