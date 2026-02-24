#!/usr/bin/env python3
"""Run chaos experiments using Chaos Toolkit."""
import subprocess
import json
import sys

def run_experiment(experiment_file):
    result = subprocess.run(["chaos", "run", experiment_file], capture_output=True)
    if result.returncode != 0:
        print(f"Experiment failed: {result.stderr}")
        sys.exit(1)
    else:
        print("Experiment succeeded")
        # Parse journal
        with open("chaos-results.json") as f:
            journal = json.load(f)
        return journal

if __name__ == "__main__":
    run_experiment("docker/chaos/network_delay.json")
