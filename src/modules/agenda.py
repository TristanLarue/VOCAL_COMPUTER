# agenda.py
# Comprehensive Google Calendar management with service account authentication
# Supports add, modify, move, remove, lookup events with full details including colors and descriptions

import os
import json
import tempfile
from datetime import datetime, timedelta
from dateutil import parser
from dateutil.tz import gettz
import traceback
from utils import log

def run(action=None, **kwargs):
    """Main execution function for agenda operations"""
    try:
        if not action:
            return "Action is required. Use: list, today, week, month, add, modify, delete, move, search, or clear."
            
        action = action.lower()
        
        # Combine action and kwargs into args dictionary for internal functions
        args = {'action': action, **kwargs}
        
        if action in ['list', 'today', 'week', 'month']:
            return list_events(args)
        elif action in ['add', 'create']:
            return add_event(args)
        elif action in ['modify', 'update', 'edit']:
            return modify_event(args)
        elif action in ['delete', 'remove']:
            return delete_event(args)
        elif action == 'move':
            return move_event(args)
        elif action in ['search', 'find']:
            return search_events(args)
        elif action == 'clear':
            return clear_calendar(args)
        else:
            return "Invalid action. Use: list, today, week, month, add, modify, delete, move, search, or clear."
            
    except Exception as e:
        error_msg = f"Error in agenda module: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg

def get_calendar_service():
    """Initialize Google Calendar service with service account credentials"""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        # Get private key and handle newlines properly
        private_key = os.getenv("GOOGLE_PRIVATE_KEY")
        if not private_key:
            log("GOOGLE_PRIVATE_KEY not found in environment variables.", "ERROR")
            return None
        
        # Handle newline characters in private key
        private_key = private_key.replace('\\n', '\n')
        
        # Create credentials from environment variables
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
        
        # Validate required fields
        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
        missing_fields = [field for field in required_fields if not credentials_info.get(field)]
        if missing_fields:
            log(f"Missing required Google credentials: {', '.join(missing_fields)}", "ERROR")
            return None
        
        # Create credentials from the info
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        log("Google Calendar service initialized successfully.", "SYSTEM")
        return service
        
    except Exception as e:
        error_msg = f"Failed to initialize Google Calendar service: {str(e)}"
        log(error_msg, "ERROR")
        return None

def parse_datetime(date_str, time_str=None):
    """Parse date and time strings into datetime object"""
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
        elif 'next week' in date_str:
            base_date = datetime.now() + timedelta(days=7)
        elif 'next month' in date_str:
            base_date = datetime.now() + timedelta(days=30)
        elif 'monday' in date_str or 'tuesday' in date_str or 'wednesday' in date_str or 'thursday' in date_str or 'friday' in date_str or 'saturday' in date_str or 'sunday' in date_str:
            # Handle day of week references
            base_date = parser.parse(date_str)
        else:
            # Try to parse the date string directly
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
    """Parse duration string and return timedelta"""
    try:
        if not duration_str:
            return timedelta(hours=1)  # Default 1 hour
            
        duration_str = duration_str.lower().strip()
        
        # Extract numbers from the string
        numbers = [int(x) for x in duration_str.split() if x.isdigit()]
        if not numbers:
            # Try to extract numbers with regex
            import re
            numbers = [int(x) for x in re.findall(r'\d+', duration_str)]
        
        if not numbers:
            return timedelta(hours=1)  # Default fallback
        
        number = numbers[0]
        
        if any(word in duration_str for word in ['hour', 'hr', 'hrs']):
            return timedelta(hours=number)
        elif any(word in duration_str for word in ['minute', 'min', 'mins']):
            return timedelta(minutes=number)
        elif any(word in duration_str for word in ['day', 'days']):
            return timedelta(days=number)
        elif any(word in duration_str for word in ['week', 'weeks']):
            return timedelta(weeks=number)
        elif any(word in duration_str for word in ['second', 'sec', 'secs']):
            return timedelta(seconds=number)
        else:
            # Default to hours if no unit specified
            return timedelta(hours=number)
            
    except Exception as e:
        log(f"Error parsing duration '{duration_str}': {str(e)}", "ERROR")
        return timedelta(hours=1)  # Default fallback

