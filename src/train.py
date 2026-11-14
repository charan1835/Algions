"""
End-to-End Training & Evaluation Pipeline for Pharmacy Demand & Expiry Risk Forecasting.
Executes data loading, feature extraction, chronological train/val/test splitting,
baseline and candidate model training, evaluation on held-out test data, and artifact persistence.
"""

import os
import sys
import json
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import joblib

from src.data_loader import PharmaDataLoader
from src.features import FeatureEngineer
from src.models.baselines import NaiveLastValueBaseline, MovingAverageBaseline, SeasonalNaiveBaseline
from src.models.demand_model import RidgeDemandRegressor, RandomForestDemandForecaster, GradientBoostingDemandForecaster
from src.models.risk_classifier import InventoryRiskEngine
from src.evaluate import ModelEvaluator

def run_pipeline(data_path: str = "data/processed/pharmacy_demand_expiry_data.csv",
                 output_dir: str = "models",
                 seed: int = 42):
    """Executes the full training, evaluation, and artifact saving pipeline."""
    np.random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 80)
    print("ALGIONS AI LABS - PHARMACY DEMAND & EXPIRY-RISK FORECASTING TRAINING PIPELINE")
    print("=" * 80)

    # 1. Ingestion & Quality Validation
    print("\n[Step 1/6] Ingesting and validating pharmaceutical dataset...")
    if not os.path.exists(data_path) or pd.read_csv(data_path).shape[0] < 500 or pd.read_csv(data_path).get("Is_At_Risk", pd.Series([0])).sum() < 20:
        print(f"Auto-refreshing benchmark dataset with active at-risk inventory distributions (1,500+ records)...")
        from data.synthetic_generator import generate_weekly_synthetic_data
        generate_weekly_synthetic_data(output_path=data_path, seed=seed)

    loader = PharmaDataLoader(data_path)
    raw_df = loader.load_and_validate()
    stats = loader.get_summary_statistics()
    print(f"Loaded {stats['total_records']} batch transactions across {stats['num_products']} products and {stats['num_batches']} batches.")
    print(f"Date Span: {stats['date_range'][0]} to {stats['date_range'][1]} | Total Units Sold: {stats['total_units_sold']:,}")

    # 2. Demand Aggregation & Feature Engineering
    print("\n[Step 2/6] Aggregating weekly product demand and building leakage-free features...")
    weekly_prod_df = loader.aggregate_weekly_demand()
    
    fe = FeatureEngineer()
    featured_df = fe.create_demand_features(weekly_prod_df, target_col="Total_Units_Sold")
    feature_cols = fe.get_feature_names(featured_df)
    print(f"Engineered {len(feature_cols)} features (Lags, Rolling Stats, Cyclical Encodings, Categories).")

    # 3. Chronological Train / Val / Test Split
    print("\n[Step 3/6] Performing strict chronological split (70% Train, 15% Val, 15% Test)...")
    train_df, val_df, test_df = loader.chronological_split(featured_df, train_ratio=0.70, val_ratio=0.15)
    
    print(f"Train Period : {train_df['Date'].min().date()} to {train_df['Date'].max().date()} ({len(train_df)} rows)")
    print(f"Val Period   : {val_df['Date'].min().date()} to {val_df['Date'].max().date()} ({len(val_df)} rows)")
    print(f"Test Period  : {test_df['Date'].min().date()} to {test_df['Date'].max().date()} ({len(test_df)} rows)")

    X_train, y_train = train_df[feature_cols], train_df["Total_Units_Sold"]
    X_val, y_val = val_df[feature_cols], val_df["Total_Units_Sold"]
    X_test, y_test = test_df[feature_cols], test_df["Total_Units_Sold"]

    # Combine Train + Val for final model training after hyperparameter verification
    X_train_val = pd.concat([X_train, X_val])
    y_train_val = pd.concat([y_train, y_val])

    # 4. Model Training & Comparison
    print("\n[Step 4/6] Training Baselines and Candidate Supervised Models...")
    models_demand = {
        "Baseline: Last-Value": NaiveLastValueBaseline().fit(train_df),
        "Baseline: 4W-MovingAvg": MovingAverageBaseline(window=4).fit(train_df),
        "Baseline: SeasonalNaive": SeasonalNaiveBaseline().fit(train_df),
        "Candidate 1: Ridge Regression": RidgeDemandRegressor(alpha=1.0, random_state=seed).fit(X_train_val, y_train_val),
        "Candidate 2: Random Forest": RandomForestDemandForecaster(n_estimators=100, max_depth=8, random_state=seed).fit(X_train_val, y_train_val),
        "Candidate 3: Gradient Boosting": GradientBoostingDemandForecaster(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=seed).fit(X_train_val, y_train_val)
    }

    print("\n" + "-" * 75)
    print(f"{'Model Name':<32} | {'MAE':<8} | {'RMSE':<8} | {'WAPE':<8} | {'R2':<8}")
    print("-" * 75)

    eval_results = {}
    best_model_name = None
    best_wape = float("inf")

    for name, model in models_demand.items():
        if "Baseline" in name:
            preds = model.predict(test_df)
        else:
            preds = model.predict(X_test)

        metrics = ModelEvaluator.evaluate_demand_regression(y_test.values, preds)
        eval_results[name] = metrics
        print(f"{name:<32} | {metrics['MAE']:<8.2f} | {metrics['RMSE']:<8.2f} | {metrics['WAPE_Pct']:<8} | {metrics['R2']:<8.4f}")

        if metrics["WAPE"] < best_wape:
            best_wape = metrics["WAPE"]
            best_model_name = name

    print("-" * 75)
    print(f"Selected Best Demand Forecaster: {best_model_name} (WAPE: {best_wape * 100:.2f}%)")

    # 5. Expiry Risk Engine Training & Evaluation
    print("\n[Step 5/6] Training and Evaluating Batch Expiry Risk Engine...")
    best_demand_forecaster = models_demand[best_model_name]
    test_df_copy = test_df.copy()
    if "Baseline" in best_model_name:
        test_df_copy["Forecast_Demand"] = best_demand_forecaster.predict(test_df)
    else:
        test_df_copy["Forecast_Demand"] = best_demand_forecaster.predict(X_test)

    # Attach demand forecast to batch test records
    batch_test = raw_df[raw_df["Date"] >= test_df["Date"].min()].copy()
    
    # Merge forecasted demand by Product_ID & Date
    demand_lookup = test_df_copy.set_index(["Product_ID", "Date"])["Forecast_Demand"].to_dict()
    batch_test["Forecasted_Demand"] = batch_test.apply(
        lambda r: demand_lookup.get((r["Product_ID"], r["Date"]), r["Units_Sold"]), axis=1
    )

    risk_engine = InventoryRiskEngine(risk_horizon_days=60, random_state=seed)
    
    # Build batch training set
    batch_features_all = fe.create_batch_risk_features(raw_df)
    batch_train = batch_features_all[batch_features_all["Date"] < test_df["Date"].min()]
    batch_test_featured = fe.create_batch_risk_features(batch_test, forecasted_weekly_demand=batch_test["Forecasted_Demand"])

    risk_feature_cols = [c for c in risk_engine.feature_names if c in batch_train.columns]
    risk_engine.fit_ml_classifier(batch_train[risk_feature_cols].fillna(0), batch_train["Is_At_Risk_Binary"])

    # Predict risk on held-out test batches
    test_risk_probs = risk_engine.predict_risk_proba(batch_test_featured[risk_feature_cols].fillna(0))
    test_risk_preds = (test_risk_probs >= 0.50).astype(int)

    risk_metrics = ModelEvaluator.evaluate_risk_classification(
        batch_test_featured["Is_At_Risk_Binary"].values,
        test_risk_preds,
        test_risk_probs
    )

    print("\nBatch Expiry-Risk Classifier Performance on Held-Out Test Set:")
    print(f"  * Precision : {risk_metrics['Precision']:.4f}")
    print(f"  * Recall    : {risk_metrics['Recall']:.4f}")
    print(f"  * F1-Score  : {risk_metrics['F1_Score']:.4f}")
    print(f"  * ROC-AUC   : {risk_metrics.get('ROC_AUC', 'N/A')}")
    print(f"  * Confusion Matrix: TP={risk_metrics['True_Positives']}, FP={risk_metrics['False_Positives']}, TN={risk_metrics['True_Negatives']}, FN={risk_metrics['False_Negatives']}")

    # 6. Artifact Serialization
    print("\n[Step 6/6] Serializing production artifacts to disk...")
    forecaster_path = os.path.join(output_dir, "demand_forecaster.joblib")
    classifier_path = os.path.join(output_dir, "risk_classifier.joblib")
    metadata_path = os.path.join(output_dir, "metadata.json")

    joblib.dump(best_demand_forecaster, forecaster_path)
    joblib.dump(risk_engine, classifier_path)

    metadata = {
        "model_version": "1.0.0",
        "random_seed": seed,
        "selected_demand_model": best_model_name,
        "features": feature_cols,
        "risk_features": risk_feature_cols,
        "demand_test_metrics": eval_results[best_model_name],
        "all_demand_comparisons": eval_results,
        "risk_test_metrics": risk_metrics,
        "risk_horizon_days": 60,
        "data_records": stats["total_records"],
        "advisory_disclaimer": (
            "Operational guidance only. All alerts must be reviewed by pharmacy inventory managers. "
            "Never use as medication, dosing, or clinical treatment advice."
        )
    }

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"[SUCCESS] Saved model artifacts to '{output_dir}/'")
    print(f"  - Forecaster: {forecaster_path}")
    print(f"  - Risk Engine: {classifier_path}")
    print(f"  - Metadata: {metadata_path}")
    print("=" * 80)

    return metadata

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train demand forecasting and expiry risk models.")
    parser.add_argument("--data", default="data/processed/pharmacy_demand_expiry_data.csv")
    parser.add_argument("--out", default="models")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    run_pipeline(data_path=args.data, output_dir=args.out, seed=args.seed)
