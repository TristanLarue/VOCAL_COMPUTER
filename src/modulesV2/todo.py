# todo.py - V2
# Enhanced TODO management with unified interface
# Simplified interface with consistent keywords

import os
import json
from datetime import datetime
from utils import log

def run(action="add", return_data=False, **kwargs):
    """
    Unified TODO management interface
    Actions: add, create, new, list, show, view, clear, delete, remove
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['add', 'create', 'new', 'insert']:
            return handle_add_todo(return_data, **kwargs)
        elif action in ['list', 'show', 'view', 'get', 'read']:
            return handle_list_todos(return_data, **kwargs)
        elif action in ['clear', 'delete', 'remove', 'empty']:
            return handle_clear_todos(return_data, **kwargs)
        elif action in ['count', 'total', 'number']:
            return handle_count_todos(return_data, **kwargs)
        else:
            # Default to add
            return handle_add_todo(return_data, **kwargs)
            
    except Exception as e:
        error_msg = f"Error in TODO module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_add_todo(return_data, **kwargs):
    """Add a new TODO item"""
    try:
        # Get text from various possible parameter names
        text = kwargs.get('text') or kwargs.get('item') or kwargs.get('todo') or kwargs.get('task') or kwargs.get('note')
        
        if not text:
            return create_response(False, "TODO text is required", return_data)
        
        # Get TODO file path
        todo_file = get_todo_file_path()
        
        # Add timestamp and format the item
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_item = f"[{timestamp}] {text.strip()}"
        
        # Append to TODO file
        with open(todo_file, 'a', encoding='utf-8') as f:
            f.write(formatted_item + '\n')
        
        response_data = {
            "action": "add",
            "success": True,
            "item": text.strip(),
            "timestamp": timestamp,
            "file": todo_file
        }
        
        return create_response(True, f"Added to TODO: {text.strip()}", return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error adding TODO item: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_list_todos(return_data, **kwargs):
    """List all TODO items"""
    try:
        todo_file = get_todo_file_path()
        
        if not os.path.exists(todo_file):
            response_data = {
                "action": "list",
                "success": True,
                "items": [],
                "total": 0,
                "message": "No TODO items found"
            }
            return create_response(True, "No TODO items found", return_data, response_data)
        
        # Read all TODO items
        with open(todo_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse TODO items
        items = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if line:
                # Extract timestamp and text
                if line.startswith('[') and ']' in line:
                    timestamp_end = line.find(']')
                    timestamp = line[1:timestamp_end]
                    text = line[timestamp_end + 1:].strip()
                else:
                    timestamp = "Unknown"
                    text = line
                
                items.append({
                    "line": line_num,
                    "timestamp": timestamp,
                    "text": text,
                    "full_line": line
                })
        
        # Apply filters
        limit = kwargs.get('limit')
        if limit:
            try:
                limit = int(limit)
                items = items[-limit:]  # Get last N items
            except (ValueError, TypeError):
                pass
        
        response_data = {
            "action": "list",
            "success": True,
            "items": items,
            "total": len(items),
            "file": todo_file
        }
        
        return create_response(True, f"Found {len(items)} TODO items", return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error listing TODO items: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_clear_todos(return_data, **kwargs):
    """Clear all TODO items"""
    try:
        todo_file = get_todo_file_path()
        
        # Count existing items before clearing
        existing_count = 0
        if os.path.exists(todo_file):
            with open(todo_file, 'r', encoding='utf-8') as f:
                existing_count = len([line for line in f.readlines() if line.strip()])
        
        # Clear the file
        with open(todo_file, 'w', encoding='utf-8') as f:
            f.write('')
        
        response_data = {
            "action": "clear",
            "success": True,
            "cleared_count": existing_count,
            "file": todo_file
        }
        
        return create_response(True, f"Cleared {existing_count} TODO items", return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error clearing TODO items: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_count_todos(return_data, **kwargs):
    """Count TODO items"""
    try:
        todo_file = get_todo_file_path()
        
        if not os.path.exists(todo_file):
            response_data = {
                "action": "count",
                "success": True,
                "total": 0,
                "file": todo_file
            }
            return create_response(True, "0 TODO items", return_data, response_data)
        
        # Count non-empty lines
        with open(todo_file, 'r', encoding='utf-8') as f:
            count = len([line for line in f.readlines() if line.strip()])
        
        response_data = {
            "action": "count",
            "success": True,
            "total": count,
            "file": todo_file
        }
        
        return create_response(True, f"{count} TODO items", return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error counting TODO items: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def get_todo_file_path():
    """Get the path to the TODO file"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/TODO.txt'))

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "module": "todo"
    }
    
    if data:
        response.update(data)
    
    if return_data:
        return response
    else:
        # Save to file
        filename = f"todo_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            
        log(f"TODO data saved to {filename}", "INFO")
        
    except Exception as e:
        log(f"Error saving to temp: {e}", "ERROR")
