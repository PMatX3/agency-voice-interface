import asyncio
import logging
from datetime import datetime
from typing import Optional

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

from voice_assistant.utils.google_services_utils import GoogleServicesUtils

load_dotenv()

logger = logging.getLogger(__name__)


class CancelCalendarEvent(BaseTool):
    """Cancels/deletes a calendar event based on title and date/time."""

    title: str = Field(default=None, description="Title of the meeting to cancel")
    date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d"),
        description="Date of the meeting (YYYY-MM-DD format)",
    )
    time: Optional[str] = Field(
        default=None,
        description="Time of the meeting (HH:MM format in 24-hour). If not provided, will match only by title and date.",
    )

    async def run(self):
        """Cancel/delete a calendar event."""
        try:
            logger.info(f"Attempting to cancel event: {self.title}")

            service = await GoogleServicesUtils.authenticate_service("calendar")

            date_obj = datetime.strptime(self.date, "%Y-%m-%d")
            time_min = date_obj.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            time_max = date_obj.replace(hour=23, minute=59, second=59).isoformat() + "Z"

            events_result = await asyncio.to_thread(
                lambda: service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    q=self.title,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            if not events:
                return f"No events found matching '{self.title}' on {self.date}"

            # Filter by time if specified
            if self.time:
                target_time = datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")
                matching = []
                for event in events:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    event_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    if event_time.hour == target_time.hour and event_time.minute == target_time.minute:
                        matching.append(event)
                events = matching

            if not events:
                return f"No events found matching '{self.title}' at {self.time} on {self.date}"

            deleted_count = 0
            for event in events:
                try:
                    await asyncio.to_thread(
                        lambda e=event: service.events()
                        .delete(calendarId="primary", eventId=e["id"])
                        .execute()
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

        except Exception as e:
            logger.error(f"Error cancelling calendar event: {str(e)}")
            return f"Error cancelling calendar event: {str(e)}"


if __name__ == "__main__":
    tool = CancelCalendarEvent(title="Test Meeting")
    print(asyncio.run(tool.run()))
