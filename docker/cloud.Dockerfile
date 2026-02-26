FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cloud/ ./cloud/
COPY scripts/ ./scripts/

ENV PYTHONPATH=/app

CMD ["uvicorn", "cloud.main:app", "--host", "0.0.0.0", "--port", "8000"]
