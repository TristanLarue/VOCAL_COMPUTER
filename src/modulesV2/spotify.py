# spotify.py - V2
# Enhanced Spotify control with unified interface
# Simplified interface with consistent keywords

import os
import json
import spotipy
from datetime import datetime
from spotipy.oauth2 import SpotifyOAuth
from utils import log

# Spotify credentials from environment variables
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

def get_spotify_client():
    """Get authenticated Spotify client"""
    try:
        return spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))
    except Exception as e:
        log(f"Error creating Spotify client: {e}", "ERROR")
        return None

def run(action="status", return_data=False, **kwargs):
    """
    Unified Spotify control interface
    Actions: play, pause, resume, next, back, volume, status, search, current
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['play', 'start', 'resume']:
            return handle_play_music(return_data, **kwargs)
        elif action in ['pause', 'stop']:
            return handle_pause_music(return_data, **kwargs)
        elif action in ['next', 'skip', 'forward']:
            return handle_next_track(return_data, **kwargs)
        elif action in ['back', 'previous', 'prev']:
            return handle_previous_track(return_data, **kwargs)
        elif action in ['volume', 'vol', 'level']:
            return handle_volume_control(return_data, **kwargs)
        elif action in ['status', 'current', 'playing', 'now']:
            return handle_get_status(return_data, **kwargs)
        elif action in ['search', 'find', 'lookup']:
            return handle_search_tracks(return_data, **kwargs)
        else:
            # Default to status
            return handle_get_status(return_data, **kwargs)
            
    except Exception as e:
        error_msg = f"Error in Spotify module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_play_music(return_data, **kwargs):
    """Handle music playback"""
    try:
        sp = get_spotify_client()
        if not sp:
            return create_response(False, "Could not authenticate with Spotify", return_data)
        
        # Get device ID
        device_id = get_device_id(sp, kwargs.get('device'))
        if not device_id:
            return create_response(False, "No active Spotify device found", return_data)
        
        # Check if search query provided
        query = kwargs.get('query') or kwargs.get('search') or kwargs.get('song') or kwargs.get('track')
        
        if query:
            # Search and play specific track
            results = sp.search(q=query, type="track", limit=1)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                track_uri = track['uri']
                track_name = track['name']
                artist_name = track['artists'][0]['name']
                
                sp.start_playback(device_id=device_id, uris=[track_uri])
                
                response_data = {
                    "action": "play",
                    "success": True,
                    "track": track_name,
                    "artist": artist_name,
                    "uri": track_uri,
                    "device": device_id
                }
                return create_response(True, f"Playing: {track_name} by {artist_name}", return_data, response_data)
            else:
                return create_response(False, f"No tracks found for: {query}", return_data)
        else:
            # Resume current playback
            sp.start_playback(device_id=device_id)
            response_data = {
                "action": "resume",
                "success": True,
                "device": device_id
            }
            return create_response(True, "Resumed playback", return_data, response_data)
            
    except Exception as e:
        error_msg = f"Error playing music: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_pause_music(return_data, **kwargs):
    """Handle music pause"""
    try:
        sp = get_spotify_client()
        if not sp:
            return create_response(False, "Could not authenticate with Spotify", return_data)
        
        device_id = get_device_id(sp, kwargs.get('device'))
        if not device_id:
            return create_response(False, "No active Spotify device found", return_data)
        
        sp.pause_playback(device_id=device_id)
        
        response_data = {
            "action": "pause",
            "success": True,
            "device": device_id
        }
        return create_response(True, "Paused playback", return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error pausing music: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_next_track(return_data, **kwargs):
    """Handle skip to next track"""
    try:
        sp = get_spotify_client()
        if not sp:
            return create_response(False, "Could not authenticate with Spotify", return_data)
        
        device_id = get_device_id(sp, kwargs.get('device'))
        if not device_id:
            return create_response(False, "No active Spotify device found", return_data)
        
        sp.next_track(device_id=device_id)
        
        response_data = {
            "action": "next",
            "success": True,
            "device": device_id
        }
        return create_response(True, "Skipped to next track", return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error skipping to next track: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_previous_track(return_data, **kwargs):
    """Handle skip to previous track"""
    try:
        sp = get_spotify_client()
        if not sp:
            return create_response(False, "Could not authenticate with Spotify", return_data)
        
        device_id = get_device_id(sp, kwargs.get('device'))
        if not device_id:
            return create_response(False, "No active Spotify device found", return_data)
        
        sp.previous_track(device_id=device_id)
        
        response_data = {
            "action": "previous",
            "success": True,
            "device": device_id
        }
        return create_response(True, "Skipped to previous track", return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error skipping to previous track: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_volume_control(return_data, **kwargs):
    """Handle volume control"""
    try:
        sp = get_spotify_client()
        if not sp:
            return create_response(False, "Could not authenticate with Spotify", return_data)
        
        device_id = get_device_id(sp, kwargs.get('device'))
        if not device_id:
            return create_response(False, "No active Spotify device found", return_data)
        
        volume = kwargs.get('volume') or kwargs.get('level') or kwargs.get('vol')
        if volume is None:
            return create_response(False, "Volume level required (0-100)", return_data)
        
        try:
            volume_int = int(volume)
            if not 0 <= volume_int <= 100:
                return create_response(False, "Volume must be between 0 and 100", return_data)
            
            sp.volume(volume_int, device_id=device_id)
            
            response_data = {
                "action": "volume",
                "success": True,
                "volume": volume_int,
                "device": device_id
            }
            return create_response(True, f"Volume set to {volume_int}%", return_data, response_data)
            
        except (ValueError, TypeError):
            return create_response(False, "Volume must be a valid number between 0 and 100", return_data)
            
    except Exception as e:
        error_msg = f"Error setting volume: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_get_status(return_data, **kwargs):
    """Get current playback status"""
    try:
        sp = get_spotify_client()
        if not sp:
            return create_response(False, "Could not authenticate with Spotify", return_data)
        
        # Get current playback
        current = sp.current_playback()
        
        if not current:
            response_data = {
                "action": "status",
                "is_playing": False,
                "message": "No active playback"
            }
            return create_response(True, "No active playback", return_data, response_data)
        
        track = current.get('item', {})
        response_data = {
            "action": "status",
            "is_playing": current.get('is_playing', False),
            "track": track.get('name', 'Unknown'),
            "artist": track.get('artists', [{}])[0].get('name', 'Unknown'),
            "album": track.get('album', {}).get('name', 'Unknown'),
            "device": current.get('device', {}).get('name', 'Unknown'),
            "volume": current.get('device', {}).get('volume_percent', 0),
            "progress": current.get('progress_ms', 0),
            "duration": track.get('duration_ms', 0),
            "uri": track.get('uri', '')
        }
        
        status_msg = f"Playing: {response_data['track']} by {response_data['artist']}" if response_data['is_playing'] else f"Paused: {response_data['track']} by {response_data['artist']}"
        return create_response(True, status_msg, return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error getting status: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_search_tracks(return_data, **kwargs):
    """Search for tracks"""
    try:
        sp = get_spotify_client()
        if not sp:
            return create_response(False, "Could not authenticate with Spotify", return_data)
        
        query = kwargs.get('query') or kwargs.get('search') or kwargs.get('song') or kwargs.get('track')
        if not query:
            return create_response(False, "Search query is required", return_data)
        
        limit = kwargs.get('limit', 10)
        try:
            limit = int(limit)
            if limit < 1 or limit > 50:
                limit = 10
        except (ValueError, TypeError):
            limit = 10
        
        results = sp.search(q=query, type="track", limit=limit)
        tracks = results.get('tracks', {}).get('items', [])
        
        if not tracks:
            return create_response(False, f"No tracks found for: {query}", return_data)
        
        track_list = []
        for track in tracks:
            track_info = {
                "name": track.get('name', ''),
                "artist": track.get('artists', [{}])[0].get('name', ''),
                "album": track.get('album', {}).get('name', ''),
                "uri": track.get('uri', ''),
                "duration": track.get('duration_ms', 0),
                "popularity": track.get('popularity', 0)
            }
            track_list.append(track_info)
        
        response_data = {
            "action": "search",
            "query": query,
            "total_results": len(track_list),
            "tracks": track_list
        }
        
        return create_response(True, f"Found {len(track_list)} tracks for: {query}", return_data, response_data)
        
    except Exception as e:
        error_msg = f"Error searching tracks: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def get_device_id(sp, device_preference=None):
    """Get active device ID"""
    try:
        if device_preference == "computer":
            device_id = os.getenv("SPOTIPY_COMPUTER_ID")
            if device_id:
                return device_id
        elif device_preference == "phone":
            device_id = os.getenv("SPOTIPY_PHONE_ID")
            if device_id:
                return device_id
        
        # Auto-detect active device
        devices = sp.devices()
        for device in devices.get('devices', []):
            if device.get('is_active') or device.get('type') in ("Computer", "Smartphone", "Speaker"):
                return device['id']
        
        # Return first available device if none are active
        if devices.get('devices'):
            return devices['devices'][0]['id']
        
        return None
        
    except Exception as e:
        log(f"Error getting device ID: {e}", "ERROR")
        return None

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "module": "spotify"
    }
    
    if data:
        response.update(data)
    
    if return_data:
        return response
    else:
        # Save to file
        filename = f"spotify_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            
        log(f"Spotify data saved to {filename}", "INFO")
        
    except Exception as e:
        log(f"Error saving to temp: {e}", "ERROR")
