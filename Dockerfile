FROM python:3.11-slim

# Install system build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libfreetype6-dev \
    libpng-dev \
    pkg-config \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and set HTTPS index
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip config set global.index-url https://pypi.org/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ... rest of your Dockerfile
