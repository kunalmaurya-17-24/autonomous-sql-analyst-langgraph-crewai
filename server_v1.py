import os
import uuid
import uvicorn
import asyncio
import logging
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

app = FastAPI(title="LangGraph Premium Shim")

# CORS Setup - Essential for Vercel -> GCP connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-loaded graph
graph = None

def get_graph():
    global graph
    if graph is None:
        logger.info("Lazily initializing LangGraph brain...")
        from LangGRAPH_SQL.graph_entry import sql_pipeline_app
        graph = sql_pipeline_app
        logger.info("Graph initialized successfully.")
    return graph

class ThreadCreate(BaseModel):
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class RunCreate(BaseModel):
    assistant_id: str
    input: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    stream_mode: Optional[Union[str, List[str]]] = "values"

@app.get("/")
@app.get("/info")
async def get_info():
    """Official LangGraph /info endpoint."""
    return {
        "version": "0.1.0",
        "service": "langgraph-platform",
        "config": {}
    }

@app.get("/assistants")
async def list_assistants():
    """Official LangGraph /assistants list endpoint."""
    return [{
        "assistant_id": "finance",
        "graph_id": "finance",
        "config": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "metadata": {},
        "name": "Autonomous SQL Analyst"
    }]

@app.get("/assistants/finance")
@app.get("/assistants/{assistant_id}")
async def get_assistant(assistant_id: str):
    """Specific assistant profile retrieval."""
    return {
        "assistant_id": "finance",
        "graph_id": "finance",
        "config": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "metadata": {},
        "name": "Autonomous SQL Analyst"
    }

@app.post("/threads")
async def create_thread(data: ThreadCreate):
    """Thread creation for persistent sessions."""
    thread_id = data.thread_id or str(uuid.uuid4())
    return {"thread_id": thread_id, "metadata": data.metadata or {}}

@app.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    """Retrieve state - dummy response for now to satisfy UI."""
    return {"values": {}, "next": []}

@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, data: RunCreate):
    """Streaming run execution for the premium UI."""
    try:
        active_graph = get_graph()
    except Exception as e:
        logger.error(f"Failed to load graph: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph initialization failed: {str(e)}")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    async def event_generator():
        try:
            user_input = data.input or {}
            query = user_input.get("user_query") or user_input.get("query") or ""
            
            # The UI often expects 'event: data' then 'data: JSON' for SSE
            async for event in active_graph.astream(
                {"user_query": query}, 
                config=config, 
                stream_mode=data.stream_mode
            ):
                yield f"event: data\ndata: {json.dumps(event)}\n\n"
            
            yield "event: end\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Standard Uvicorn startup
    uvicorn.run(app, host="0.0.0.0", port=port)
