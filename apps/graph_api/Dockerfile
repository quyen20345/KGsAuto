# Dockerfile for the Graph API service
# This Dockerfile sets up a Python environment with necessary dependencies for the graph API application.
# It uses a slim Python image to reduce the size of the final image.
FROM python:3.12-slim

# Disable interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app 

# Install system packages required by Python extensions
RUN apt-get update && apt-get install -y \
    curl git wget unzip nano vim libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Build this image from the repo root:
# docker build -f apps/graph_api/Dockerfile .
# Copy and install root Python dependencies for caching
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . ./

# Expose port
EXPOSE 8000

# Launch with auto-reload for development
CMD ["uvicorn", "apps.graph_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
