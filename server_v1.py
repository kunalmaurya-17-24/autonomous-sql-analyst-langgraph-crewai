import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from LangGRAPH_SQL.graph_entry import builder_final

app = FastAPI(title="Autonomous SQL Analyst API")

# Initialize the graph
graph = builder_final.compile()

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
