#!/usr/bin/env python3
"""
Recompute features and optionally retrain models on historical data.
"""
import argparse
import pandas as pd
from sqlalchemy import create_engine
from cloud.feature_store.feature_store import FeatureStore
from cloud.model_registry.registry import ModelRegistry
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--retrain", action="store_true")
    args = parser.parse_args()

    engine = create_engine("postgresql://user:pass@db/citp")  # Use env var
    feature_store = FeatureStore("postgresql://user:pass@db/citp")

    # Load historical telemetry
    query = f"SELECT * FROM telemetry WHERE timestamp BETWEEN '{args.start_date}' AND '{args.end_date}'"
    df = pd.read_sql(query, engine)

    # For each user, recompute aggregates (feature store has method)
    # This is a placeholder; actual backfill would call precompute_aggregates
    feature_store.precompute_aggregates(
        datetime.fromisoformat(args.start_date),
        datetime.fromisoformat(args.end_date)
    )

    if args.retrain:
        # Load features and labels, train model
        from sklearn.ensemble import RandomForestClassifier
        # ... training code ...
        registry = ModelRegistry()
        registry.register_model("./model.pkl", "risk_model", stage="Staging")

if __name__ == "__main__":
    main()
