import os
from datetime import datetime

from agency_swarm.tools import BaseTool
from pydantic import Field

from voice_assistant.config import WORKSPACE_DIR


class UpdateProjectRegister(BaseTool):
    """Update a project's status, stage, or notes in the AIOS project register. Changes are logged for review rather than applied directly."""

    project_name: str = Field(
        ..., description="Name of the project to update (e.g. 'Impireum', 'Steinwood')"
    )
    field: str = Field(
        ...,
        description="Field to update: 'status', 'stage', 'probability', 'next_milestone', or 'notes'",
    )
    value: str = Field(..., description="New value for the field")

    async def run(self) -> str:
        if not WORKSPACE_DIR:
            return "WORKSPACE_DIR not configured. Set it in .env to enable workspace tools."
        register_path = os.path.join(WORKSPACE_DIR, "outputs", "project-register.md")
        if not os.path.exists(register_path):
            return "Project register not found."
        with open(register_path, "r") as f:
            content = f.read()
        if self.project_name.lower() not in content.lower():
            return f"Project '{self.project_name}' not found in register."
        log_path = os.path.join(
            WORKSPACE_DIR, "outputs", "daily-log", "voice-updates.md"
        )
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"- [{timestamp}] Update {self.project_name}: {self.field} = {self.value}\n"
        with open(log_path, "a") as f:
            f.write(entry)
        return f"Logged update for {self.project_name}: {self.field} set to '{self.value}'. Change logged to voice-updates.md for review."


if __name__ == "__main__":
    import asyncio

    tool = UpdateProjectRegister(
        project_name="Impireum", field="status", value="Contract sent"
    )
    print(asyncio.run(tool.run()))
