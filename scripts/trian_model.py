#!/usr/bin/env python3
"""
Train a new model using historical data and register with MLflow.
"""
import argparse
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import mlflow
import mlflow.sklearn
from cloud.model_registry.registry import ModelRegistry
import logging
import joblib

logging.basicConfig(level=logging.INFO)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to CSV with features and labels")
    parser.add_argument("--model-name", default="risk_model")
    parser.add_argument("--stage", default="Staging")
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    X = df.drop("label", axis=1)
    y = df["label"]

    model = RandomForestClassifier(n_estimators=100, max_depth=10)
    model.fit(X, y)

    # Save model locally
    joblib.dump(model, "model.pkl")

    # Register with MLflow
    registry = ModelRegistry()
    version = registry.register_model("model.pkl", args.model_name, stage=args.stage)
    print(f"Registered model version {version} as {args.stage}")

if __name__ == "__main__":
    main()
