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

# Ensure the database and logs directory exist with right permissions
RUN mkdir -p logs

# Expose port (Cloud Run uses PORT env var, default to 8080)
EXPOSE 8080

# Run the FastAPI shim
CMD ["python", "server_v1.py"]
