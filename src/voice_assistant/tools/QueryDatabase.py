import json
import os
import sqlite3

from agency_swarm.tools import BaseTool
from pydantic import Field

from voice_assistant.config import WORKSPACE_DIR


class QueryDatabase(BaseTool):
    """Run a read-only SQL query against the AIOS workspace database (data/data.db). Use for metrics, pipeline data, and business intelligence."""

    query: str = Field(
        ...,
        description="SQL SELECT query to run. Only SELECT statements are allowed. Tables include: ghl_pipeline_daily (date, pipeline_name, stage_name, count, total_value_gbp), ghl_activity_daily, fx_rates, collection_log, github_daily, github_repos, calendly_daily, calendly_events, xero_daily, gcal_daily, gcal_events, scorecard, meta_ads_daily. Example: SELECT SUM(total_value_gbp) as total FROM ghl_pipeline_daily WHERE date = (SELECT MAX(date) FROM ghl_pipeline_daily)",
    )

    async def run(self) -> str:
        if not WORKSPACE_DIR:
            return "WORKSPACE_DIR not configured. Set it in .env to enable workspace tools."
        db_path = os.path.join(WORKSPACE_DIR, "data", "data.db")
        if not os.path.exists(db_path):
            return "Database not found at data/data.db"
        query_upper = self.query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return "Only SELECT queries are allowed."
        if any(
            kw in query_upper
            for kw in ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"]
        ):
            return "Only SELECT queries are allowed. No modification statements."
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(self.query)
            rows = [dict(row) for row in cursor.fetchmany(50)]
            conn.close()
            if not rows:
                return "Query returned no results."
            return json.dumps(rows, indent=2, default=str)
        except Exception as e:
            return f"Query error: {str(e)}"


if __name__ == "__main__":
    import asyncio

    tool = QueryDatabase(query="SELECT name FROM sqlite_master WHERE type='table'")
    print(asyncio.run(tool.run()))
