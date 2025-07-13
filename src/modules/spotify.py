import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from utils import log

# Set these as environment variables or replace with your credentials
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

def get_active_device_id():
    """Return the first active device id, or None if no device is active."""
    try:
        devices = sp.devices()
        for device in devices.get('devices', []):
            if device.get('is_active') or device.get('type') in ("Computer", "Smartphone", "Speaker"):
                return device['id']
        if devices.get('devices'):
            # Return the first available device if none are active
            return devices['devices'][0]['id']
    except Exception as e:
        log(f"Error fetching devices: {e}", "ERROR", script="spotify.py")
    return None

def run(action=None, search=None, volume=None, device=None, **kwargs):
    """
    Simple Spotify control with minimal arguments.
    action: play, pause, resume, next, back, volume
    search: song/artist search term (only for play action)
    volume: int (0-100, only for volume action)
    device: string (computer|phone - optional)
    """
    try:
        if not action:
            log("No action specified. Use: play, pause, resume, next, back, volume", "ERROR", script="spotify.py")
            return

        # Get device ID based on device argument
        device_id = None
        if device == "computer":
            device_id = os.getenv("SPOTIPY_COMPUTER_ID")
            if not device_id:
                log("SPOTIPY_COMPUTER_ID not set in environment", "ERROR", script="spotify.py")
                return
        elif device == "phone":
            device_id = os.getenv("SPOTIPY_PHONE_ID")
            if not device_id:
                log("SPOTIPY_PHONE_ID not set in environment", "ERROR", script="spotify.py")
                return
        else:
            # Auto-detect active device if no specific device requested
            device_id = get_active_device_id()
            if not device_id:
                log("No active Spotify device found. Please open Spotify on any device.", "ERROR", script="spotify.py")
                return

        if action == "play":
            if search:
                try:
                    # Simple search for track or artist
                    results = sp.search(q=search, type="track", limit=1)
                    if results['tracks']['items']:
                        track_uri = results['tracks']['items'][0]['uri']
                        track_name = results['tracks']['items'][0]['name']
                        artist_name = results['tracks']['items'][0]['artists'][0]['name']
                        sp.start_playback(device_id=device_id, uris=[track_uri])
                    else:
                        log(f"No tracks found for: {search}", "ERROR", script="spotify.py")
                except Exception as e:
                    log(f"Error searching for track '{search}': {e}", "ERROR", script="spotify.py")
            else:
                try:
                    # Resume current playback
                    sp.start_playback(device_id=device_id)
                except Exception as e:
                    log(f"Error resuming playback: {e}", "ERROR", script="spotify.py")

        elif action == "pause":
            try:
                sp.pause_playback(device_id=device_id)
            except Exception as e:
                log(f"Error pausing playback: {e}", "ERROR", script="spotify.py")

        elif action == "resume":
            try:
                sp.start_playback(device_id=device_id)
            except Exception as e:
                log(f"Error resuming playback: {e}", "ERROR", script="spotify.py")

        elif action == "next":
            try:
                sp.next_track(device_id=device_id)
            except Exception as e:
                log(f"Error skipping to next track: {e}", "ERROR", script="spotify.py")

        elif action == "back":
            try:
                sp.previous_track(device_id=device_id)
            except Exception as e:
                log(f"Error going to previous track: {e}", "ERROR", script="spotify.py")

        elif action == "volume":
            if volume is None:
                log("Volume level required (0-100)", "ERROR", script="spotify.py")
                return
            try:
                volume_int = int(volume)
                if 0 <= volume_int <= 100:
                    sp.volume(volume_int, device_id=device_id)
                else:
                    log("Volume must be between 0 and 100", "ERROR", script="spotify.py")
            except (ValueError, TypeError):
                log("Volume must be a valid number between 0 and 100", "ERROR", script="spotify.py")
            except Exception as e:
                log(f"Error setting volume to {volume}: {e}", "ERROR", script="spotify.py")

        else:
            log(f"Invalid action: {action}. Use: play, pause, resume, next, back, volume", "ERROR", script="spotify.py")

    except Exception as e:
        log(f"Spotify module error: {e}", "ERROR", script="spotify.py")
