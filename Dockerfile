# Use Python 3.11 slim image for stability and compatibility
FROM python:3.11-slim

# Set working directory to match Render's path
WORKDIR /opt/render/project/src

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MODEL_PATH=/opt/render/project/src/models/phi-2.Q4_K_M.gguf

# Install system dependencies needed for building packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create models directory and download model during build
RUN mkdir -p /opt/render/project/src/models

# Copy application code
COPY . .

# Create a non-root user to run the app
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /opt/render/project/src

# Run model download script as root before switching user
RUN python download_model.py

# Switch to non-root user
USER appuser

# Expose port (Render will set PORT env variable)
EXPOSE ${PORT}

# Health check using Python
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:' + str($PORT) + '/health')" || exit 1

# Create volume for model persistence
VOLUME ["/opt/render/project/src/models"]

# Start the application
CMD ["sh", "-c", "python download_model.py && uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 2"]