"""
Prometheus metrics for monitoring.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import APIRouter, Response
import time
from functools import wraps

# Define metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
risk_score_histogram = Histogram('risk_score', 'Risk score distribution', ['level'])
trust_score_gauge = Gauge('trust_score', 'Current trust score for a session', ['session_id'])
active_sessions = Gauge('active_sessions', 'Number of active sessions')
telemetry_counter = Counter('telemetry_events_total', 'Total telemetry events ingested', ['endpoint'])
login_attempts_counter = Counter('login_attempts_total', 'Total login attempts', ['status'])
mfa_challenges_counter = Counter('mfa_challenges_total', 'Total MFA challenges', ['provider', 'status'])

metrics_router = APIRouter()

@metrics_router.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")

def monitor_request(func):
    """Decorator to monitor request count and duration."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        # In FastAPI, you'd use middleware instead of decorator for endpoint monitoring.
        # This is a placeholder for demonstration.
        result = await func(*args, **kwargs)
        duration = time.time() - start
        # You'd need to extract method/endpoint from request context
        return result
    return wrapper

def setup_metrics(app):
    """Add metrics middleware to FastAPI app."""
    from starlette.middleware.base import BaseHTTPMiddleware
    import time

    class MetricsMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            method = request.method
            path = request.url.path
            start_time = time.time()
            response = await call_next(request)
            duration = time.time() - start_time
            request_count.labels(method=method, endpoint=path, status=response.status_code).inc()
            request_duration.labels(method=method, endpoint=path).observe(duration)
            return response

    app.add_middleware(MetricsMiddleware)
