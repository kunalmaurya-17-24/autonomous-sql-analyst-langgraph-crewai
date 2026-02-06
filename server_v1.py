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

app = FastAPI(title="LangGraph API Shim (Lazy)")

# --- ADDED CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow your Vercel URL to talk to GCP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------

# Lazy-loaded graph
graph = None

def get_graph():
    global graph
    if graph is None:
        logger.info("Lazily initializing LangGraph...")
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
async def root():
    return {"status": "online", "message": "Server is up. Graph will load on first request."}

@app.get("/assistants")
async def list_assistants():
    return [{
        "assistant_id": "finance",
        "graph_id": "finance",
        "name": "Autonomous SQL Analyst",
        "description": "Natural language SQL analyst for financial data."
    }]

@app.post("/threads")
async def create_thread(data: ThreadCreate):
    thread_id = data.thread_id or str(uuid.uuid4())
    return {"thread_id": thread_id, "metadata": data.metadata or {}}

@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, data: RunCreate):
    try:
        active_graph = get_graph()
    except Exception as e:
        logger.error(f"Failed to load graph: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Graph initialization failed: {str(e)}")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    async def event_generator():
        user_input = data.input or {}
        query = user_input.get("user_query") or user_input.get("query") or ""
        async for event in active_graph.astream({"user_query": query}, config=config, stream_mode=data.stream_mode):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
