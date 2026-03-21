import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build

load_dotenv()

logger = logging.getLogger(__name__)


class GoogleServicesUtils:
    """
    Utility class for Gmail and Google Calendar authentication and service creation.

    Calendar: uses service account with domain-wide delegation.
    Gmail: uses OAuth2 credentials from ~/.gmail-mcp/.
    """

    SERVICE_API_VERSIONS = {"gmail": "v1", "calendar": "v3"}

    @staticmethod
    async def authenticate_service(service_name):
        """
        Authenticates and returns a Gmail or Google Calendar service object.
        """

        def authenticate():
            if service_name == "calendar":
                return GoogleServicesUtils._build_calendar_service()
            elif service_name == "gmail":
                return GoogleServicesUtils._build_gmail_service()
            else:
                raise ValueError(f"Unsupported service: {service_name}")

        try:
            service = await asyncio.to_thread(authenticate)
            logger.info(
                f"{service_name.capitalize()} service authenticated successfully."
            )
            return service
        except Exception as e:
            logger.error(f"Failed to authenticate {service_name} service: {e}")
            raise e

    @staticmethod
    def _build_calendar_service():
        """Build Calendar service using service account with domain-wide delegation."""
        workspace_dir = os.getenv("WORKSPACE_DIR", "")
        sa_path = os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_JSON",
            os.path.join(workspace_dir, "credentials", "google-service-account.json"),
        )

        # Resolve relative paths against workspace dir
        full_path = Path(sa_path)
        if not full_path.is_absolute() and workspace_dir:
            full_path = Path(workspace_dir) / sa_path

        if not full_path.exists():
            raise FileNotFoundError(
                f"Service account JSON not found at {full_path}. "
                "Set GOOGLE_SERVICE_ACCOUNT_JSON or WORKSPACE_DIR in .env"
            )

        calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "").strip()

        creds = ServiceAccountCredentials.from_service_account_file(
            str(full_path),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )

        # Use domain-wide delegation to impersonate the calendar owner
        if calendar_id and calendar_id != "primary" and "@" in calendar_id:
            creds = creds.with_subject(calendar_id)

        logger.info(f"Calendar service built with service account, calendar_id={calendar_id}")
        return build("calendar", "v3", credentials=creds)

    @staticmethod
    def _build_gmail_service():
        """Build Gmail service using OAuth2 credentials from ~/.gmail-mcp/."""
        gmail_dir = Path.home() / ".gmail-mcp"
        oauth_keys_path = gmail_dir / "gcp-oauth.keys.json"
        credentials_path = gmail_dir / "credentials.json"

        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Gmail credentials not found at {credentials_path}. "
                "Run the Gmail MCP auth flow first."
            )
        if not oauth_keys_path.exists():
            raise FileNotFoundError(
                f"Gmail OAuth keys not found at {oauth_keys_path}. "
                "Place your GCP OAuth client keys in ~/.gmail-mcp/"
            )

        with open(credentials_path) as f:
            token_data = json.load(f)
        with open(oauth_keys_path) as f:
            oauth_keys = json.load(f)

        key_data = oauth_keys.get("installed") or oauth_keys.get("web")

        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=key_data["client_id"],
            client_secret=key_data["client_secret"],
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.compose",
            ],
        )

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail credentials.")
            creds.refresh(Request())
            # Save refreshed token back
            token_data["access_token"] = creds.token
            with open(credentials_path, "w") as f:
                json.dump(token_data, f)
            logger.info("Saved refreshed Gmail token.")

        logger.info("Gmail service built with OAuth2 credentials.")
        return build("gmail", "v1", credentials=creds)

    @staticmethod
    async def authenticate_gmail():
        return await GoogleServicesUtils.authenticate_service("gmail")

    @staticmethod
    async def authenticate_calendar():
        return await GoogleServicesUtils.authenticate_service("calendar")
