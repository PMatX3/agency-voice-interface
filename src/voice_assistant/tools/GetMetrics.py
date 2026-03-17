import os

from agency_swarm.tools import BaseTool

from voice_assistant.config import WORKSPACE_DIR


class GetMetrics(BaseTool):
    """Get the current AIOS business metrics summary including revenue, pipeline, and activity data."""

    async def run(self) -> str:
        if not WORKSPACE_DIR:
            return "WORKSPACE_DIR not configured. Set it in .env to enable workspace tools."
        metrics_path = os.path.join(
            WORKSPACE_DIR, "context", "group", "key-metrics.md"
        )
        if not os.path.exists(metrics_path):
            return "Key metrics file not found. Run data collection first."
        with open(metrics_path, "r") as f:
            content = f.read()
        return content


if __name__ == "__main__":
    import asyncio

    tool = GetMetrics()
    print(asyncio.run(tool.run()))
