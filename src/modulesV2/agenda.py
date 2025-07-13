# agenda.py - V2
# Comprehensive Google Calendar management with direct return capability
# Simplified interface with consistent keywords

import os
import json
from datetime import datetime, timedelta
from dateutil import parser
from utils import log

def run(action="list", return_data=False, **kwargs):
    """
    Unified agenda interface
    Actions: list, today, week, month, add, edit, delete, search, clear
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['list', 'today', 'week', 'month']:
            return handle_list_events(action, return_data, **kwargs)
        elif action in ['add', 'create', 'new']:
            return handle_add_event(return_data, **kwargs)
        elif action in ['edit', 'modify', 'update', 'change']:
            return handle_edit_event(return_data, **kwargs)
        elif action in ['delete', 'remove', 'cancel']:
            return handle_delete_event(return_data, **kwargs)
        elif action in ['search', 'find', 'lookup']:
            return handle_search_events(return_data, **kwargs)
        elif action in ['clear', 'wipe', 'empty']:
            return handle_clear_calendar(return_data, **kwargs)
        else:
            error_msg = f"Unknown action: {action}. Use: list, today, week, month, add, edit, delete, search, clear"
            return create_response(False, error_msg, return_data)
            
    except Exception as e:
        error_msg = f"Error in agenda module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def get_calendar_service():
    """Initialize Google Calendar service"""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        # Get credentials from environment
        private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n')
        
        credentials_info = {
            "type": os.getenv("GOOGLE_SERVICE_ACCOUNT_TYPE"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
            "private_key": private_key,
            "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
            "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN")
        }
        
        credentials = Credentials.from_service_account_info(
            credentials_info, scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        return build('calendar', 'v3', credentials=credentials)
        
    except Exception as e:
        log(f"Calendar service initialization failed: {str(e)}", "ERROR")
        return None

def handle_list_events(action, return_data, **kwargs):
    """Handle event listing with time range"""
    try:
        service = get_calendar_service()
        if not service:
            return create_response(False, "Calendar service unavailable", return_data)
        
        # Determine time range
        now = datetime.now()
        if action == 'today':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
        elif action == 'week':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=7)
        elif action == 'month':
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=31)
        else:  # list
            start_time = now
            end_time = now + timedelta(days=7)
        
        # Fetch events
        events_result = service.events().list(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            timeMin=start_time.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format events
        formatted_events = []
        for event in events:
            formatted_events.append({
                'title': event.get('summary', 'No Title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'id': event.get('id', '')
            })
        
        success_msg = f"Found {len(events)} events for {action}"
        return create_response(True, success_msg, return_data, {
            'events': formatted_events,
            'count': len(events),
            'timeframe': action
        })
        
    except Exception as e:
        error_msg = f"Error listing events: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_add_event(return_data, **kwargs):
    """Handle event creation"""
    try:
        service = get_calendar_service()
        if not service:
            return create_response(False, "Calendar service unavailable", return_data)
        
        # Required fields
        title = kwargs.get('title') or kwargs.get('name') or kwargs.get('event')
        if not title:
            return create_response(False, "Event title is required", return_data)
        
        # Parse date and time
        date_str = kwargs.get('date', 'today')
        time_str = kwargs.get('time') or kwargs.get('start_time', '9:00 AM')
        
        start_datetime = parse_datetime(date_str, time_str)
        
        # Calculate end time
        if kwargs.get('end_time'):
            end_datetime = parse_datetime(date_str, kwargs.get('end_time'))
        else:
            duration = kwargs.get('duration', '1 hour')
            end_datetime = start_datetime + parse_duration(duration)
        
        # Create event
        event = {
            'summary': title,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'America/New_York',
            },
        }
        
        # Add optional fields
        if kwargs.get('location'):
            event['location'] = kwargs.get('location')
        if kwargs.get('description') or kwargs.get('notes'):
            event['description'] = kwargs.get('description') or kwargs.get('notes')
        
        # Create the event
        created_event = service.events().insert(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            body=event
        ).execute()
        
        success_msg = f"Event '{title}' created successfully"
        return create_response(True, success_msg, return_data, {
            'event_id': created_event.get('id'),
            'title': title,
            'start_time': start_datetime.isoformat(),
            'end_time': end_datetime.isoformat()
        })
        
    except Exception as e:
        error_msg = f"Error adding event: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_edit_event(return_data, **kwargs):
    """Handle event modification"""
    try:
        event_id = kwargs.get('id') or kwargs.get('event_id')
        if not event_id:
            return create_response(False, "Event ID is required for editing", return_data)
        
        service = get_calendar_service()
        if not service:
            return create_response(False, "Calendar service unavailable", return_data)
        
        # Get existing event
        event = service.events().get(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            eventId=event_id
        ).execute()
        
        # Update fields
        if kwargs.get('title') or kwargs.get('name'):
            event['summary'] = kwargs.get('title') or kwargs.get('name')
        if kwargs.get('location'):
            event['location'] = kwargs.get('location')
        if kwargs.get('description') or kwargs.get('notes'):
            event['description'] = kwargs.get('description') or kwargs.get('notes')
        
        # Update the event
        updated_event = service.events().update(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            eventId=event_id,
            body=event
        ).execute()
        
        success_msg = f"Event updated successfully"
        return create_response(True, success_msg, return_data, {
            'event_id': event_id,
            'title': event.get('summary', 'Unknown')
        })
        
    except Exception as e:
        error_msg = f"Error editing event: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_delete_event(return_data, **kwargs):
    """Handle event deletion"""
    try:
        event_id = kwargs.get('id') or kwargs.get('event_id')
        if not event_id:
            return create_response(False, "Event ID is required for deletion", return_data)
        
        service = get_calendar_service()
        if not service:
            return create_response(False, "Calendar service unavailable", return_data)
        
        # Get event title before deletion
        event = service.events().get(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            eventId=event_id
        ).execute()
        
        event_title = event.get('summary', 'Unknown')
        
        # Delete the event
        service.events().delete(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            eventId=event_id
        ).execute()
        
        success_msg = f"Event '{event_title}' deleted successfully"
        return create_response(True, success_msg, return_data, {
            'event_id': event_id,
            'title': event_title
        })
        
    except Exception as e:
        error_msg = f"Error deleting event: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_search_events(return_data, **kwargs):
    """Handle event search"""
    try:
        query = kwargs.get('query') or kwargs.get('search') or kwargs.get('term')
        if not query:
            return create_response(False, "Search query is required", return_data)
        
        service = get_calendar_service()
        if not service:
            return create_response(False, "Calendar service unavailable", return_data)
        
        # Search events
        events_result = service.events().list(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            q=query,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format results
        formatted_events = []
        for event in events:
            formatted_events.append({
                'title': event.get('summary', 'No Title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'id': event.get('id', ''),
                'location': event.get('location', ''),
                'description': event.get('description', '')
            })
        
        success_msg = f"Found {len(events)} events matching '{query}'"
        return create_response(True, success_msg, return_data, {
            'events': formatted_events,
            'count': len(events),
            'query': query
        })
        
    except Exception as e:
        error_msg = f"Error searching events: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_clear_calendar(return_data, **kwargs):
    """Handle calendar clearing"""
    try:
        service = get_calendar_service()
        if not service:
            return create_response(False, "Calendar service unavailable", return_data)
        
        # Get all events
        events_result = service.events().list(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            maxResults=250,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        deleted_count = 0
        
        # Delete all events
        for event in events:
            try:
                service.events().delete(
                    calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
                    eventId=event['id']
                ).execute()
                deleted_count += 1
            except Exception as e:
                log(f"Failed to delete event {event.get('summary', 'Unknown')}: {str(e)}", "ERROR")
        
        success_msg = f"Cleared {deleted_count} events from calendar"
        return create_response(True, success_msg, return_data, {
            'deleted_count': deleted_count,
            'total_events': len(events)
        })
        
    except Exception as e:
        error_msg = f"Error clearing calendar: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def parse_datetime(date_str, time_str=None):
    """Parse date and time strings"""
    try:
        if not date_str:
            return datetime.now()
        
        date_str = date_str.lower().strip()
        
        # Handle natural language dates
        if date_str in ['today', 'now']:
            base_date = datetime.now()
        elif date_str in ['tomorrow', 'tmrw']:
            base_date = datetime.now() + timedelta(days=1)
        elif date_str in ['yesterday']:
            base_date = datetime.now() - timedelta(days=1)
        else:
            base_date = parser.parse(date_str)
        
        # Add time if provided
        if time_str:
            time_str = time_str.strip()
            time_part = parser.parse(time_str).time()
            return datetime.combine(base_date.date(), time_part)
        
        return base_date
        
    except Exception as e:
        log(f"Error parsing datetime '{date_str}' with time '{time_str}': {str(e)}", "ERROR")
        return datetime.now()

def parse_duration(duration_str):
    """Parse duration string"""
    try:
        if not duration_str:
            return timedelta(hours=1)
        
        duration_str = duration_str.lower().strip()
        
        # Extract numbers
        import re
        numbers = [int(x) for x in re.findall(r'\d+', duration_str)]
        
        if not numbers:
            return timedelta(hours=1)
        
        number = numbers[0]
        
        if any(word in duration_str for word in ['hour', 'hr', 'hrs']):
            return timedelta(hours=number)
        elif any(word in duration_str for word in ['minute', 'min', 'mins']):
            return timedelta(minutes=number)
        elif any(word in duration_str for word in ['day', 'days']):
            return timedelta(days=number)
        else:
            return timedelta(hours=number)
            
    except Exception as e:
        log(f"Error parsing duration '{duration_str}': {str(e)}", "ERROR")
        return timedelta(hours=1)

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    if return_data:
        return {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'agenda'
        }
    else:
        # File-based response for complex analysis
        filename = f"agenda_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_data = {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'agenda',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(os.path.join(temp_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2)
        
        log(message, "COMMAND")
        return f"Calendar operation completed. Data saved to {filename}"
