# BengaluruTrafficAI — Docker Image
# Multi-stage build for optimized image size

# Stage 1: Base with Python and system dependencies
FROM python:3.11-slim as base

# Install system dependencies for OpenCV and other libraries
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgthread-2.0-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Stage 2: Install Python dependencies
FROM base as dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Application
FROM dependencies as application

# Copy application code
COPY . .

# Create output directories
RUN mkdir -p output/evidence

# Download YOLOv8 model if not present
RUN python -c "from ultralytics import YOLO; YOLO('yolov8s.pt')" || true

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/')" || exit 1

# Default command: run API server
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
