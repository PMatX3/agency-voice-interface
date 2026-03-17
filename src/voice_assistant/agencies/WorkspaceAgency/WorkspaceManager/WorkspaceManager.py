from agency_swarm import Agent

from voice_assistant.tools.CreateDailyLog import CreateDailyLog
from voice_assistant.tools.ExecuteCommand import ExecuteCommand
from voice_assistant.tools.GetMetrics import GetMetrics
from voice_assistant.tools.QueryDatabase import QueryDatabase
from voice_assistant.tools.ReadWorkspaceContext import ReadWorkspaceContext
from voice_assistant.tools.RunCollection import RunCollection
from voice_assistant.tools.UpdateProjectRegister import UpdateProjectRegister


class WorkspaceManager(Agent):
    def __init__(self):
        super().__init__(
            name="WorkspaceManager",
            description="Manages the AIOS workspace: reads context, queries data, updates projects, runs collections, and logs activity.",
            instructions="./instructions.md",
            tools=[
                ReadWorkspaceContext,
                QueryDatabase,
                UpdateProjectRegister,
                RunCollection,
                GetMetrics,
                CreateDailyLog,
                ExecuteCommand,
            ],
            model="gpt-4o",
        )
