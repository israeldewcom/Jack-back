# Use an official Python 3.11 slim image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system build dependencies required by Python packages like matplotlib, numpy, etc.
# This avoids many common compilation errors.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Command to run your application.
# **IMPORTANT**: Replace `cloud.api.main:app` with the correct import path for your FastAPI app.
# The port `10000` is Render's default, but you can also use the `$PORT` environment variable.
CMD ["uvicorn", "cloud.api.main:app", "--host", "0.0.0.0", "--port", "10000"]
