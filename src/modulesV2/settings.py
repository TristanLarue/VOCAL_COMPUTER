# settings.py - V2
# Enhanced settings management with get/set capabilities
# Simplified interface with consistent keywords

import os
import json
from datetime import datetime
from utils import log, get_settings

def run(action="get", return_data=False, **kwargs):
    """
    Unified settings interface
    Actions: get, set, list, reset, update
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['get', 'read', 'show', 'view']:
            return handle_get_setting(return_data, **kwargs)
        elif action in ['set', 'write', 'update', 'change']:
            return handle_set_setting(return_data, **kwargs)
        elif action in ['list', 'all', 'show_all', 'dump']:
            return handle_list_settings(return_data, **kwargs)
        elif action in ['reset', 'clear', 'default']:
            return handle_reset_settings(return_data, **kwargs)
        else:
            error_msg = f"Unknown action: {action}. Use: get, set, list, reset"
            return create_response(False, error_msg, return_data)
            
    except Exception as e:
        error_msg = f"Error in settings module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_get_setting(return_data, **kwargs):
    """Handle getting a specific setting"""
    try:
        key = kwargs.get('key') or kwargs.get('setting') or kwargs.get('name')
        
        if not key:
            return create_response(False, "Setting key is required", return_data)
        
        # Load current settings
        settings = get_settings()
        
        if key not in settings:
            return create_response(False, f"Setting '{key}' not found", return_data)
        
        value = settings[key]
        success_msg = f"Retrieved setting '{key}': {value}"
        
        return create_response(True, success_msg, return_data, {
            'key': key,
            'value': value,
            'type': type(value).__name__
        })
        
    except Exception as e:
        error_msg = f"Error getting setting: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_set_setting(return_data, **kwargs):
    """Handle setting a specific value"""
    try:
        key = kwargs.get('key') or kwargs.get('setting') or kwargs.get('name')
        value = kwargs.get('value') or kwargs.get('data')
        
        if not key:
            return create_response(False, "Setting key is required", return_data)
        
        if value is None:
            return create_response(False, "Setting value is required", return_data)
        
        # Load current settings
        settings = get_settings()
        
        # Convert value to appropriate type if possible
        if isinstance(value, str):
            # Try to convert string values to appropriate types
            if value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)
        
        # Update setting
        old_value = settings.get(key)
        settings[key] = value
        
        # Save settings
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/settings.json'))
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        
        success_msg = f"Updated setting '{key}': {old_value} → {value}"
        
        return create_response(True, success_msg, return_data, {
            'key': key,
            'old_value': old_value,
            'new_value': value,
            'type': type(value).__name__
        })
        
    except Exception as e:
        error_msg = f"Error setting value: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_list_settings(return_data, **kwargs):
    """Handle listing all settings"""
    try:
        # Load current settings
        settings = get_settings()
        
        # Filter settings if requested
        filter_key = kwargs.get('filter') or kwargs.get('search')
        
        if filter_key:
            filtered_settings = {k: v for k, v in settings.items() if filter_key.lower() in k.lower()}
            settings_to_show = filtered_settings
            success_msg = f"Found {len(filtered_settings)} settings matching '{filter_key}'"
        else:
            settings_to_show = settings
            success_msg = f"Retrieved {len(settings)} settings"
        
        return create_response(True, success_msg, return_data, {
            'settings': settings_to_show,
            'count': len(settings_to_show),
            'filter': filter_key
        })
        
    except Exception as e:
        error_msg = f"Error listing settings: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_reset_settings(return_data, **kwargs):
    """Handle resetting settings to defaults"""
    try:
        # Define default settings
        default_settings = {
            "permanent-memory": False,
            "voice-enabled": True,
            "tts-enabled": True,
            "wake-word": "computer",
            "volume": 0.8,
            "log-level": "INFO"
        }
        
        # Confirm reset if not forced
        force = kwargs.get('force', False) or kwargs.get('confirm', False)
        
        if not force:
            return create_response(False, "Reset requires confirmation. Use force=true", return_data)
        
        # Reset to defaults
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/settings.json'))
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=2)
        
        success_msg = f"Settings reset to defaults ({len(default_settings)} settings)"
        
        return create_response(True, success_msg, return_data, {
            'reset_settings': default_settings,
            'count': len(default_settings)
        })
        
    except Exception as e:
        error_msg = f"Error resetting settings: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    if return_data:
        return {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'settings'
        }
    else:
        # File-based response for complex analysis
        filename = f"settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_data = {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'settings',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(os.path.join(temp_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2)
        
        log(message, "COMMAND")
        return f"Settings operation completed. Data saved to {filename}"
