import importlib
import json
import os
import sys
import asyncio
from utils import log, log_command_execution

def load_commands():
    with open(os.path.join(os.path.dirname(__file__), '../assets/commands.json'), 'r', encoding='utf-8') as f:
        return {cmd['name']: cmd for cmd in json.load(f)['commands']}

COMMANDS = load_commands()
MODULE_CACHE = {}

# Ensure the modules directory is in sys.path for dynamic import
MODULES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
if MODULES_PATH not in sys.path:
    sys.path.insert(0, MODULES_PATH)

def execute_commands_from_json_response(response_text):
    """Parse and execute commands from JSON response format"""
    try:
        # Try to parse the response as JSON
        commands_list = json.loads(response_text.strip())
        
        if not isinstance(commands_list, list):
            log("Response is not a JSON array. Falling back to legacy parsing", "ERROR", script="commands.py")
            return execute_commands_from_response_block(response_text)
        
        for command_obj in commands_list:
            if not isinstance(command_obj, dict):
                log(f"Invalid command object: {command_obj}", "ERROR", script="commands.py")
                continue
                
            module_name = command_obj.get('module')
            args = command_obj.get('args', {})
            
            if not module_name:
                log(f"Missing module name in command: {command_obj}", "ERROR", script="commands.py")
                continue
                
            if module_name not in COMMANDS:
                log(f"Unknown module: {module_name}", "ERROR", script="commands.py")
                continue
            
            try:
                execute_single_command(module_name, args)
            except Exception as e:
                log(f"Error executing command {module_name}: {e}", "ERROR", script="commands.py")
                
    except json.JSONDecodeError as e:
        log(f"Failed to parse JSON response, falling back to legacy format: {e}", "ERROR", script="commands.py")
        return execute_commands_from_response_block(response_text)
    except Exception as e:
        log(f"Error processing JSON commands: {e}", "ERROR", script="commands.py")

def execute_single_command(module_name, args):
    """Execute a single command with given module name and arguments"""
    try:
        module_file = COMMANDS[module_name]['module']
        module_key = module_file[:-3]  # Remove .py
        
        # Log command execution
        log_command_execution(module_name, args)
        
        if module_key not in MODULE_CACHE:
            MODULE_CACHE[module_key] = importlib.import_module(module_key)
        
        module = MODULE_CACHE[module_key]
        
        if hasattr(module, 'run'):
            module.run(**args)
        else:
            log(f"Command module '{module_key}' does not have a 'run' function", "ERROR", script="commands.py")
            
    except Exception as e:
        log(f"Error executing single command {module_name}: {e}", "ERROR", script="commands.py")

async def execute_commands_from_json_response_async(response_text):
    """Async version of JSON command execution"""
    try:
        commands_list = json.loads(response_text.strip())
        
        if not isinstance(commands_list, list):
            log("Response is not a JSON array. Falling back to legacy parsing", "ERROR", script="commands.py")
            return await execute_commands_from_response_block_async(response_text)
        
        for command_obj in commands_list:
            if not isinstance(command_obj, dict):
                log(f"Invalid command object: {command_obj}", "ERROR", script="commands.py")
                continue
                
            module_name = command_obj.get('module')
            args = command_obj.get('args', {})
            
            if not module_name:
                log(f"Missing module name in command: {command_obj}", "ERROR", script="commands.py")
                continue
                
            if module_name not in COMMANDS:
                log(f"Unknown module: {module_name}", "ERROR", script="commands.py")
                continue
            
            try:
                await execute_single_command_async(module_name, args)
            except Exception as e:
                log(f"Error executing async command {module_name}: {e}", "ERROR", script="commands.py")
                
    except json.JSONDecodeError as e:
        log(f"Failed to parse JSON response, falling back to legacy format: {e}", "ERROR", script="commands.py")
        return await execute_commands_from_response_block_async(response_text)
    except Exception as e:
        log(f"Error processing JSON commands: {e}", "ERROR", script="commands.py")

async def execute_single_command_async(module_name, args):
    """Execute a single command asynchronously"""
    try:
        module_file = COMMANDS[module_name]['module']
        module_key = module_file[:-3]  # Remove .py
        
        # Log command execution
        log_command_execution(module_name, args)
        
        if module_key not in MODULE_CACHE:
            MODULE_CACHE[module_key] = importlib.import_module(module_key)
        
        module = MODULE_CACHE[module_key]
        
        if hasattr(module, 'run'):
            if asyncio.iscoroutinefunction(getattr(module, 'run', None)):
                await module.run(**args)
            else:
                await asyncio.to_thread(module.run, **args)
        else:
            log(f"Command module '{module_key}' does not have a 'run' function.", "ERROR")
            
    except Exception as e:
        log(f"Error executing async single command {module_name}: {e}", "ERROR")

# Legacy functions for backward compatibility
def execute_commands_from_response(line):
    print(f"Processing command line: {line}")
    line = line.strip()
    if not line or not line.startswith('/'):
        return
    try:
        cmd_name, params = parse_command(line)
        if cmd_name not in COMMANDS:
            log(f"Unknown command received: {cmd_name}", "ERROR")
            return
        execute_single_command(cmd_name, params)
    except Exception as e:
        log(f"Error executing command from line '{line}': {e}", "ERROR")

def execute_commands_from_response_block(response_block):
    """Splits a multi-line response and processes each line as a command or thought."""
    for line in response_block.split('\n'):
        execute_commands_from_response(line)

async def execute_commands_from_response_block_async(response_block):
    for line in response_block.split('\n'):
        await execute_command_line_async(line)

async def execute_command_line_async(line):
    line = line.strip()
    if not line or not line.startswith('/'):
        return
    try:
        cmd_name, params = parse_command(line)
        if cmd_name not in COMMANDS:
            log(f"Unknown command: {cmd_name}", "ERROR")
            return
        await execute_single_command_async(cmd_name, params)
    except Exception as e:
        log(f"Error executing command from line '{line}': {e}", "ERROR")

async def execute_commands_from_response_block_sync(response_block):
    for line in response_block.split('\n'):
        await execute_command_line_sync(line)

async def execute_command_line_sync(line):
    line = line.strip()
    if not line or not line.startswith('/'):
        return
    try:
        cmd_name, params = parse_command(line)
        if cmd_name not in COMMANDS:
            log(f"Unknown command: {cmd_name}", "ERROR")
            return
        await execute_single_command_async(cmd_name, params)
    except Exception as e:
        log(f"Error executing command from line '{line}': {e}", "ERROR")

def parse_command(line):
    import re
    # Accept /moduleName(key1={value1},key2={value2})
    match_with_param = re.match(r"/(\w+)\((.*)\)", line)
    if match_with_param:
        cmd_name = match_with_param.group(1)
        params_str = match_with_param.group(2)
        params = {}
        # Find all key={value} pairs
        for param_match in re.finditer(r"(\w+)=\{([^{}]*)\}", params_str):
            key = param_match.group(1)
            value = param_match.group(2)
            # Type detection: try int, then float, else string
            value_strip = value.strip()
            # Try int
            try:
                value_cast = int(value_strip)
            except ValueError:
                # Try float
                try:
                    value_cast = float(value_strip)
                except ValueError:
                    value_cast = value_strip
            params[key] = value_cast
        return cmd_name, params
    match_no_param = re.match(r"/(\w+)\(\)", line)
    if match_no_param:
        cmd_name = match_no_param.group(1)
        return cmd_name, {}
    raise ValueError(f"Invalid command format: {line}")
