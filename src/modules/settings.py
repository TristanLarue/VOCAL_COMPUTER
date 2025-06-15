import json
import os
from utils import log

SETTINGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/settings.json'))

def run(key=None, value=None, **kwargs):
    """
    Modifies an existing setting in settings.json. Only existing settings can be changed; new settings cannot be added.
    Args:
        key (str): The setting key to modify.
        value (str|int|bool): The new value for the setting.
    """
    if key is None or value is None:
        log("/settings command called without both 'key' and 'value' arguments. No changes made.", "ERROR")
        return
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        if key not in settings:
            log(f"/settings command attempted to modify unknown setting '{key}'. No changes made.", "ERROR")
            return
        # Try to convert value to int or bool if possible
        if isinstance(value, str):
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                try:
                    value = int(value)
                except ValueError:
                    pass
        settings[key] = value
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        log(f"/settings command: Setting '{key}' updated to '{value}'.", "SYSTEM")
    except Exception as e:
        log(f"/settings command error updating setting '{key}': {e}", "ERROR")
