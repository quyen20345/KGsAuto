# Dockerfile for the backend service
# This Dockerfile sets up a Python environment with necessary dependencies for the backend application.
# It uses a slim Python image to reduce the size of the final image.
FROM python:3.12-slim

# Disable interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory backend
WORKDIR /app 

# Install system packages required by Python extensions
RUN apt-get update && apt-get install -y \
    curl git wget unzip nano vim libgl1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies for caching
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . ./

# Expose port
EXPOSE 8000

# Launch with auto-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]