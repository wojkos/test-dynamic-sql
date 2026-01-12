FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for sqlite)
# RUN apt-get update && apt-get install -y --no-install-recommends ...

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports
# 8000: Main FastAPI App
# 8001: Internal MCP Server
EXPOSE 8000
EXPOSE 8001

# Make start script executable
RUN chmod +x start.sh

# Run the start script
CMD ["./start.sh"]
