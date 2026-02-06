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

# Copy project files
COPY . .

# Expose port
EXPOSE 8080

# Run the official LangGraph server in dev mode 
# This provides the exact API endpoints the Vercel UI expects
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "8080"]
