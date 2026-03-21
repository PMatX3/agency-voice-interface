import asyncio
import logging
from datetime import datetime, timedelta

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

from voice_assistant.utils.google_services_utils import GoogleServicesUtils

load_dotenv()

logger = logging.getLogger(__name__)


class CreateCalendarEvent(BaseTool):
    """Creates a new event in Google Calendar with specified title, date, time, and duration."""

    title: str = Field(default=None, description="Title of the meeting")
    date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d"),
        description="Date of the meeting (YYYY-MM-DD format)",
    )
    time: str = Field(default=None, description="Start time of the meeting (HH:MM format in 24-hour)")
    duration_minutes: int = Field(
        default=30,
        description="Duration of the meeting in minutes",
        gt=0,
        le=480,
    )
    description: str = Field(default="", description="Optional description for the meeting")

    async def run(self):
        """Create a calendar event."""
        try:
            logger.info(f"Creating calendar event: {self.title}")

            service = await GoogleServicesUtils.authenticate_service("calendar")

            start_time = datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")
            end_time = start_time + timedelta(minutes=self.duration_minutes)

            event = {
                "summary": self.title,
                "description": self.description,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "Europe/London",
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "Europe/London",
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 15},
                    ],
                },
            }

            result = await asyncio.to_thread(
                lambda: service.events()
                .insert(calendarId="primary", body=event)
                .execute()
            )

            html_link = result.get("htmlLink")
            return (
                f"Meeting '{self.title}' scheduled for {self.date} at {self.time} "
                f"(Duration: {self.duration_minutes} minutes)\n"
                f"Calendar link: {html_link}"
            )

        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}")
            return f"Error creating calendar event: {str(e)}"


if __name__ == "__main__":
    tool = CreateCalendarEvent(title="Test Meeting", time="14:30", duration_minutes=45)
    print(asyncio.run(tool.run()))
