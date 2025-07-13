# reprompt.py - V2
# Enhanced AI reprompting with file analysis
# Simplified interface with consistent keywords

import os
import json
from datetime import datetime
from utils import log

def run(action="analyze", return_data=False, **kwargs):
    """
    Unified reprompt interface
    Actions: analyze, process, read, summarize
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['analyze', 'process', 'read', 'summarize', 'review']:
            return handle_analyze_files(return_data, **kwargs)
        else:
            # Default to analyze
            return handle_analyze_files(return_data, **kwargs)
            
    except Exception as e:
        error_msg = f"Error in reprompt module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_analyze_files(return_data, **kwargs):
    """Handle file analysis and processing"""
    try:
        # Get files to analyze
        filenames = kwargs.get('filenames') or kwargs.get('files') or kwargs.get('filename')
        prompt = kwargs.get('prompt') or kwargs.get('question') or kwargs.get('query')
        context = kwargs.get('context') or kwargs.get('background') or ''
        
        if not filenames:
            return create_response(False, "Filenames are required for analysis", return_data)
        
        if not prompt:
            return create_response(False, "Analysis prompt is required", return_data)
        
        # Handle single filename or comma-separated list
        if isinstance(filenames, str):
            file_list = [f.strip() for f in filenames.split(',')]
        else:
            file_list = filenames if isinstance(filenames, list) else [filenames]
        
        # Read and analyze files
        file_contents = {}
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        
        for filename in file_list:
            file_path = os.path.join(temp_dir, filename)
            
            if not os.path.exists(file_path):
                log(f"File not found: {filename}", "WARNING")
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Try to parse as JSON, fall back to text
                try:
                    parsed_content = json.loads(content)
                    file_contents[filename] = {
                        'type': 'json',
                        'content': parsed_content,
                        'size': len(content)
                    }
                except json.JSONDecodeError:
                    file_contents[filename] = {
                        'type': 'text',
                        'content': content,
                        'size': len(content)
                    }
                    
            except Exception as e:
                log(f"Error reading file {filename}: {str(e)}", "ERROR")
                continue
        
        if not file_contents:
            return create_response(False, "No valid files found for analysis", return_data)
        
        # Prepare analysis data
        analysis_data = {
            'prompt': prompt,
            'context': context,
            'files': file_contents,
            'file_count': len(file_contents),
            'total_size': sum(f['size'] for f in file_contents.values())
        }
        
        success_msg = f"Analyzed {len(file_contents)} files for prompt: '{prompt}'"
        return create_response(True, success_msg, return_data, analysis_data)
        
    except Exception as e:
        error_msg = f"Error analyzing files: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    if return_data:
        return {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'reprompt'
        }
    else:
        # File-based response for complex analysis
        filename = f"reprompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_data = {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'reprompt',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(os.path.join(temp_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2)
        
        log(message, "COMMAND")
        return f"Reprompt operation completed. Data saved to {filename}"
