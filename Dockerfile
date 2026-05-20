# Hugging Face Spaces Dockerfile for Graph RAG Resume Agent
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/tmp/huggingface
# API runs on localhost:8000, Gradio connects internally
ENV API_URL=http://localhost:8000

# Expose ports (FastAPI: 8000, Gradio: 7860)
EXPOSE 8000 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860')" || exit 1

# Run both FastAPI (background) and Gradio (foreground)
# FastAPI serves the knowledge graph queries
# Gradio provides the UI
CMD sh -c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 & python app_gradio.py"
