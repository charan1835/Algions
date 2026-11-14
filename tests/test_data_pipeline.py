"""
Unit tests for data loader, quality assertions, and anti-leakage splitting.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.data_loader import PharmaDataLoader
from src.features import FeatureEngineer

@pytest.fixture
def sample_raw_data(tmp_path):
    """Creates a temporary valid CSV dataset for testing."""
    dates = [datetime(2024, 1, 1) + timedelta(weeks=i) for i in range(20)]
    rows = []
    for d in dates:
        rows.append({
            "Date": d.strftime("%Y-%m-%d"),
            "Product_ID": "PROD_001",
            "Product_Name": "Amoxicillin 500mg",
            "Category": "Antibiotic",
            "Batch_ID": "BAT_001_101",
            "Manufacture_Date": "2024-01-01",
            "Expiry_Date": "2024-12-31",
            "Initial_Stock": 500,
            "Units_Sold": 25,
            "Stock_Balance": 400,
            "Days_To_Expiry": (datetime(2024, 12, 31) - d).days
        })
    df = pd.DataFrame(rows)
    csv_file = tmp_path / "test_pharma.csv"
    df.to_csv(csv_file, index=False)
    return str(csv_file)

def test_loader_schema_and_types(sample_raw_data):
    loader = PharmaDataLoader(sample_raw_data)
    df = loader.load_and_validate()
    assert not df.empty
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert (df["Units_Sold"] >= 0).all()
    assert (df["Stock_Balance"] >= 0).all()

def test_chronological_split_no_leakage(sample_raw_data):
    loader = PharmaDataLoader(sample_raw_data)
    df = loader.load_and_validate()
    weekly = loader.aggregate_weekly_demand()

    train, val, test = loader.chronological_split(weekly, train_ratio=0.6, val_ratio=0.2)
    assert train["Date"].max() < val["Date"].min()
    assert val["Date"].max() < test["Date"].min()

def test_features_shifted_anti_leakage(sample_raw_data):
    loader = PharmaDataLoader(sample_raw_data)
    loader.load_and_validate()
    weekly = loader.aggregate_weekly_demand()

    fe = FeatureEngineer(lag_periods=[1, 2], rolling_windows=[4])
    featured = fe.create_demand_features(weekly, target_col="Total_Units_Sold")

    # Verify that Demand_Lag_1 at row t equals Total_Units_Sold at row t-1
    for i in range(1, len(featured)):
        assert featured["Demand_Lag_1"].iloc[i] == featured["Total_Units_Sold"].iloc[i-1]
