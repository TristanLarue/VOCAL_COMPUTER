def run(param, audio_stream=None):
    responses = {
        "weather": f"Weather information for {param}: Currently sunny with a temperature of 72°F.",
        "calendar": f"Calendar: {param}. You have 3 events scheduled for today.",
        "timer": f"Timer set for {param} minutes.",
        "alarm": f"Alarm set for {param}.",
        "music": f"Playing music: {param}.",
        "search": f"Web search results for '{param}' found.",
        "reminder": f"Reminder added: {param}.",
        "news": f"Latest news on {param}: Three new developments reported today."
    }
    # The command name is expected to be set as the module name
    import sys
    cmd = __name__.split('.')[-1]
    return responses.get(cmd, f"Command {cmd} executed with parameter {param}")