def get_event_color_id(color_name):
    """Convert color name to Google Calendar color ID"""
    if not color_name:
        return '1'  # Default to blue
        
    color_name = color_name.lower().strip()
    
    color_map = {
        # Standard colors
        'blue': '1', 'lavender': '1',
        'green': '2', 'sage': '2', 
        'purple': '3', 'grape': '3', 'violet': '3',
        'red': '4', 'flamingo': '4', 'pink': '4',
        'yellow': '5', 'banana': '5', 'gold': '5',
        'orange': '6', 'tangerine': '6',
        'turquoise': '7', 'peacock': '7', 'teal': '7', 'cyan': '7',
        'gray': '8', 'grey': '8', 'graphite': '8',
        'bold_blue': '9', 'blueberry': '9', 'dark_blue': '9',
        'bold_green': '10', 'basil': '10', 'dark_green': '10',
        'bold_red': '11', 'tomato': '11', 'dark_red': '11'
    }
    
    color_id = color_map.get(color_name, '1')  # Default to blue
    log(f"Mapped color '{color_name}' to color ID '{color_id}'", "SYSTEM")
    return color_id

def list_events(args):
    """List calendar events"""
    try:
        service = get_calendar_service()
        if not service:
            return "Failed to connect to Google Calendar."
        
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        action = args.get('action', 'today')
        
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
            next_month = start_time.replace(month=start_time.month + 1) if start_time.month < 12 else start_time.replace(year=start_time.year + 1, month=1)
            end_time = next_month
        else:  # list - default to next 10 events
            start_time = now
            end_time = None
        
        # Fetch events
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z' if end_time else None,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"No events found for {action}."
        
        # Format events for output
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Parse start time for display
            if 'T' in start:
                start_dt = parser.parse(start)
                start_display = start_dt.strftime('%m/%d %I:%M %p')
            else:
                start_display = start
            
            title = event.get('summary', 'No Title')
            description = event.get('description', '')
            location = event.get('location', '')
            
            event_info = f"• {start_display}: {title}"
            if location:
                event_info += f" @ {location}"
            if description:
                event_info += f" - {description}"
            
            event_list.append(event_info)
        
        # Save to temp file for AI to read
        filename = args.get('filename', f'calendar_{action}.txt')
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, filename)
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(f"Calendar Events ({action}):\n\n")
            f.write('\n'.join(event_list))
        
        log(f"Calendar events for {action} retrieved and saved to temp file.", "COMMAND")
        return f"Retrieved {len(events)} events for {action}. Events saved to {filename} for AI analysis."
        
    except Exception as e:
        error_msg = f"Error listing events: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg

