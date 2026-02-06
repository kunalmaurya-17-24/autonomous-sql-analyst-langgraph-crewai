import os
import uuid
import uvicorn
import asyncio
from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from LangGRAPH_SQL.graph_entry import sql_pipeline_app

# Load environment variables
load_dotenv()

app = FastAPI(title="LangGraph API Shim")

# In-memory storage for threads (since we are on a single container)
checkpointer = MemorySaver()
graph = sql_pipeline_app # Our compiled graph

class ThreadCreate(BaseModel):
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class RunCreate(BaseModel):
    assistant_id: str
    input: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    stream_mode: Optional[Union[str, List[str]]] = "values"

@app.get("/assistants")
async def list_assistants():
    """Mock the assistants list for the UI."""
    return [{
        "assistant_id": "finance",
        "graph_id": "finance",
        "name": "Autonomous SQL Analyst",
        "description": "Natural language SQL analyst for financial data."
    }]

@app.post("/threads")
async def create_thread(data: ThreadCreate):
    """Create a new thread ID."""
    thread_id = data.thread_id or str(uuid.uuid4())
    return {"thread_id": thread_id, "metadata": data.metadata or {}}

@app.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    """Retrieve the current state of a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    return {
        "values": state.values,
        "next": state.next,
        "config": config,
        "metadata": state.metadata,
        "created_at": None,
        "parent_config": state.parent_config
    }

@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, data: RunCreate):
    """
    Handle a new run request. 
    The Vercel UI expects a streaming response of LangGraph events.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    async def event_generator():
        # Map input to our graph's expected input (user_query)
        user_input = data.input or {}
        query = user_input.get("user_query") or user_input.get("query") or ""
        
        # Stream the results from the graph
        async for event in graph.astream(
            {"user_query": query}, 
            config=config, 
            stream_mode=data.stream_mode
        ):
            # Format the event for the LangGraph API spec
            # The UI usually looks for 'values' or 'messages'
            import json
            yield f"event: data\ndata: {json.dumps(event)}\n\n"
        
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "LangGraph Shim"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
