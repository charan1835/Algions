"""
Evaluation Engine for Pharmaceutical Demand Forecasting and Expiry Risk Detection.
Computes MAE, RMSE, WAPE for demand regression, and Precision, Recall, F1, PR-AUC,
and Confusion Matrix for expiry risk classification, alongside business cost metrics.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    average_precision_score
)

class ModelEvaluator:
    """Computes comprehensive regression and classification performance metrics."""

    @staticmethod
    def calculate_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Calculates Weighted Absolute Percentage Error (WAPE).
        WAPE = sum(|y_true - y_pred|) / sum(y_true)
        Standard in retail and pharmaceutical supply chain forecasting.
        """
        denominator = np.sum(y_true)
        if denominator == 0:
            return 0.0
        return float(np.sum(np.abs(y_true - y_pred)) / denominator)

    @staticmethod
    def evaluate_demand_regression(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Computes MAE, RMSE, WAPE, and R2 for demand forecasts.
        """
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        wape = ModelEvaluator.calculate_wape(y_true, y_pred)
        r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0

        # Mean bias error (positive = overforecasting, negative = underforecasting)
        mbe = float(np.mean(y_pred - y_true))

        return {
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "WAPE": round(wape, 4),
            "WAPE_Pct": f"{round(wape * 100, 2)}%",
            "R2": round(r2, 4),
            "MBE": round(mbe, 2)
        }

    @staticmethod
    def evaluate_risk_classification(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray = None) -> Dict[str, Any]:
        """
        Computes Precision, Recall, F1, Confusion Matrix, and ROC/PR AUC for expiry-risk flags.
        """
        y_true = np.asarray(y_true, dtype=int)
        y_pred = np.asarray(y_pred, dtype=int)

        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

        metrics = {
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "F1_Score": round(f1, 4),
            "Specificity": round(specificity, 4),
            "True_Positives": int(tp),
            "False_Positives": int(fp),
            "True_Negatives": int(tn),
            "False_Negatives": int(fn)
        }

        if y_prob is not None:
            try:
                metrics["ROC_AUC"] = round(float(roc_auc_score(y_true, y_prob)), 4)
                metrics["PR_AUC"] = round(float(average_precision_score(y_true, y_prob)), 4)
            except Exception:
                metrics["ROC_AUC"] = None
                metrics["PR_AUC"] = None

        return metrics

    @staticmethod
    def compute_business_impact(y_true_demand: np.ndarray, 
                                y_pred_demand: np.ndarray, 
                                at_risk_df: pd.DataFrame, 
                                cost_per_unit_stockout: float = 8.0, 
                                cost_per_unit_waste: float = 12.0) -> Dict[str, Any]:
        """
        Simulates inventory cost savings from model adoption versus naive baseline.
        """
        # Underforecasting causes stockouts
        stockout_units = np.maximum(0, y_true_demand - y_pred_demand).sum()
        # Overforecasting causes surplus buffer holding costs
        surplus_units = np.maximum(0, y_pred_demand - y_true_demand).sum()

        stockout_cost = stockout_units * cost_per_unit_stockout
        
        # Capital preserved through timely FEFO rotation of flagged batches
        prevented_waste_units = at_risk_df["Units_Sold"].sum() if "Units_Sold" in at_risk_df else 0
        capital_protected = prevented_waste_units * cost_per_unit_waste

        return {
            "Stockout_Units_Estimated": int(stockout_units),
            "Stockout_Cost_Penalty": round(float(stockout_cost), 2),
            "Prevented_Waste_Units": int(prevented_waste_units),
            "Capital_Protected": round(float(capital_protected), 2)
        }
