import importlib
import json
import os
import sys
import asyncio
from utils import log

def load_commands():
    with open(os.path.join(os.path.dirname(__file__), '../assets/commands.json'), 'r', encoding='utf-8') as f:
        return {cmd['name']: cmd for cmd in json.load(f)['commands']}

COMMANDS = load_commands()
MODULE_CACHE = {}

# Ensure the modules directory is in sys.path for dynamic import
MODULES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
if MODULES_PATH not in sys.path:
    sys.path.insert(0, MODULES_PATH)

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
        module_file = COMMANDS[cmd_name]['module']
        module_name = module_file[:-3]  # Remove .py
        # Fix: If module_name is 'speech', replace with 'speak'
        if module_name not in MODULE_CACHE:
            MODULE_CACHE[module_name] = importlib.import_module(module_name)
        module = MODULE_CACHE[module_name]
        if hasattr(module, 'run'):
            module.run(**params)
        else:
            log(f"Command module '{module_name}' does not have a 'run' function.", "ERROR")
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
        module_file = COMMANDS[cmd_name]['module']
        module_name = module_file[:-3]  # Remove .py
        if module_name not in MODULE_CACHE:
            MODULE_CACHE[module_name] = importlib.import_module(module_name)
        module = MODULE_CACHE[module_name]
        # If the module's run is async, await it; else run in a thread
        if asyncio.iscoroutinefunction(getattr(module, 'run', None)):
            await module.run(**params)
        else:
            await asyncio.to_thread(module.run, **params)
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
        module_file = COMMANDS[cmd_name]['module']
        module_name = module_file[:-3]  # Remove .py
        if module_name not in MODULE_CACHE:
            MODULE_CACHE[module_name] = importlib.import_module(module_name)
        module = MODULE_CACHE[module_name]
        # If the module's run is async, await it; else run in a thread
        if asyncio.iscoroutinefunction(getattr(module, 'run', None)):
            await module.run(**params)
        else:
            await asyncio.to_thread(module.run, **params)
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
