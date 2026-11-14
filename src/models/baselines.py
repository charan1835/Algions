"""
Baseline Models for Pharmacy Medicine Demand Forecasting.
Implements:
1. Naive Last-Period (Persistence) Model
2. Simple Moving Average Baseline (e.g. 4-week, 12-week)
3. Seasonal Naive Baseline (accounting for seasonal periodicity)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any

class NaiveLastValueBaseline:
    """Predicts next period's demand using the most recent observed period's demand."""

    def __init__(self, target_col: str = "Total_Units_Sold"):
        self.target_col = target_col
        self.last_values: Dict[str, float] = {}

    def fit(self, df: pd.DataFrame):
        for prod_id, grp in df.groupby("Product_ID"):
            self.last_values[prod_id] = grp.sort_values("Date")[self.target_col].iloc[-1]
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            prod = row.get("Product_ID", None)
            if prod is None:
                # Check for one-hot encoded prod columns
                for col in row.index:
                    if col.startswith("Prod_") and row[col] == 1:
                        prod = col.replace("Prod_", "")
                        break
            preds.append(self.last_values.get(prod, df[self.target_col].mean() if self.target_col in df else 50.0))
        return np.array(preds)


class MovingAverageBaseline:
    """Predicts next period's demand using the trailing N-week simple moving average."""

    def __init__(self, window: int = 4, target_col: str = "Total_Units_Sold"):
        self.window = window
        self.target_col = target_col
        self.trailing_means: Dict[str, float] = {}

    def fit(self, df: pd.DataFrame):
        for prod_id, grp in df.groupby("Product_ID"):
            sorted_vals = grp.sort_values("Date")[self.target_col]
            self.trailing_means[prod_id] = sorted_vals.tail(self.window).mean()
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            prod = row.get("Product_ID", None)
            if prod is None:
                for col in row.index:
                    if col.startswith("Prod_") and row[col] == 1:
                        prod = col.replace("Prod_", "")
                        break
            preds.append(self.trailing_means.get(prod, 50.0))
        return np.array(preds)


class SeasonalNaiveBaseline:
    """
    Predicts demand using the observation from the same seasonal cycle in the past.
    For weekly data, uses 52-week lag if available, otherwise falls back to trailing 4-week mean.
    """

    def __init__(self, seasonal_period: int = 52, target_col: str = "Total_Units_Sold"):
        self.seasonal_period = seasonal_period
        self.target_col = target_col
        self.history: pd.DataFrame = None

    def fit(self, df: pd.DataFrame):
        self.history = df[["Product_ID", "Date", self.target_col]].copy()
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            prod = row.get("Product_ID", None)
            if prod is None:
                for col in row.index:
                    if col.startswith("Prod_") and row[col] == 1:
                        prod = col.replace("Prod_", "")
                        break
            date_val = row.get("Date", None)
            if date_val is not None:
                target_date = date_val - pd.DateOffset(weeks=self.seasonal_period)
                match = self.history[(self.history["Product_ID"] == prod) & (self.history["Date"] == target_date)]
            else:
                match = pd.DataFrame()
            if not match.empty:
                preds.append(float(match[self.target_col].iloc[0]))
            else:
                # Fallback to product mean
                prod_hist = self.history[self.history["Product_ID"] == prod]
                preds.append(float(prod_hist[self.target_col].mean()) if not prod_hist.empty else 50.0)
        return np.array(preds)
