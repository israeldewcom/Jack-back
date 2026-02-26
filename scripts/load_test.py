#!/usr/bin/env python3
"""
Locust load test for the ingest endpoint.
"""
from locust import HttpUser, task, between
import random
from datetime import datetime

class TelemetryUser(HttpUser):
    wait_time = between(0.5, 2)

    @task
    def send_telemetry(self):
        now = datetime.utcnow().isoformat()
        payload = {
            "session_id": f"session_{random.randint(1,10000)}",
            "user_id": f"user_{random.randint(1,1000)}",
            "ip": f"192.168.{random.randint(1,254)}.{random.randint(1,254)}",
            "keystroke_speed": random.uniform(1, 10),
            "mouse_speed": random.uniform(1, 10),
            "timestamp": now,
            "device": "desktop",
            "role": "standard"
        }
        self.client.post("/v2/telemetry", json=payload)
