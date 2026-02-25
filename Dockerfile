# Stage 1: Builder – install dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Install system build dependencies (only needed for compiling some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install a known good matplotlib version first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir "matplotlib>=3.5.0"

# Copy requirements and install all dependencies into a local directory
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.11-slim

# Create a non-root user to run the app
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

WORKDIR /app

# Copy installed packages from builder with correct ownership
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Set environment variables so Python finds the user-installed packages
ENV PYTHONUSERBASE=/home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

# Expose the port the app runs on (Render will set PORT env variable)
EXPOSE $PORT

# Health check (ensure your FastAPI app has a /health endpoint)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:$PORT/health')" || exit 1

# Run the FastAPI app with uvicorn, binding to $PORT
CMD uvicorn cloud.api.main:app --host 0.0.0.0 --port $PORT
