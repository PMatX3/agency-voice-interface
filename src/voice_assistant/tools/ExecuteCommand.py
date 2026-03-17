import asyncio
import os

from agency_swarm.tools import BaseTool
from pydantic import Field

from voice_assistant.config import WORKSPACE_DIR

ALLOWED_SCRIPTS = {
    "collect": "scripts/collect.py",
    "generate_metrics": "scripts/generate_metrics.py",
    "push_scorecard": "scripts/push_scorecard.py",
    "push_pipeline": "scripts/push_pipeline_to_ghl.py",
}


class ExecuteCommand(BaseTool):
    """Run a whitelisted AIOS workspace script. Available commands: collect, generate_metrics, push_scorecard, push_pipeline."""

    command: str = Field(
        ...,
        description=f"Command to run. Options: {', '.join(ALLOWED_SCRIPTS.keys())}",
    )
    args: str = Field(
        default="", description="Optional arguments to pass to the script"
    )

    async def run(self) -> str:
        if not WORKSPACE_DIR:
            return "WORKSPACE_DIR not configured. Set it in .env to enable workspace tools."
        if self.command not in ALLOWED_SCRIPTS:
            return f"Unknown command '{self.command}'. Available: {', '.join(ALLOWED_SCRIPTS.keys())}"
        script_path = os.path.join(WORKSPACE_DIR, ALLOWED_SCRIPTS[self.command])
        venv_python = os.path.join(WORKSPACE_DIR, ".venv", "bin", "python")
        if not os.path.exists(script_path):
            return f"Script not found: {ALLOWED_SCRIPTS[self.command]}"
        cmd = [venv_python, script_path]
        if self.args:
            cmd.extend(self.args.split())
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
                    f"Command '{self.command}' completed. {output[-500:]}"
                    if output
                    else f"Command '{self.command}' completed successfully."
                )
            else:
                error = stderr.decode().strip()
                return f"Command '{self.command}' failed: {error[-300:]}"
        except asyncio.TimeoutError:
            return f"Command '{self.command}' timed out after 120 seconds."


if __name__ == "__main__":
    tool = ExecuteCommand(command="generate_metrics")
    print(asyncio.run(tool.run()))
