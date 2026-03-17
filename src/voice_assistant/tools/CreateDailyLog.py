import os
from datetime import datetime

from agency_swarm.tools import BaseTool
from pydantic import Field

from voice_assistant.config import WORKSPACE_DIR


class CreateDailyLog(BaseTool):
    """Add an entry to today's daily log in the AIOS workspace."""

    entry: str = Field(
        ...,
        description="The log entry to add. Can be a note, decision, action item, or observation.",
    )
    category: str = Field(
        default="note",
        description="Category: 'note', 'decision', 'action', 'meeting', 'idea'",
    )

    async def run(self) -> str:
        if not WORKSPACE_DIR:
            return "WORKSPACE_DIR not configured. Set it in .env to enable workspace tools."
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = os.path.join(WORKSPACE_DIR, "outputs", "daily-log")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{today}.md")
        timestamp = datetime.now().strftime("%H:%M")
        if not os.path.exists(log_path):
            header = f"# Daily Log: {today}\n\n"
            with open(log_path, "w") as f:
                f.write(header)
        formatted_entry = (
            f"- **[{timestamp}] [{self.category.upper()}]** {self.entry}\n"
        )
        with open(log_path, "a") as f:
            f.write(formatted_entry)
        return f"Logged to {today}: [{self.category}] {self.entry}"


if __name__ == "__main__":
    import asyncio

    tool = CreateDailyLog(entry="Test log entry from voice", category="note")
    print(asyncio.run(tool.run()))
