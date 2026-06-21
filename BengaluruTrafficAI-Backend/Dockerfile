# BengaluruTrafficAI — Railway Deployment
FROM python:3.11-slim

WORKDIR /app

# Install OpenCV dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p output/evidence uploads

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Start command
CMD uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8000}