def add_event(args):
    """Add a new calendar event with full Google Calendar feature support"""
    try:
        service = get_calendar_service()
        if not service:
            return "Failed to connect to Google Calendar."
        
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        # Required fields
        title = args.get('title')
        if not title:
            return "Event title is required."
        
        # Check if this is an all-day event
        all_day = args.get('all_day', False) or args.get('allday', False)
        if isinstance(all_day, str):
            all_day = all_day.lower() in ['true', 'yes', '1', 'on']
        
        if all_day:
            # All-day event
            date_str = args.get('date', 'today')
            start_date = parse_datetime(date_str, None).date()
            
            # For all-day events, end date is the next day
            end_date_str = args.get('end_date')
            if end_date_str:
                end_date = parse_datetime(end_date_str, None).date()
            else:
                end_date = start_date + timedelta(days=1)
            
            event = {
                'summary': title,
                'start': {
                    'date': start_date.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'end': {
                    'date': end_date.isoformat(),
                    'timeZone': 'America/New_York',
                },
            }
            
        else:
            # Timed event
            date_str = args.get('date', 'today')
            
            # Handle start time
            start_time_str = args.get('start_time') or args.get('time')
            if not start_time_str:
                start_time_str = '9:00 AM'  # Default start time
            start_datetime = parse_datetime(date_str, start_time_str)
            
            # Handle end time - can be specified directly or calculated from duration
            end_time_str = args.get('end_time')
            if end_time_str:
                # End time specified directly
                end_date_str = args.get('end_date', date_str)
                end_datetime = parse_datetime(end_date_str, end_time_str)
            else:
                # Calculate end time from duration
                duration_str = args.get('duration', '1 hour')
                duration = parse_duration(duration_str)
                end_datetime = start_datetime + duration
            
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
        
        # Optional fields
        if args.get('description'):
            event['description'] = args.get('description')
        
        if args.get('location'):
            event['location'] = args.get('location')
        
        # Handle color
        color = args.get('color')
        if color:
            event['colorId'] = get_event_color_id(color)
        
        # Handle visibility (public, private, default)
        visibility = args.get('visibility')
        if visibility and visibility.lower() in ['public', 'private', 'default']:
            event['visibility'] = visibility.lower()
        
        # Handle recurrence
        recurrence = args.get('recurrence')
        if recurrence:
            event['recurrence'] = [format_recurrence_rule(recurrence)]
        
        # Handle reminders
        reminders = args.get('reminders')
        if reminders:
            event['reminders'] = format_reminders(reminders)
        else:
            # Use default reminders
            event['reminders'] = {'useDefault': True}
        
        # Handle attendees
        attendees = args.get('attendees')
        if attendees:
            event['attendees'] = format_attendees(attendees)
        
        # Create the event
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        if all_day:
            success_msg = f"All-day event '{title}' added successfully for {start_date.strftime('%m/%d/%Y')}."
        else:
            success_msg = f"Event '{title}' added successfully for {start_datetime.strftime('%m/%d/%Y at %I:%M %p')}."
        
        log(success_msg, "COMMAND")
        return success_msg
        
    except Exception as e:
        error_msg = f"Error adding event: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg

def modify_event(args):
    """Modify an existing calendar event"""
    try:
        service = get_calendar_service()
        if not service:
            return "Failed to connect to Google Calendar."
        
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        # Find event to modify
        event_id = args.get('event_id')
        if not event_id:
            # Search by title or other criteria
            search_query = args.get('title') or args.get('query')
            if not search_query:
                return "Event ID or search query required to modify event."
            
            # Search for events
            events_result = service.events().list(
                calendarId=calendar_id,
                q=search_query,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            if not events:
                return f"No events found matching '{search_query}'."
            
            event = events[0]  # Use first match
            event_id = event['id']
        else:
            # Get event by ID
            event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # Modify event fields
        if args.get('new_title'):
            event['summary'] = args.get('new_title')
        
        # Handle time changes
        if args.get('new_date') or args.get('new_start_time') or args.get('new_end_time'):
            # Determine if this is an all-day event
            is_all_day = 'date' in event['start']
            
            if is_all_day:
                # Handle all-day event modifications
                if args.get('new_date'):
                    new_date = parse_datetime(args.get('new_date'), None).date()
                    event['start']['date'] = new_date.isoformat()
                    # Preserve duration for all-day events
                    old_start = parser.parse(event['start']['date']).date()
                    old_end = parser.parse(event['end']['date']).date()
                    duration_days = (old_end - old_start).days
                    event['end']['date'] = (new_date + timedelta(days=duration_days)).isoformat()
            else:
                # Handle timed event modifications
                new_date = args.get('new_date')
                new_start_time = args.get('new_start_time')
                new_end_time = args.get('new_end_time')
                
                if new_date or new_start_time:
                    # Parse current start time
                    current_start = parser.parse(event['start']['dateTime'])
                    
                    # Use new date if provided, otherwise keep current date
                    if new_date:
                        new_start_date = parse_datetime(new_date, None).date()
                    else:
                        new_start_date = current_start.date()
                    
                    # Use new start time if provided, otherwise keep current time
                    if new_start_time:
                        new_start_time_parsed = parser.parse(new_start_time).time()
                    else:
                        new_start_time_parsed = current_start.time()
                    
                    new_start = datetime.combine(new_start_date, new_start_time_parsed)
                    event['start']['dateTime'] = new_start.isoformat()
                    
                    # Handle end time
                    if new_end_time:
                        new_end_time_parsed = parser.parse(new_end_time).time()
                        new_end = datetime.combine(new_start_date, new_end_time_parsed)
                    else:
                        # Preserve duration
                        old_start = parser.parse(event['start']['dateTime'])
                        old_end = parser.parse(event['end']['dateTime'])
                        duration = old_end - old_start
                        new_end = new_start + duration
                    
                    event['end']['dateTime'] = new_end.isoformat()
        
        # Handle duration changes
        if args.get('new_duration'):
            new_duration = parse_duration(args.get('new_duration'))
            if 'dateTime' in event['start']:
                start_datetime = parser.parse(event['start']['dateTime'])
                event['end']['dateTime'] = (start_datetime + new_duration).isoformat()
        
        # Update other properties
        if args.get('description') is not None:
            event['description'] = args.get('description')
        
        if args.get('location') is not None:
            event['location'] = args.get('location')
        
        if args.get('color'):
            event['colorId'] = get_event_color_id(args.get('color'))
        
        if args.get('visibility'):
            event['visibility'] = args.get('visibility').lower()
        
        # Handle reminders update
        if args.get('reminders'):
            event['reminders'] = format_reminders(args.get('reminders'))
        
        # Handle attendees update
        if args.get('attendees'):
            event['attendees'] = format_attendees(args.get('attendees'))
        
        # Update the event
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        
        success_msg = f"Event '{event.get('summary')}' modified successfully."
        log(success_msg, "COMMAND")
        return success_msg
        
    except Exception as e:
        error_msg = f"Error modifying event: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg

def delete_event(args):
    """Delete a calendar event"""
    try:
        service = get_calendar_service()
        if not service:
            return "Failed to connect to Google Calendar."
        
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        # Find event to delete
        event_id = args.get('event_id')
        if not event_id:
            # Search by title or other criteria
            search_query = args.get('title') or args.get('query')
            if not search_query:
                return "Event ID or search query required to delete event."
            
            # Search for events
            events_result = service.events().list(
                calendarId=calendar_id,
                q=search_query,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            if not events:
                return f"No events found matching '{search_query}'."
            
            event = events[0]  # Use first match
            event_id = event['id']
            event_title = event.get('summary', 'Unknown')
        else:
            # Get event by ID to get title
            event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            event_title = event.get('summary', 'Unknown')
        
        # Delete the event
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        
        success_msg = f"Event '{event_title}' deleted successfully."
        log(success_msg, "COMMAND")
        return success_msg
        
    except Exception as e:
        error_msg = f"Error deleting event: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg

def move_event(args):
    """Move an event to a different date/time"""
    try:
        # Use modify_event with new date/time
        return modify_event(args)
        
    except Exception as e:
        error_msg = f"Error moving event: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg

def search_events(args):
    """Search for events by query"""
    try:
        service = get_calendar_service()
        if not service:
            return "Failed to connect to Google Calendar."
        
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        query = args.get('query')
        
        if not query:
            return "Search query is required."
        
        # Search for events
        events_result = service.events().list(
            calendarId=calendar_id,
            q=query,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"No events found matching '{query}'."
        
        # Format search results
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
                start_dt = parser.parse(start)
                start_display = start_dt.strftime('%m/%d %I:%M %p')
            else:
                start_display = start
            
            title = event.get('summary', 'No Title')
            event_info = f"• {start_display}: {title} (ID: {event['id']})"
            event_list.append(event_info)
        
        # Save to temp file
        filename = args.get('filename', f'calendar_search_{query.replace(" ", "_")}.txt')
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, filename)
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(f"Search Results for '{query}':\n\n")
            f.write('\n'.join(event_list))
        
        success_msg = f"Found {len(events)} events matching '{query}'. Results saved to {filename}."
        log(success_msg, "COMMAND")
        return success_msg
        
    except Exception as e:
        error_msg = f"Error searching events: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg

def clear_calendar(args):
    """Clear all events from calendar (use with caution)"""
    try:
        service = get_calendar_service()
        if not service:
            return "Failed to connect to Google Calendar."
        
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        # Get all events
        events_result = service.events().list(
            calendarId=calendar_id,
            maxResults=250,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "No events to clear."
        
        # Delete all events
        deleted_count = 0
        for event in events:
            try:
                service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
                deleted_count += 1
            except Exception as e:
                log(f"Failed to delete event {event.get('summary', 'Unknown')}: {str(e)}", "ERROR")
        
        success_msg = f"Cleared {deleted_count} events from calendar."
        log(success_msg, "COMMAND")
        return success_msg
        
    except Exception as e:
        error_msg = f"Error clearing calendar: {str(e)}"
        log(error_msg, "ERROR")
        return error_msg

def format_recurrence_rule(recurrence_str):
    """Convert recurrence string to Google Calendar RRULE format"""
    try:
        recurrence_str = recurrence_str.lower()
        
        if 'daily' in recurrence_str:
            return 'RRULE:FREQ=DAILY'
        elif 'weekly' in recurrence_str:
            return 'RRULE:FREQ=WEEKLY'
        elif 'monthly' in recurrence_str:
            return 'RRULE:FREQ=MONTHLY'
        elif 'yearly' in recurrence_str:
            return 'RRULE:FREQ=YEARLY'
        elif 'weekdays' in recurrence_str:
            return 'RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR'
        elif 'weekends' in recurrence_str:
            return 'RRULE:FREQ=WEEKLY;BYDAY=SA,SU'
        else:
            # Try to parse more complex patterns
            return f'RRULE:FREQ=WEEKLY'  # Default fallback
            
    except Exception:
        return 'RRULE:FREQ=WEEKLY'  # Safe fallback

def format_reminders(reminder_str):
    """Convert reminder string to Google Calendar reminder format"""
    try:
        reminders = {'useDefault': False, 'overrides': []}
        
        # Parse reminder times
        if isinstance(reminder_str, str):
            reminder_parts = reminder_str.lower().split(',')
        else:
            reminder_parts = [str(reminder_str)]
        
        for reminder in reminder_parts:
            reminder = reminder.strip()
            
            if 'minute' in reminder:
                minutes = int(''.join(filter(str.isdigit, reminder)) or 10)
                reminders['overrides'].append({'method': 'popup', 'minutes': minutes})
            elif 'hour' in reminder:
                hours = int(''.join(filter(str.isdigit, reminder)) or 1)
                reminders['overrides'].append({'method': 'popup', 'minutes': hours * 60})
            elif 'day' in reminder:
                days = int(''.join(filter(str.isdigit, reminder)) or 1)
                reminders['overrides'].append({'method': 'popup', 'minutes': days * 24 * 60})
            else:
                # Default to 15 minutes
                reminders['overrides'].append({'method': 'popup', 'minutes': 15})
        
        return reminders
        
    except Exception:
        return {'useDefault': True}

def format_attendees(attendees_str):
    """Convert attendees string to Google Calendar attendees format"""
    try:
        attendees = []
        
        if isinstance(attendees_str, str):
            attendee_list = attendees_str.split(',')
        else:
            attendee_list = [str(attendees_str)]
        
        for attendee in attendee_list:
            attendee = attendee.strip()
            if '@' in attendee:
                attendees.append({'email': attendee})
            else:
                # If no @ symbol, treat as display name
                attendees.append({'displayName': attendee})
        
        return attendees
        
    except Exception:
        return []
