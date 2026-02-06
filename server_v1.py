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
    return {"values": {}, "next": [], "metadata": {}, "created_at": "2024-01-01T00:00:00Z", "config": {}, "parent_config": {}}

@app.post("/threads/search")
async def search_threads(request: Request):
    """Dummy thread search."""
    return [{"thread_id": str(uuid.uuid4()), "metadata": {}, "created_at": "2024-01-01T00:00:00Z"}]

@app.get("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str):
    return []

@app.get("/threads/{thread_id}/runs")
async def list_runs(thread_id: str):
    return []

@app.post("/threads/{thread_id}/runs/wait")
async def wait_run(thread_id: str):
    return {}

@app.post("/threads/{thread_id}/runs")
@app.post("/threads/{thread_id}/runs/stream")
@app.post("/runs/stream")
async def create_run(thread_id: str = None, request: Request = None):
    """Streaming run execution for the premium UI."""
    # Log the raw request for debugging
    if request:
        body = await request.body()
        logger.info(f"Raw request body: {body.decode('utf-8')}")
        try:
            data_dict = json.loads(body.decode('utf-8'))
            logger.info(f"Parsed request: {data_dict}")
        except:
            data_dict = {}
    else:
        data_dict = {}
    
    try:
        active_graph = get_graph()
    except Exception as e:
        logger.error(f"Failed to load graph: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph initialization failed: {str(e)}")
    
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}
    
    async def event_generator():
        try:
            # Handle various input formats
            user_input = data_dict.get("input", {})
            query = ""
            
            # Try to extract the query from various formats
            if isinstance(user_input, dict):
                query = user_input.get("user_query") or user_input.get("query") or user_input.get("content") or ""
                # Check for messages array format
                messages = user_input.get("messages", [])
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict):
                        query = last_msg.get("content", query)
                    elif isinstance(last_msg, str):
                        query = last_msg
            elif isinstance(user_input, str):
                query = user_input
            
            # Also check if there's a direct "messages" field in the request
            if not query and "messages" in data_dict:
                messages = data_dict["messages"]
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict):
                        query = last_msg.get("content", "")
                    elif isinstance(last_msg, str):
                        query = last_msg
            
            logger.info(f"Processing query: '{query}'")
            
            stream_mode = data_dict.get("stream_mode", "values")
            
            async for event in active_graph.astream(
                {"user_query": query}, 
                config=config, 
                stream_mode=stream_mode
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
