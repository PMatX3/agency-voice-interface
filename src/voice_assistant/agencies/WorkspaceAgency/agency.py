from agency_swarm import Agency

from .WorkspaceManager.WorkspaceManager import WorkspaceManager


def create_agency():
    workspace_manager = WorkspaceManager()

    agency = Agency(
        [workspace_manager],
        shared_instructions="agency_manifesto.md",
        temperature=0.0,
        max_prompt_tokens=25000,
        async_mode="threading",
    )

    return agency


agency = create_agency()
