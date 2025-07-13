# exit.py - V2
# Session termination with cleanup
# Simplified interface with consistent keywords

import os
import json
from datetime import datetime
from utils import log

def run(action="quit", return_data=False, **kwargs):
    """
    Strict exit interface - single keyword only
    Actions: quit
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Only accept 'quit' as valid action
        if action == 'quit':
            return handle_exit(return_data, **kwargs)
        else:
            error_msg = f"Unknown action: {action}. Use: quit"
            return create_response(False, error_msg, return_data)
            
    except Exception as e:
        error_msg = f"Error in exit module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_exit(return_data, **kwargs):
    """Handle session termination - message is optional"""
    try:
        # Get optional message
        message = kwargs.get('message')
        
        if message:
            success_msg = f"Session terminated: {message}"
        else:
            success_msg = "Session terminated"
        
        # Create response before triggering exit
        response_data = {
            'reason': message or "User requested exit",
            'timestamp': datetime.now().isoformat(),
            'session_ended': True
        }
        
        # Log the exit
        log("Session exit requested by user", "SYSTEM")
        
        return create_response(True, success_msg, return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error during exit: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'module': 'exit'
    }
    
    if data:
        response.update(data)
    
    if return_data:
        return response
    else:
        # Save to file
        filename = f"exit_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            
        log(f"Exit data saved to {filename}", "INFO")
        
    except Exception as e:
        log(f"Error saving to temp: {e}", "ERROR")
        return f"Exit operation completed. Data saved to {filename}"
