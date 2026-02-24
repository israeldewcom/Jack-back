#!/usr/bin/env python3
"""Monitor model performance and trigger alerts/retraining."""
import argparse
import requests
import json
import time
from cloud.engine.drift_detector import DriftDetector
from cloud.model_registry.monitoring import ModelMonitor
from cloud.observability.logging import setup_logging

logger = setup_logging()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--threshold", type=float, default=0.1)
    args = parser.parse_args()

    monitor = ModelMonitor(args.model_name)
    while True:
        metrics = monitor.collect_live_metrics()
        drift = monitor.detect_drift(metrics, threshold=args.threshold)
        if drift:
            logger.warning(f"Drift detected for {args.model_name}: {drift}")
            # Trigger alert (PagerDuty, Slack)
            requests.post(os.getenv("SLACK_WEBHOOK"), json={"text": f"Model {args.model_name} drifted!"})
            # Optionally auto-retrain
            if os.getenv("AUTO_RETRAIN") == "true":
                subprocess.run(["python", "scripts/train_model.py", "--model-name", args.model_name])
        time.sleep(3600)  # check every hour

if __name__ == "__main__":
    main()
