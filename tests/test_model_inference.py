"""
Unit tests for model inference, uncertainty intervals, and risk classification logic.
"""

import os
import pytest
import numpy as np
import pandas as pd

from src.models.demand_model import RandomForestDemandForecaster, RidgeDemandRegressor
from src.models.risk_classifier import InventoryRiskEngine
from src.evaluate import ModelEvaluator

def test_wape_calculation():
    y_true = np.array([100, 200, 300])
    y_pred = np.array([110, 190, 300])
    # abs errors: 10 + 10 + 0 = 20. sum(y_true) = 600. wape = 20/600 = 0.0333...
    wape = ModelEvaluator.calculate_wape(y_true, y_pred)
    assert pytest.approx(wape, 0.001) == 20.0 / 600.0

def test_random_forest_forecaster_bounds():
    X = pd.DataFrame({
        "lag_1": [50, 60, 70, 80, 90],
        "rolling_4": [52, 58, 65, 75, 82]
    })
    y = pd.Series([55, 62, 72, 78, 88])

    rf = RandomForestDemandForecaster(n_estimators=10, max_depth=3, random_state=42)
    rf.fit(X, y)

    mean, lower, upper = rf.predict_with_uncertainty(X)
    assert len(mean) == len(X)
    assert (lower <= mean).all()
    assert (mean <= upper).all()
    assert (mean >= 0).all()

def test_inventory_risk_engine_triage():
    engine = InventoryRiskEngine(risk_horizon_days=60)
    
    # Critical risk case: 20 days to expiry with 300 units stock but only 10 units weekly demand
    batch_critical = {
        "Batch_ID": "BAT_CRIT_01",
        "Product_ID": "PROD_001",
        "Product_Name": "Amoxicillin",
        "Stock_Balance": 300,
        "Days_To_Expiry": 20,
        "Unit_Price": 10.0
    }
    result = engine.evaluate_batch(batch_critical, forecasted_weekly_demand=10.0)
    assert result["risk_tier"] in ["CRITICAL", "WARNING"]
    assert result["projected_waste_units"] > 200
    assert result["disclaimer"] != ""

    # Safe case: 120 days to expiry, fast moving
    batch_safe = {
        "Batch_ID": "BAT_SAFE_01",
        "Product_ID": "PROD_002",
        "Product_Name": "Metformin",
        "Stock_Balance": 50,
        "Days_To_Expiry": 120,
        "Unit_Price": 8.0
    }
    result_safe = engine.evaluate_batch(batch_safe, forecasted_weekly_demand=50.0)
    assert result_safe["risk_tier"] == "HEALTHY"
    assert result_safe["projected_waste_units"] == 0
