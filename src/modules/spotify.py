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
        log(f"[spotify.py] Error fetching devices: {e}", "ERROR")
    return None

def run(action=None, song_name=None, artist=None, album=None, year=None, genre=None, device=None, volume=None, **kwargs):
    """
    action: play, stop, next, previous, raise_volume, lower_volume, set_volume
    song_name: track title
    artist: artist name
    album: album name
    year: year or range
    genre: genre
    device: 'phone', 'computer', or None (auto)
    volume: int (0-100) for set_volume
    """
    try:
        # Choose device_id based on argument
        if device == "phone":
            device_id = os.getenv("SPOTIPY_PHONE_ID")
            if not device_id:
                log("[spotify.py] SPOTIPY_PHONE_ID not set in environment.", "ERROR")
                return
        elif device == "computer":
            device_id = os.getenv("SPOTIPY_COMPUTER_ID")
            if not device_id:
                log("[spotify.py] SPOTIPY_COMPUTER_ID not set in environment.", "ERROR")
                return
        else:
            device_id = get_active_device_id()
            if not device_id:
                log("[spotify.py] No active Spotify device found. Please open Spotify and play a song on any device.", "ERROR")
                return
        if action == "play":
            # Build search query with all filters
            query_parts = []
            if song_name:
                query_parts.append(f'track:"{song_name}"')
            if artist:
                query_parts.append(f'artist:"{artist}"')
            if album:
                query_parts.append(f'album:"{album}"')
            if year:
                query_parts.append(f'year:{year}')
            if genre:
                query_parts.append(f'genre:"{genre}"')
            query = ' '.join(query_parts)
            if not query:
                log("[spotify.py] At least one of song_name, artist, album, year, or genre must be provided for play.", "ERROR")
                return
            results = sp.search(q=query, type="track", limit=1)
            if results['tracks']['items']:
                track_uri = results['tracks']['items'][0]['uri']
                sp.start_playback(device_id=device_id, uris=[track_uri])
                log(f"[spotify.py] Playing: {query} on device {device or 'auto'}.", "INFO")
            else:
                log(f"[spotify.py] Song not found: {query}", "ERROR")
        elif action == "stop":
            sp.pause_playback(device_id=device_id)
            log(f"[spotify.py] Playback stopped on device {device or 'auto'}.", "INFO")
        elif action == "next":
            sp.next_track(device_id=device_id)
            log(f"[spotify.py] Skipped to next track on device {device or 'auto'}.", "INFO")
        elif action == "previous":
            sp.previous_track(device_id=device_id)
            log(f"[spotify.py] Went to previous track on device {device or 'auto'}.", "INFO")
        elif action == "raise_volume":
            current = sp.current_playback()
            if current and 'device' in current and 'volume_percent' in current['device']:
                new_vol = min(current['device']['volume_percent'] + 10, 100)
                sp.volume(new_vol, device_id=device_id)
                log(f"[spotify.py] Volume raised to {new_vol} on device {device or 'auto'}.", "INFO")
        elif action == "lower_volume":
            current = sp.current_playback()
            if current and 'device' in current and 'volume_percent' in current['device']:
                new_vol = max(current['device']['volume_percent'] - 10, 0)
                sp.volume(new_vol, device_id=device_id)
                log(f"[spotify.py] Volume lowered to {new_vol} on device {device or 'auto'}.", "INFO")
        elif action == "set_volume":
            if volume is not None and 0 <= int(volume) <= 100:
                sp.volume(int(volume), device_id=device_id)
                log(f"[spotify.py] Volume set to {volume} on device {device or 'auto'}.", "INFO")
            else:
                log("[spotify.py] Volume must be an integer between 0 and 100.", "ERROR")
        else:
            log("[spotify.py] Invalid action or missing parameters.", "ERROR")
    except Exception as e:
        log(f"[spotify.py] Spotify API error: {e}", "ERROR")
