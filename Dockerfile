FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir langgraph-cli uvicorn

# Copy project files
COPY . .

# Ensure the database and KB are present (we bundle them for V1)
# These should already exist in e:\sql_crew
# finance.db
# LangGRAPH_SQL/kb.pkl

# Expose port (Cloud Run uses PORT env var, default to 8080)
EXPOSE 8080

# Command to run the LangGraph server
# We use langgraph dev or langgraph deploy style; for Cloud Run we'll use uvicorn to serve the API
CMD ["langgraph", "up", "--host", "0.0.0.0", "--port", "8080"]
