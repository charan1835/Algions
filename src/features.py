"""
Feature Engineering Engine for Pharmacy Demand Forecasting & Expiry Risk Assessment.
Computes lag features, rolling statistics, calendar seasonality, and stock-to-demand ratios
with strict anti-leakage guards (all lag/rolling metrics shifted by at least 1 period).
"""

import numpy as np
import pandas as pd
from typing import List, Tuple

class FeatureEngineer:
    """Extracts leakage-free temporal, product, and batch-level features."""

    def __init__(self, lag_periods: List[int] = None, rolling_windows: List[int] = None):
        self.lag_periods = lag_periods or [1, 2, 4, 8]
        self.rolling_windows = rolling_windows or [4, 8, 12]

    def create_demand_features(self, df: pd.DataFrame, target_col: str = "Total_Units_Sold") -> pd.DataFrame:
        """
        Creates product-level demand forecasting features from weekly aggregated series.
        All rolling and lag statistics use shift(1) to prevent target leakage.
        """
        data = df.copy().sort_values(by=["Product_ID", "Date"]).reset_index(drop=True)

        feature_dfs = [data]

        # 1. Calendar & Seasonality features
        data["Month"] = data["Date"].dt.month
        data["Quarter"] = data["Date"].dt.quarter
        data["WeekOfYear"] = data["Date"].dt.isocalendar().week.astype(int)

        # Cyclical month encodings for smooth periodic representation
        data["Sin_Month"] = np.sin(2 * np.pi * data["Month"] / 12.0)
        data["Cos_Month"] = np.cos(2 * np.pi * data["Month"] / 12.0)
        data["Sin_Week"] = np.sin(2 * np.pi * data["WeekOfYear"] / 52.0)
        data["Cos_Week"] = np.cos(2 * np.pi * data["WeekOfYear"] / 52.0)

        # 2. Lag features (strictly shifted)
        for lag in self.lag_periods:
            col_name = f"Demand_Lag_{lag}"
            data[col_name] = data.groupby("Product_ID")[target_col].shift(lag)

        # 3. Rolling window statistics (shifted by 1 to exclude current period)
        for w in self.rolling_windows:
            rolled = data.groupby("Product_ID")[target_col].shift(1).rolling(window=w)
            data[f"Rolling_Mean_{w}"] = rolled.mean()
            data[f"Rolling_Std_{w}"] = rolled.std().fillna(0)
            data[f"Rolling_Min_{w}"] = rolled.min()
            data[f"Rolling_Max_{w}"] = rolled.max()

        # 4. Momentum / Trend ratio
        data["Demand_Momentum"] = (data["Demand_Lag_1"] / (data["Rolling_Mean_4"] + 1e-5)).clip(0, 5)

        # 5. One-hot encoding for categorical attributes
        cat_dummies = pd.get_dummies(data["Category"], prefix="Cat", drop_first=True)
        prod_dummies = pd.get_dummies(data["Product_ID"], prefix="Prod", drop_first=True)

        data = pd.concat([data, cat_dummies, prod_dummies], axis=1)

        # Drop rows where initial lags are NaN
        max_lag = max(self.lag_periods + self.rolling_windows)
        data_clean = data.dropna().reset_index(drop=True)

        return data_clean

    def create_batch_risk_features(self, batch_df: pd.DataFrame, forecasted_weekly_demand: pd.Series = None) -> pd.DataFrame:
        """
        Enriches batch records with inventory depletion rate, shelf-life ratios,
        and projected stock remaining at expiry date.
        """
        df = batch_df.copy()

        df["Days_To_Expiry"] = pd.to_numeric(df["Days_To_Expiry"], errors="coerce").fillna(0)
        df["Weeks_To_Expiry"] = (df["Days_To_Expiry"] / 7.0).clip(lower=0)
        df["Stock_Balance"] = pd.to_numeric(df["Stock_Balance"], errors="coerce").fillna(0)

        # Shelf-life burn velocity
        # If forecasted weekly demand is provided, use it; otherwise use 4-week trailing proxy
        if forecasted_weekly_demand is not None and len(forecasted_weekly_demand) == len(df):
            df["Expected_Weekly_Demand"] = np.asarray(forecasted_weekly_demand)
        else:
            df["Expected_Weekly_Demand"] = df["Units_Sold"].clip(lower=1)

        # Cumulative projected demand over remaining shelf life
        df["Projected_Demand_Until_Expiry"] = df["Expected_Weekly_Demand"] * df["Weeks_To_Expiry"]
        
        # Risk metric: Expected Excess Units = Stock_Balance - Projected_Demand_Until_Expiry
        df["Projected_Excess_Units"] = df["Stock_Balance"] - df["Projected_Demand_Until_Expiry"]
        
        # Ratio of Stock to Expected Demand
        df["Stock_Cover_Ratio"] = (df["Stock_Balance"] / (df["Projected_Demand_Until_Expiry"] + 1e-5)).clip(0, 10)
        df["Stock_Cover_Weeks"] = (df["Stock_Balance"] / (df["Expected_Weekly_Demand"] + 1e-5)).clip(0, 52)
        df["Depletion_Percentage"] = ((df["Initial_Stock"] - df["Stock_Balance"]) / (df["Initial_Stock"] + 1e-5)).clip(0, 1)

        # Operational Risk Categorization
        # Rule:
        # High Risk: Days_To_Expiry <= 60 AND Projected_Excess_Units > 0
        # Medium Risk: 60 < Days_To_Expiry <= 90 AND Projected_Excess_Units > 0
        # Safe: Days_To_Expiry > 90 OR Projected_Excess_Units <= 0
        conditions = [
            (df["Days_To_Expiry"] <= 60) & (df["Projected_Excess_Units"] > 0),
            (df["Days_To_Expiry"] <= 90) & (df["Projected_Excess_Units"] > 0)
        ]
        choices = ["CRITICAL", "WARNING"]
        df["Risk_Category"] = np.select(conditions, choices, default="SAFE")
        
        # Ground truth target: if Is_At_Risk is in source data, use it; otherwise fallback to rule
        if "Is_At_Risk" in df.columns:
            df["Is_At_Risk_Binary"] = df["Is_At_Risk"].astype(int)
        else:
            df["Is_At_Risk_Binary"] = (df["Risk_Category"].isin(["CRITICAL", "WARNING"])).astype(int)

        return df

    def get_feature_names(self, df: pd.DataFrame, exclude_cols: List[str] = None) -> List[str]:
        """Returns list of numeric feature column names for model training."""
        exclude = set(exclude_cols or [
            "Date", "Product_ID", "Product_Name", "Category", 
            "Batch_ID", "Manufacture_Date", "Expiry_Date", 
            "Total_Units_Sold", "Units_Sold", "Is_At_Risk", "Is_At_Risk_Binary", "Risk_Category"
        ])
        return [col for col in df.columns if col not in exclude and np.issubdtype(df[col].dtype, np.number)]
