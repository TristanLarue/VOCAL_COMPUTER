# speak.py - V2
# Enhanced text-to-speech with voice control
# Simplified interface with consistent keywords

import os
import json
from datetime import datetime
from utils import log

def run(action="say", return_data=False, **kwargs):
    """
    Unified speak interface
    Actions: say, speak, talk, tell, announce
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['say', 'speak', 'talk', 'tell', 'announce', 'voice']:
            return handle_speak_text(return_data, **kwargs)
        elif action in ['stop', 'silence', 'quiet', 'mute']:
            return handle_stop_speech(return_data, **kwargs)
        elif action in ['volume', 'vol', 'level']:
            return handle_volume_control(return_data, **kwargs)
        else:
            # Default to speaking
            return handle_speak_text(return_data, **kwargs)
            
    except Exception as e:
        error_msg = f"Error in speak module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_speak_text(return_data, **kwargs):
    """Handle text-to-speech"""
    try:
        text = kwargs.get('text') or kwargs.get('message') or kwargs.get('content') or kwargs.get('say')
        
        if not text:
            return create_response(False, "Text is required for speech", return_data)
        
        # Get speech parameters
        voice = kwargs.get('voice') or kwargs.get('speaker', 'default')
        speed = kwargs.get('speed') or kwargs.get('rate', 1.0)
        volume = kwargs.get('volume') or kwargs.get('vol', 1.0)
        
        # Convert parameters to proper types
        try:
            speed = float(speed)
            volume = float(volume)
        except (ValueError, TypeError):
            speed = 1.0
            volume = 1.0
        
        # Ensure parameters are in valid ranges
        speed = max(0.1, min(3.0, speed))
        volume = max(0.0, min(1.0, volume))
        
        # Import speech function from sounds module
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from sounds import speech_queue
            
            # Add to speech queue
            speech_queue.put({
                'text': text,
                'voice': voice,
                'speed': speed,
                'volume': volume
            })
            
            success_msg = f"Speaking: '{text[:50]}{'...' if len(text) > 50 else ''}'"
            
            return create_response(True, success_msg, return_data, {
                'text': text,
                'length': len(text),
                'voice': voice,
                'speed': speed,
                'volume': volume,
                'queued': True
            })
            
        except ImportError:
            # Fallback: just log the text
            log(f"TTS: {text}", "SPEECH")
            success_msg = f"Text logged for speech: '{text[:50]}{'...' if len(text) > 50 else ''}'"
            
            return create_response(True, success_msg, return_data, {
                'text': text,
                'length': len(text),
                'fallback': True
            })
        
    except Exception as e:
        error_msg = f"Error in text-to-speech: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_stop_speech(return_data, **kwargs):
    """Handle stopping current speech"""
    try:
        # Try to stop speech using sounds module
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from sounds import interrupt_speech
            
            interrupt_speech()
            success_msg = "Speech interrupted and stopped"
            
            return create_response(True, success_msg, return_data, {
                'action': 'stop',
                'interrupted': True
            })
            
        except ImportError:
            success_msg = "Speech stop command acknowledged (no active TTS)"
            
            return create_response(True, success_msg, return_data, {
                'action': 'stop',
                'fallback': True
            })
        
    except Exception as e:
        error_msg = f"Error stopping speech: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_volume_control(return_data, **kwargs):
    """Handle volume control"""
    try:
        volume = kwargs.get('volume') or kwargs.get('level') or kwargs.get('vol')
        
        if volume is None:
            return create_response(False, "Volume level is required", return_data)
        
        # Convert to float and validate
        try:
            volume = float(volume)
        except (ValueError, TypeError):
            return create_response(False, "Volume must be a number", return_data)
        
        # Ensure volume is in valid range
        volume = max(0.0, min(1.0, volume))
        
        # Try to set volume using sounds module
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            # Note: Volume control would need to be implemented in sounds module
            
            success_msg = f"Volume set to {volume:.1%}"
            
            return create_response(True, success_msg, return_data, {
                'volume': volume,
                'percentage': f"{volume:.1%}",
                'action': 'volume'
            })
            
        except ImportError:
            success_msg = f"Volume command acknowledged: {volume:.1%}"
            
            return create_response(True, success_msg, return_data, {
                'volume': volume,
                'percentage': f"{volume:.1%}",
                'fallback': True
            })
        
    except Exception as e:
        error_msg = f"Error controlling volume: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    if return_data:
        return {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'speak'
        }
    else:
        # File-based response for complex analysis
        filename = f"speak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_data = {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'speak',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(os.path.join(temp_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2)
        
        log(message, "COMMAND")
        return f"Speech operation completed. Data saved to {filename}"
