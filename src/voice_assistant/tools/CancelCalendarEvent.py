from agency_swarm.tools import BaseTool
from pydantic import Field
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import asyncio
from concurrent.futures import ThreadPoolExecutor
import socket
import logging
from typing import Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]
TOKEN_PATH = os.getenv('TOKEN_PATH', 'calendar_token.pickle')
CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH', 'credentials.json')

# Timeout configuration
AUTH_TIMEOUT = int(os.getenv('CALENDAR_AUTH_TIMEOUT', 15))
API_TIMEOUT = int(os.getenv('CALENDAR_API_TIMEOUT', 10))
MAX_RETRIES = int(os.getenv('CALENDAR_MAX_RETRIES', 3))
RETRY_DELAY = float(os.getenv('CALENDAR_RETRY_DELAY', 1.0))

class CancelCalendarEvent(BaseTool):
    """
    Cancels/deletes a calendar event based on title and date/time.
    """

    title: str = Field(
        default=None,
        description="Title of the meeting to cancel"
    )
    
    date: str = Field(
        default=datetime.now().strftime("%Y-%m-%d"),
        description="Date of the meeting (YYYY-MM-DD format)"
    )
    
    time: str = Field(
        default=None,
        description="Time of the meeting (HH:MM format in 24-hour). If not provided, will match only by title and date."
    )

    @property
    def schema(self) -> dict:
        return {
            "name": "cancelcalendarevent",
            "type": "function",
            "description": "Cancels/deletes a calendar event based on title and date/time",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the meeting to cancel"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the meeting (YYYY-MM-DD format)",
                        "default": datetime.now().strftime("%Y-%m-%d")
                    },
                    "time": {
                        "type": "string",
                        "description": "Time of the meeting (HH:MM format in 24-hour). Optional.",
                        "default": None
                    }
                },
                "required": ["title"]
            }
        }

    async def authenticate_calendar(self) -> tuple[Optional[Credentials], Optional[str]]:
        """Handle Calendar authentication with timeout"""
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Authentication attempt {attempt + 1}/{MAX_RETRIES}")
                creds = None
                
                await asyncio.sleep(0.5)
                
                if os.path.exists(TOKEN_PATH):
                    logger.debug("Loading existing token")
                    with open(TOKEN_PATH, 'rb') as token:
                        creds = pickle.load(token)

                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        logger.info("Refreshing expired credentials")
                        await asyncio.sleep(0.5)
                        creds.refresh(Request())
                    else:
                        logger.info("Initiating new authentication flow")
                        if not os.path.exists(CREDENTIALS_PATH):
                            return None, "Error: credentials.json file not found."
                        
                        await asyncio.sleep(0.5)
                        
                        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                        loop = asyncio.get_event_loop()
                        
                        def auth_flow():
                            return flow.run_local_server(port=0, timeout=AUTH_TIMEOUT)
                        
                        with ThreadPoolExecutor() as executor:
                            future = executor.submit(auth_flow)
                            creds = await loop.run_in_executor(
                                None,
                                lambda: future.result(timeout=AUTH_TIMEOUT)
                            )
                            
                            with open(TOKEN_PATH, 'wb') as token:
                                pickle.dump(creds, token)

                return creds, None

            except TimeoutError:
                logger.warning(f"Authentication timeout on attempt {attempt + 1}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return None, "Authentication timed out after multiple attempts."
            
            except Exception as e:
                logger.error(f"Authentication error on attempt {attempt + 1}: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return None, f"Authentication failed: {str(e)}"

    async def run(self):
        """Cancel/delete a calendar event"""
        try:
            logger.info(f"Attempting to cancel event: {self.title}")
            
            if not self.date:
                self.date = datetime.now().strftime("%Y-%m-%d")
            
            creds, error = await self.authenticate_calendar()
            if error:
                return error
            if not creds:
                return "Failed to authenticate with Google Calendar."

            try:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    service = build('calendar', 'v3', credentials=creds)
                    socket.setdefaulttimeout(API_TIMEOUT)
                    
                    # Set time range for search
                    date_obj = datetime.strptime(self.date, "%Y-%m-%d")
                    time_min = date_obj.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                    time_max = date_obj.replace(hour=23, minute=59, second=59).isoformat() + 'Z'
                    
                    # Search for events matching the criteria
                    events_result = await loop.run_in_executor(
                        executor,
                        lambda: service.events().list(
                            calendarId='primary',
                            timeMin=time_min,
                            timeMax=time_max,
                            q=self.title,  # Search by title
                            singleEvents=True,
                            orderBy='startTime'
                        ).execute()
                    )
                    
                    events = events_result.get('items', [])
                    
                    if not events:
                        return f"No events found matching '{self.title}' on {self.date}"
                    
                    # Filter events by time if specified
                    if self.time:
                        target_time = datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")
                        matching_events = []
                        for event in events:
                            start = event['start'].get('dateTime', event['start'].get('date'))
                            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            if (event_time.hour == target_time.hour and 
                                event_time.minute == target_time.minute):
                                matching_events.append(event)
                        events = matching_events
                    
                    if not events:
                        return f"No events found matching '{self.title}' at {self.time} on {self.date}"
                    
                    # Delete the matching events
                    deleted_count = 0
                    for event in events:
                        try:
                            await loop.run_in_executor(
                                executor,
                                lambda: service.events().delete(
                                    calendarId='primary',
                                    eventId=event['id']
                                ).execute()
                            )
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"Error deleting event {event['id']}: {str(e)}")
                    
                    if deleted_count == 1:
                        return f"Successfully cancelled the meeting '{self.title}' on {self.date}"
                    elif deleted_count > 1:
                        return f"Successfully cancelled {deleted_count} occurrences of '{self.title}' on {self.date}"
                    else:
                        return "Failed to cancel any events"

            except TimeoutError:
                logger.warning("API timeout")
                return "Calendar API request timed out. Please try again."
            
            except Exception as e:
                logger.error(f"API error: {str(e)}")
                return f"Error cancelling calendar event: {str(e)}"
                    
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"Error cancelling calendar event: {str(e)}"


if __name__ == "__main__":  # pragma: no cover
    tool = CancelCalendarEvent()
    # Test cancelling an event
    cancel_details = {
        "title": "Test Meeting",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": "14:30"
    }
    asyncio.run(tool.run(**cancel_details)) 