# todo.py
# Simple TODO list management for tracking AI capabilities and features to implement
# Just adds text to a TODO.txt file in the project root

import os
from datetime import datetime
from utils import log

def run(text=None, **kwargs):
    """Add a TODO item to the list"""
    try:
        # Get text from various possible parameter names
        todo_text = text or kwargs.get('item') or kwargs.get('todo')
        
        if not todo_text:
            return "TODO text is required."
        
        # Get TODO.txt file path (in assets folder)
        todo_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/TODO.txt'))
        
        # Add timestamp and format the item
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        formatted_item = f"[{timestamp}] {todo_text.strip()}"
        
        # Append to TODO.txt file
        with open(todo_file, 'a', encoding='utf-8') as f:
            f.write(formatted_item + '\n')
        
        success_msg = f"Added to TODO: {todo_text}"
        log(success_msg, "COMMAND")
        return success_msg
        
    except Exception as e:
        error_msg = f"Error adding TODO item: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg
