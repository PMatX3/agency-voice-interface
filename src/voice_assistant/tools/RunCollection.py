import asyncio
import os

from agency_swarm.tools import BaseTool
from pydantic import Field

from voice_assistant.config import WORKSPACE_DIR


class RunCollection(BaseTool):
    """Trigger the AIOS data collection pipeline to refresh business metrics from all connected sources."""

    sources: str = Field(
        default="",
        description="Optional: comma-separated list of sources to collect (e.g. 'ghl,github'). Leave empty for all sources.",
    )

    async def run(self) -> str:
        if not WORKSPACE_DIR:
            return "WORKSPACE_DIR not configured. Set it in .env to enable workspace tools."
        venv_python = os.path.join(WORKSPACE_DIR, ".venv", "bin", "python")
        collect_script = os.path.join(WORKSPACE_DIR, "scripts", "collect.py")
        if not os.path.exists(venv_python):
            return "Python venv not found at .venv/bin/python"
        if not os.path.exists(collect_script):
            return "Collection script not found at scripts/collect.py"
        cmd = [venv_python, collect_script]
        if self.sources:
            cmd.extend(["--sources", self.sources])
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=WORKSPACE_DIR,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=120
            )
            output = stdout.decode().strip()
            if process.returncode == 0:
                return (
                    f"Collection complete. {output[-500:]}"
                    if len(output) > 500
                    else f"Collection complete. {output}"
                )
            else:
                error = stderr.decode().strip()
                return f"Collection failed (exit {process.returncode}): {error[-300:]}"
        except asyncio.TimeoutError:
            return "Collection timed out after 120 seconds."
        except Exception as e:
            return f"Collection error: {str(e)}"


if __name__ == "__main__":
    tool = RunCollection()
    print(asyncio.run(tool.run()))
