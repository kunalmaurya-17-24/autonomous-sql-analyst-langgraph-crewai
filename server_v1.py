import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Autonomous SQL Analyst API")

# Initialize the graph with logging
try:
    print("Initializing LangGraph...")
    from LangGRAPH_SQL.graph_entry import builder_final
    graph = builder_final.compile()
    print("Graph compiled successfully.")
except Exception as e:
    print(f"CRITICAL: Failed to compile graph: {str(e)}")
    # We allow the app to start so the container doesn't crash, 
    # but we'll return errors on requests.
    graph = None

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    status: str
    result: Any

@app.get("/")
async def root():
    return {"status": "online", "message": "Autonomous SQL Analyst API is running."}

@app.post("/api/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    if graph is None:
        raise HTTPException(status_code=500, detail="Graph failed to initialize. Check server logs.")
    try:
        # Run the graph with the user query
        inputs = {"query": request.query}
        result = graph.invoke(inputs)
        
        return QueryResponse(
            status="success",
            result=result
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Cloud Run provides the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
