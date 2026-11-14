"""
Data Loader & Quality Validation Pipeline.
Handles data ingestion, schema validation, data cleanliness checks,
and chronological dataset partitioning without lookahead bias.
"""

import os
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any

REQUIRED_COLUMNS = [
    "Date", "Product_ID", "Product_Name", "Category", 
    "Batch_ID", "Manufacture_Date", "Expiry_Date", 
    "Initial_Stock", "Units_Sold", "Stock_Balance", "Days_To_Expiry"
]

class PharmaDataLoader:
    """Loads and validates pharmaceutical demand and batch lifecycle data."""

    def __init__(self, file_path: str = "data/processed/pharmacy_demand_expiry_data.csv"):
        self.file_path = file_path
        self.df: pd.DataFrame = pd.DataFrame()

    def load_and_validate(self) -> pd.DataFrame:
        """Loads CSV, validates schema, converts dates, and checks data integrity."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Dataset not found at '{self.file_path}'. Run data/synthetic_generator.py first.")

        df = pd.read_csv(self.file_path)

        # 1. Schema check
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Schema validation failed. Missing columns: {missing_cols}")

        # 2. Type conversions
        df["Date"] = pd.to_datetime(df["Date"])
        df["Manufacture_Date"] = pd.to_datetime(df["Manufacture_Date"])
        df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"])
        df["Units_Sold"] = pd.to_numeric(df["Units_Sold"], errors="coerce").fillna(0).clip(lower=0)
        df["Stock_Balance"] = pd.to_numeric(df["Stock_Balance"], errors="coerce").fillna(0).clip(lower=0)
        df["Initial_Stock"] = pd.to_numeric(df["Initial_Stock"], errors="coerce").fillna(0).clip(lower=0)
        df["Days_To_Expiry"] = pd.to_numeric(df["Days_To_Expiry"], errors="coerce").fillna(0)

        # 3. Quality assurance assertions
        # Units sold cannot be negative
        assert (df["Units_Sold"] >= 0).all(), "Data Quality Error: Negative Units_Sold detected."
        # Stock balance cannot be negative
        assert (df["Stock_Balance"] >= 0).all(), "Data Quality Error: Negative Stock_Balance detected."

        # Derived flags
        if "Is_At_Risk" not in df.columns:
            # Expiry risk: remaining shelf life <= 60 days with unsold units on hand
            df["Is_At_Risk"] = ((df["Days_To_Expiry"] <= 60) & (df["Stock_Balance"] > 0)).astype(int)

        self.df = df.sort_values(by=["Product_ID", "Date"]).reset_index(drop=True)
        return self.df

    def aggregate_weekly_demand(self) -> pd.DataFrame:
        """
        Aggregates batch-level transactions into Product-Week demand series
        for demand forecasting, while preserving batch metadata for expiry analysis.
        """
        if self.df.empty:
            self.load_and_validate()

        # Group by Product and Date (Week start)
        prod_weekly = self.df.groupby(["Product_ID", "Product_Name", "Category", "Date"]).agg(
            Total_Units_Sold=("Units_Sold", "sum"),
            Total_Stock_Balance=("Stock_Balance", "sum"),
            Active_Batches=("Batch_ID", "nunique"),
            Min_Days_To_Expiry=("Days_To_Expiry", "min")
        ).reset_index().sort_values(by=["Product_ID", "Date"])

        return prod_weekly

    def chronological_split(self, df: pd.DataFrame, train_ratio: float = 0.70, val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Performs a strict chronological train/validation/test split.
        Ensures NO future leakage into earlier partitions.
        """
        dates = sorted(df["Date"].unique())
        n_dates = len(dates)

        train_cutoff_idx = int(n_dates * train_ratio)
        val_cutoff_idx = int(n_dates * (train_ratio + val_ratio))

        train_cutoff_date = dates[train_cutoff_idx]
        val_cutoff_date = dates[val_cutoff_idx]

        train_df = df[df["Date"] < train_cutoff_date].copy()
        val_df = df[(df["Date"] >= train_cutoff_date) & (df["Date"] < val_cutoff_date)].copy()
        test_df = df[df["Date"] >= val_cutoff_date].copy()

        # Verify no overlap
        assert train_df["Date"].max() < val_df["Date"].min(), "Leakage detected: Train/Val overlap."
        assert val_df["Date"].max() < test_df["Date"].min(), "Leakage detected: Val/Test overlap."

        return train_df, val_df, test_df

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Returns profiling metrics for EDA and documentation."""
        if self.df.empty:
            self.load_and_validate()

        return {
            "total_records": len(self.df),
            "num_products": self.df["Product_ID"].nunique(),
            "num_batches": self.df["Batch_ID"].nunique(),
            "date_range": (self.df["Date"].min().strftime("%Y-%m-%d"), self.df["Date"].max().strftime("%Y-%m-%d")),
            "total_units_sold": int(self.df["Units_Sold"].sum()),
            "at_risk_batch_records": int(self.df["Is_At_Risk"].sum()),
            "risk_prevalence": float(self.df["Is_At_Risk"].mean())
        }
