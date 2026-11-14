"""
Supervised Machine Learning Models for Pharmaceutical Demand Forecasting.
Provides Ridge, Random Forest, and Gradient Boosting forecasters with feature
importance extraction and prediction interval / uncertainty quantification.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

class RidgeDemandRegressor:
    """Regularized linear regression for demand forecasting."""

    def __init__(self, alpha: float = 1.0, random_state: int = 42):
        self.alpha = alpha
        self.random_state = random_state
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=self.alpha, random_state=self.random_state))
        ])
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.feature_names = list(X.columns)
        self.pipeline.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.pipeline.predict(X[self.feature_names])
        return np.clip(preds, a_min=0, a_max=None)

    def get_feature_coefficients(self) -> Dict[str, float]:
        coefs = self.pipeline.named_steps["model"].coef_
        return dict(zip(self.feature_names, coefs))


class RandomForestDemandForecaster:
    """Random Forest regressor with uncertainty estimation from tree variance."""

    def __init__(self, n_estimators: int = 100, max_depth: int = 10, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.feature_names = list(X.columns)
        self.model.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.model.predict(X[self.feature_names])
        return np.clip(preds, a_min=0, a_max=None)

    def predict_with_uncertainty(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns (mean_prediction, lower_bound_95, upper_bound_95)
        calculated from individual tree predictions.
        """
        features = X[self.feature_names].values
        tree_preds = np.array([tree.predict(features) for tree in self.model.estimators_])
        mean_preds = np.mean(tree_preds, axis=0)
        std_preds = np.std(tree_preds, axis=0)
        lower_bound = np.clip(mean_preds - 1.96 * std_preds, 0, None)
        upper_bound = mean_preds + 1.96 * std_preds
        return mean_preds, lower_bound, upper_bound

    def get_feature_importances(self) -> Dict[str, float]:
        importances = self.model.feature_importances_
        return dict(sorted(zip(self.feature_names, importances), key=lambda x: x[1], reverse=True))


class GradientBoostingDemandForecaster:
    """Gradient Boosting regressor capturing subtle non-linear seasonal interactions."""

    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.05, max_depth: int = 5, random_state: int = 42):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.random_state = random_state
        self.model = GradientBoostingRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            random_state=self.random_state
        )
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.feature_names = list(X.columns)
        self.model.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.model.predict(X[self.feature_names])
        return np.clip(preds, a_min=0, a_max=None)

    def get_feature_importances(self) -> Dict[str, float]:
        importances = self.model.feature_importances_
        return dict(sorted(zip(self.feature_names, importances), key=lambda x: x[1], reverse=True))
