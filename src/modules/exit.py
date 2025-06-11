def run(**kwargs):
    """Entry point for the exit command. Forces the assistant to return to sleep mode (wake-word detection)."""
    from triggers import force_sleep_mode
    force_sleep_mode()