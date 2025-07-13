# browse.py - V2
# Web browser control with enhanced capabilities
# Simplified interface with consistent keywords

import webbrowser
import os
import json
from datetime import datetime
from utils import log

def run(action="open", return_data=False, **kwargs):
    """
    Strict browse interface - exact keywords only
    Actions: open, search, youtube, maps, news
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function - strict keywords only
        if action == 'open':
            return handle_open_url(return_data, **kwargs)
        elif action == 'search':
            return handle_search(return_data, **kwargs)
        elif action == 'youtube':
            return handle_youtube(return_data, **kwargs)
        elif action == 'maps':
            return handle_maps(return_data, **kwargs)
        elif action == 'news':
            return handle_news(return_data, **kwargs)
        else:
            error_msg = f"Unknown action: {action}. Use: open, search, youtube, maps, news"
            return create_response(False, error_msg, return_data)
            
    except Exception as e:
        error_msg = f"Error in browse module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_open_url(return_data, **kwargs):
    """Handle direct URL opening - strict single argument"""
    try:
        url = kwargs.get('url')
        
        if not url:
            return create_response(False, "URL is required", return_data)
        
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Open URL
        webbrowser.open(url)
        
        return create_response(True, f"Opened {url}", return_data, {
            'url': url,
            'action': 'open'
        })
        
    except Exception as e:
        error_msg = f"Error opening URL: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_search(return_data, **kwargs):
    """Handle Google search - strict single argument"""
    try:
        query = kwargs.get('query')
        
        if not query:
            return create_response(False, "Search query is required", return_data)
        
        # Create Google search URL
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        
        # Open search
        webbrowser.open(search_url)
        
        return create_response(True, f"Searched for '{query}'", return_data, {
            'query': query,
            'url': search_url,
            'action': 'search'
        })
        
    except Exception as e:
        error_msg = f"Error performing search: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_youtube(return_data, **kwargs):
    """Handle YouTube search - strict single argument"""
    try:
        query = kwargs.get('query')
        
        if not query:
            return create_response(False, "YouTube query is required", return_data)
        
        # Create YouTube search URL
        youtube_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        
        # Open YouTube
        webbrowser.open(youtube_url)
        
        return create_response(True, f"Searched YouTube for '{query}'", return_data, {
            'query': query,
            'url': youtube_url,
            'action': 'youtube'
        })
        
    except Exception as e:
        error_msg = f"Error opening YouTube: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_maps(return_data, **kwargs):
    """Handle Google Maps - strict single argument"""
    try:
        location = kwargs.get('location')
        
        if not location:
            return create_response(False, "Location is required", return_data)
        
        # Create Google Maps URL
        maps_url = f"https://www.google.com/maps/search/{location.replace(' ', '+')}"
        
        # Open Maps
        webbrowser.open(maps_url)
        
        return create_response(True, f"Opened '{location}' in Maps", return_data, {
            'location': location,
            'url': maps_url,
            'action': 'maps'
        })
        
    except Exception as e:
        error_msg = f"Error opening Maps: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_news(return_data, **kwargs):
    """Handle news browsing - no arguments needed"""
    try:
        topic = kwargs.get('topic')  # Optional
        
        if topic:
            # News search with topic
            news_url = f"https://news.google.com/search?q={topic.replace(' ', '+')}"
            message = f"Opened news for '{topic}'"
        else:
            # General news
            news_url = "https://news.google.com/topstories"
            message = "Opened general news"
        
        # Open news
        webbrowser.open(news_url)
        
        return create_response(True, message, return_data, {
            'topic': topic,
            'url': news_url,
            'action': 'news'
        })
        
    except Exception as e:
        error_msg = f"Error opening news: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'module': 'browse'
    }
    
    if data:
        response.update(data)
    
    if return_data:
        return response
    else:
        # Save to file
        filename = f"browse_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            
        log(f"Browse data saved to {filename}", "INFO")
        
    except Exception as e:
        log(f"Error saving to temp: {e}", "ERROR")
