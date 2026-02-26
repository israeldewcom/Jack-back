#!/usr/bin/env python3
import requests
import sys
import os

def check_service(url, name):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            print(f"{name}: OK")
            return True
        else:
            print(f"{name}: ERROR (status {r.status_code})")
            return False
    except Exception as e:
        print(f"{name}: ERROR ({e})")
        return False

def main():
    services = [
        ("edge", os.getenv("EDGE_HEALTH_URL", "http://edge:8000/health")),
        ("cloud", os.getenv("CLOUD_HEALTH_URL", "http://cloud:8000/health")),
        ("db", os.getenv("DB_HEALTH_URL", "http://db:5432")),  # TCP check would be better
        ("redis", os.getenv("REDIS_HEALTH_URL", "redis://redis:6379")),
        ("kafka", os.getenv("KAFKA_HEALTH_URL", "http://kafka:9092")),
        ("mlflow", os.getenv("MLFLOW_HEALTH_URL", "http://mlflow:5000"))
    ]
    all_ok = True
    for name, url in services:
        ok = check_service(url, name)
        if not ok:
            all_ok = False
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
