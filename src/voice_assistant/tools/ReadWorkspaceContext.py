import os

from agency_swarm.tools import BaseTool
from pydantic import Field

from voice_assistant.config import WORKSPACE_DIR


class ReadWorkspaceContext(BaseTool):
    """Read a file from the AIOS workspace context, outputs, or reference directories."""

    file_path: str = Field(
        ...,
        description="Relative path within the workspace. Examples: 'context/strategy.md', 'outputs/project-register.md', 'context/group/key-metrics.md'",
    )

    async def run(self) -> str:
        if not WORKSPACE_DIR:
            return "WORKSPACE_DIR not configured. Set it in .env to enable workspace tools."
        full_path = os.path.join(WORKSPACE_DIR, self.file_path)
        allowed_dirs = ["context/", "outputs/", "reference/", "plans/", "artifacts/"]
        if not any(self.file_path.startswith(d) for d in allowed_dirs):
            return f"Access denied. Only these directories are readable: {', '.join(allowed_dirs)}"
        if not os.path.exists(full_path):
            return f"File not found: {self.file_path}"
        with open(full_path, "r") as f:
            content = f.read()
        if len(content) > 4000:
            content = content[:4000] + "\n\n[Content truncated for voice output]"
        return content


if __name__ == "__main__":
    import asyncio

    tool = ReadWorkspaceContext(file_path="context/group/key-metrics.md")
    print(asyncio.run(tool.run()))
