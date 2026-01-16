import os
import sys
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

# Ensure LangGRAPH_SQL is in the path for imports
# This assumes the project structure:
# e:\sql_crew\
#    ├── CrewAI\
#    │   └── sql_tools.py
#    └── LangGRAPH_SQL\
#        └── graph_entry.py

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from LangGRAPH_SQL.graph_entry import run_sql_pipeline

class SQLToolInput(BaseModel):
    """Input for the SQLTool."""
    query: str = Field(..., description="The natural language question to ask the database.")

# Failure Counter
FAIL_COUNT = 0

class LangGraphSQLTool(BaseTool):
    name: str = "Ask_Company_Database"
    description: str = (
        "Useful for when you need to answer questions about sales, users, or revenue from the company database. "
        "Input should be a specific natural language question like 'What was the churn rate last week?'"
    )
    args_schema: Type[BaseModel] = SQLToolInput

    def _run(self, query: str) -> str:
        global FAIL_COUNT
        
        # 0. Safety Check
        if FAIL_COUNT >= 3:
            return "STOP: The SQL Agent has failed 3 consecutive times. Aborting to save API credits. Please check logs."

        # 1. Call the deterministic LangGraph pipeline (which now executes the SQL)
        print(f"\n[Tool] Activating Safe SQL Executor for query: '{query}'")
        data_result = run_sql_pipeline(query)
        
        # 2. Check for failure
        if "Error" in data_result or "Failed" in data_result or "No results" in data_result:
            FAIL_COUNT += 1
            if FAIL_COUNT >= 3:
                 return f"Database Results:\n\n{data_result}\n\n[SYSTEM]: Critical Failure Limit Reached ({FAIL_COUNT}/3). Stopping."
        else:
             # Reset on success
             FAIL_COUNT = 0
        
        # 3. Return the formatted data (Markdown table)
        return f"Database Results:\n\n{data_result}"

# For standalone testing
if __name__ == "__main__":
    tool = LangGraphSQLTool()
    print(tool._run("Show me all active users"))
