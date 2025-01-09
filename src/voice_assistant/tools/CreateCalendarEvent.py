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
    'https://www.googleapis.com/auth/calendar',  # Full access to calendar
    'https://www.googleapis.com/auth/calendar.events',  # Full access to events
    'https://www.googleapis.com/auth/calendar.events.readonly',  # Read-only access to events
    'https://www.googleapis.com/auth/calendar.readonly',  # Read-only access to calendars
]
TOKEN_PATH = os.getenv('TOKEN_PATH', 'calendar_token.pickle')
CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH', 'credentials.json')

# Timeout configuration
AUTH_TIMEOUT = int(os.getenv('CALENDAR_AUTH_TIMEOUT', 15))
API_TIMEOUT = int(os.getenv('CALENDAR_API_TIMEOUT', 10))
MAX_RETRIES = int(os.getenv('CALENDAR_MAX_RETRIES', 3))
RETRY_DELAY = float(os.getenv('CALENDAR_RETRY_DELAY', 1.0))

class CreateCalendarEvent(BaseTool):
    """
    Creates a new event in Google Calendar with specified title, date, time, and duration.
    """

    title: str = Field(
        default=None,
        description="Title of the meeting"
    )
    
    date: str = Field(
        default=datetime.now().strftime("%Y-%m-%d"),
        description="Date of the meeting (YYYY-MM-DD format)"
    )
    
    time: str = Field(
        default=None,
        description="Start time of the meeting (HH:MM format in 24-hour)"
    )
    
    duration_minutes: int = Field(
        default=30,
        description="Duration of the meeting in minutes",
        gt=0,
        le=480  # Max 8 hours
    )
    
    description: str = Field(
        default="",
        description="Optional description for the meeting"
    )

    @property
    def schema(self) -> dict:
        return {
            "name": "createcalendarevent",
            "type": "function",
            "description": "Creates a new event in Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the meeting"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the meeting (YYYY-MM-DD format)",
                        "default": datetime.now().strftime("%Y-%m-%d")
                    },
                    "time": {
                        "type": "string",
                        "description": "Start time of the meeting (HH:MM format in 24-hour)"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration of the meeting in minutes",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 480
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description for the meeting",
                        "default": ""
                    }
                },
                "required": ["title", "time"]
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
        """Create a calendar event"""
        try:
            logger.info(f"Creating calendar event: {self.title}")
            
            # Use today's date if none provided
            date = self.date if self.date else datetime.now().strftime("%Y-%m-%d")
            
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
                    
                    # Create start and end times
                    start_time = datetime.strptime(f"{date} {self.time}", "%Y-%m-%d %H:%M")
                    end_time = start_time + timedelta(minutes=self.duration_minutes)
                    
                    event = {
                        'summary': self.title,
                        'description': self.description,
                        'start': {
                            'dateTime': start_time.isoformat(),
                            'timeZone': 'UTC',
                        },
                        'end': {
                            'dateTime': end_time.isoformat(),
                            'timeZone': 'UTC',
                        },
                        'reminders': {
                            'useDefault': False,
                            'overrides': [
                                {'method': 'email', 'minutes': 30},
                                {'method': 'popup', 'minutes': 15},
                            ],
                        },
                        'attendees': [
                            {'email': os.getenv('GOOGLE_CALENDAR_EMAIL', '')},  # Add your email
                        ],
                        'sendUpdates': 'all',  # This ensures notifications are sent
                    }
                    
                    logger.debug(f"Creating event: {event}")
                    result = await loop.run_in_executor(
                        executor,
                        lambda: service.events().insert(
                            calendarId='primary',
                            body=event
                        ).execute()
                    )
                    
                    event_id = result.get('id')
                    html_link = result.get('htmlLink')
                    
                    return (f"Meeting '{self.title}' scheduled for {date} at {self.time} "
                           f"(Duration: {self.duration_minutes} minutes)\n"
                           f"Calendar link: {html_link}")

            except TimeoutError:
                logger.warning("API timeout")
                return "Calendar API request timed out. Please try again."
            
            except Exception as e:
                logger.error(f"API error: {str(e)}")
                return f"Error creating calendar event: {str(e)}"
                    
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"Error creating calendar event: {str(e)}"


if __name__ == "__main__":  # pragma: no cover
    tool = CreateCalendarEvent()
    # Test creating an event
    event_details = {
        "title": "Test Meeting",
        "time": "14:30",
        "duration_minutes": 45,
        "description": "This is a test meeting"
    }
    asyncio.run(tool.run(**event_details)) 