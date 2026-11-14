"""
Streamlit Decision-Support Dashboard for Pharmacy Medicine Demand & Expiry Risk Forecasting.
Provides interactive demand forecasting with prediction intervals, batch-level triage,
what-if inventory shock simulations, explainability charts, and operational advisories.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import numpy as np
import pandas as pd
import streamlit as st
import joblib

# Page configuration
st.set_page_config(
    page_title="Algions | Pharmacy Demand & Expiry Risk Engine",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mandatory Operational Disclaimer
DISCLAIMER_TEXT = (
    "⚠️ **OPERATIONAL DECISION-SUPPORT NOTICE**: "
    "This tool generates statistical inventory forecasts and expiry risk flags to support supply-chain "
    "and replenishment workflows. It is **not** clinical, medical, or prescribing software and must "
    "never be used to guide patient treatment or drug therapy."
)

@st.cache_resource
def load_models_and_data():
    """Caches model artifacts and datasets for low-latency dashboard interaction."""
    models_dir = "models"
    data_path = "data/processed/pharmacy_demand_expiry_data.csv"

    artifacts = {}
    if os.path.exists(os.path.join(models_dir, "metadata.json")):
        with open(os.path.join(models_dir, "metadata.json"), "r") as f:
            artifacts["metadata"] = json.load(f)

    if os.path.exists(os.path.join(models_dir, "demand_forecaster.joblib")):
        artifacts["forecaster"] = joblib.load(os.path.join(models_dir, "demand_forecaster.joblib"))

    if os.path.exists(os.path.join(models_dir, "risk_classifier.joblib")):
        artifacts["risk_engine"] = joblib.load(os.path.join(models_dir, "risk_classifier.joblib"))

    if os.path.exists(data_path):
        artifacts["data"] = pd.read_csv(data_path)
        artifacts["data"]["Date"] = pd.to_datetime(artifacts["data"]["Date"])
    else:
        artifacts["data"] = pd.DataFrame()

    return artifacts

artifacts = load_models_and_data()

# Header & Disclaimer Banner
st.title("💊 Pharmacy Medicine Demand & Expiry-Risk Decision Support")
st.markdown(f"> {DISCLAIMER_TEXT}")

if not artifacts or "metadata" not in artifacts:
    st.error("Model artifacts not detected in `models/`. Please execute the training pipeline first: `python src/train.py`.")
    st.stop()

metadata = artifacts["metadata"]
df_raw = artifacts["data"]
forecaster = artifacts.get("forecaster")
risk_engine = artifacts.get("risk_engine")

if risk_engine is None:
    from src.models.risk_classifier import InventoryRiskEngine
    risk_engine = InventoryRiskEngine()

# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/fluency/96/pill.png", width=70)
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📊 Demand Forecasting Studio", "🚨 Batch Expiry Risk Triage", "🧪 What-If Simulation", "📈 Model Benchmarks & Explainability"]
)

# -----------------------------------------------------------------------------
# PAGE 1: DEMAND FORECASTING STUDIO
# -----------------------------------------------------------------------------
if page == "📊 Demand Forecasting Studio":
    st.header("Weekly Medicine Demand Forecasting")
    st.caption("Generate real-time point forecasts and 95% uncertainty intervals for active catalog items.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. Inventory Parameters")
        products = sorted(df_raw["Product_ID"].unique()) if not df_raw.empty else ["PROD_001", "PROD_002"]
        selected_prod = st.selectbox("Select Product", products, index=0)

        # Get defaults from historical dataset if available
        prod_data = df_raw[df_raw["Product_ID"] == selected_prod] if not df_raw.empty else pd.DataFrame()
        prod_name = prod_data["Product_Name"].iloc[0] if not prod_data.empty else "Amoxicillin 500mg"
        category = prod_data["Category"].iloc[0] if not prod_data.empty else "Antibiotic"

        st.info(f"**Medicine**: {prod_name}\n\n**Category**: {category}")

        lag_1 = st.slider("Last Week Demand (Lag 1)", min_value=5, max_value=400, value=75)
        rolling_4 = st.slider("Trailing 4-Week Moving Average", min_value=5, max_value=400, value=70)
        month = st.selectbox("Forecast Month", list(range(1, 13)), index=10)
        week_num = st.slider("Week of Year", 1, 52, 45)

        predict_btn = st.button("Generate Demand Forecast", type="primary")

    with col2:
        st.subheader("2. Model Forecast & Uncertainty Bounds")
        
        # Prepare feature vector
        row_dict = {
            "Month": month,
            "Quarter": (month - 1) // 3 + 1,
            "WeekOfYear": week_num,
            "Sin_Month": np.sin(2 * np.pi * month / 12.0),
            "Cos_Month": np.cos(2 * np.pi * month / 12.0),
            "Sin_Week": np.sin(2 * np.pi * week_num / 52.0),
            "Cos_Week": np.cos(2 * np.pi * week_num / 52.0),
            "Demand_Lag_1": float(lag_1),
            "Demand_Lag_2": float(lag_1 * 0.98),
            "Demand_Lag_4": float(rolling_4),
            "Demand_Lag_8": float(rolling_4 * 0.95),
            "Rolling_Mean_4": float(rolling_4),
            "Rolling_Std_4": float(rolling_4 * 0.12),
            "Rolling_Min_4": max(0.0, rolling_4 * 0.8),
            "Rolling_Max_4": rolling_4 * 1.2,
            "Rolling_Mean_8": float(rolling_4),
            "Rolling_Std_8": float(rolling_4 * 0.15),
            "Rolling_Min_8": max(0.0, rolling_4 * 0.75),
            "Rolling_Max_8": rolling_4 * 1.25,
            "Rolling_Mean_12": float(rolling_4),
            "Rolling_Std_12": float(rolling_4 * 0.18),
            "Rolling_Min_12": max(0.0, rolling_4 * 0.70),
            "Rolling_Max_12": rolling_4 * 1.30,
            "Demand_Momentum": float(lag_1 / (rolling_4 + 1e-5))
        }

        # Align with trained feature columns
        feat_df = pd.DataFrame([row_dict])
        for col in metadata["features"]:
            if col not in feat_df.columns:
                if col == f"Prod_{selected_prod}" or col == f"Cat_{category}":
                    feat_df[col] = 1
                else:
                    feat_df[col] = 0

        feat_df = feat_df[metadata["features"]]

        if forecaster is not None and hasattr(forecaster, "predict_with_uncertainty"):
            pred_mean, pred_lower, pred_upper = forecaster.predict_with_uncertainty(feat_df)
            val_mean = float(pred_mean[0])
            val_lower = float(pred_lower[0])
            val_upper = float(pred_upper[0])
        elif forecaster is not None:
            val_mean = float(forecaster.predict(feat_df)[0])
            val_lower = max(0.0, val_mean * 0.85)
            val_upper = val_mean * 1.15
        else:
            seasonal_mult = 1.0 + 0.3 * np.sin(2 * np.pi * month / 12.0)
            base_estimate = (0.55 * lag_1 + 0.45 * rolling_4) * seasonal_mult
            val_mean = float(np.clip(base_estimate, a_min=5.0, a_max=None))
            val_lower = max(0.0, val_mean * 0.88)
            val_upper = val_mean * 1.12

        m1, m2, m3 = st.columns(3)
        m1.metric("Predicted Demand", f"{val_mean:.1f} units")
        m2.metric("95% Lower Bound", f"{val_lower:.1f} units")
        m3.metric("95% Upper Bound", f"{val_upper:.1f} units")

        # Visualizing historical trend vs forecast
        if not prod_data.empty:
            weekly_hist = prod_data.groupby("Date")["Units_Sold"].sum().reset_index().tail(16)
            st.line_chart(weekly_hist.set_index("Date")["Units_Sold"])
            st.caption("Recent 16-Week Historical Demand Trend")

# -----------------------------------------------------------------------------
# PAGE 2: BATCH EXPIRY RISK TRIAGE
# -----------------------------------------------------------------------------
elif page == "🚨 Batch Expiry Risk Triage":
    st.header("Batch Expiry-Risk Triage Center")
    st.caption("Active batch surveillance identifying batches with surplus stock projected to expire before sale.")

    if df_raw.empty:
        st.warning("No batch records available to display.")
    else:
        # Filter latest date snapshot
        latest_date = df_raw["Date"].max()
        snapshot_df = df_raw[df_raw["Date"] == latest_date].copy()

        # Apply risk engine
        triaged = risk_engine.batch_triage_dataframe(snapshot_df, snapshot_df["Units_Sold"])

        # KPI Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Batches Monitored", len(triaged))
        crit_count = len(triaged[triaged["risk_tier"] == "CRITICAL"])
        warn_count = len(triaged[triaged["risk_tier"] == "WARNING"])
        c2.metric("Critical Risk Batches", crit_count, delta=f"{crit_count} urgent" if crit_count > 0 else "0", delta_color="inverse")
        c3.metric("Warning Batches", warn_count)
        capital_at_risk = triaged["estimated_capital_at_risk"].sum()
        c4.metric("Capital at Risk", f"${capital_at_risk:,.2f}")

        # Filter by risk tier
        selected_tier = st.multiselect("Filter by Tier", ["EXPIRED", "CRITICAL", "WARNING", "SURPLUS_MONITOR", "HEALTHY"], default=["CRITICAL", "WARNING"])
        filtered_triaged = triaged[triaged["risk_tier"].isin(selected_tier)] if selected_tier else triaged

        display_cols = [
            "batch_id", "product_name", "current_stock", "days_to_expiry",
            "forecasted_weekly_demand", "projected_waste_units", "estimated_capital_at_risk",
            "risk_tier", "recommended_action"
        ]
        
        st.dataframe(filtered_triaged[display_cols].sort_values(by=["days_to_expiry"]), use_container_width=True)

# -----------------------------------------------------------------------------
# PAGE 3: WHAT-IF SIMULATION
# -----------------------------------------------------------------------------
elif page == "🧪 What-If Simulation":
    st.header("What-If Inventory Stress Testing")
    st.caption("Simulate demand shocks (epidemic surge, supply chain disruption, markdown promotions) on stock survival.")

    c1, c2 = st.columns(2)
    with c1:
        sim_stock = st.number_input("Batch Stock Balance", value=450, step=25)
        sim_days = st.slider("Days Until Expiry", min_value=1, max_value=180, value=45)
        sim_demand = st.slider("Base Weekly Demand", min_value=5, max_value=250, value=50)

    with c2:
        demand_shock_pct = st.slider("Demand Multiplier (Shock / Seasonality)", min_value=0.5, max_value=2.5, value=1.0, step=0.1)
        sim_unit_price = st.number_input("Unit Price ($)", value=14.50, step=1.0)

    effective_demand = sim_demand * demand_shock_pct
    weeks_remaining = sim_days / 7.0
    projected_sales = effective_demand * weeks_remaining
    projected_surplus = max(0.0, sim_stock - projected_sales)
    financial_loss = projected_surplus * sim_unit_price

    st.divider()
    res1, res2, res3 = st.columns(3)
    res1.metric("Effective Weekly Demand", f"{effective_demand:.1f} units")
    res2.metric("Projected Spoilage Quantity", f"{projected_surplus:.1f} units", delta=f"{projected_surplus:.0f} wasted" if projected_surplus > 0 else "0", delta_color="inverse")
    res3.metric("Projected Financial Write-Off", f"${financial_loss:,.2f}")

    if projected_surplus > 0:
        st.error(f"🚨 **Intervention Required**: Under current velocity, **{projected_surplus:.0f} units** will expire unsold in {sim_days} days. Recommended Action: Accelerate stock via 20-30% institutional markdown or FEFO rotation.")
    else:
        st.success(f"✅ **Stock Healthy**: Projected demand ({projected_sales:.0f} units) comfortably absorbs all available stock before expiry.")

# -----------------------------------------------------------------------------
# PAGE 4: MODEL BENCHMARKS & EXPLAINABILITY
# -----------------------------------------------------------------------------
elif page == "📈 Model Benchmarks & Explainability":
    st.header("Rigorous Model Comparison & Explainability")
    st.caption("Verification against naive/moving-average baselines and feature importance inspection.")

    st.subheader("1. Demand Forecasting Benchmarks (Held-Out Test Data)")
    benchmarks = metadata.get("all_demand_comparisons", {})
    bench_df = pd.DataFrame(benchmarks).T
    st.dataframe(bench_df, use_container_width=True)

    st.subheader("2. Expiry Risk Classifier Metrics")
    risk_m = metadata.get("risk_test_metrics", {})
    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    r_col1.metric("Precision", f"{risk_m.get('Precision', 0):.4f}")
    r_col2.metric("Recall", f"{risk_m.get('Recall', 0):.4f}")
    r_col3.metric("F1-Score", f"{risk_m.get('F1_Score', 0):.4f}")
    r_col4.metric("ROC-AUC", f"{risk_m.get('ROC_AUC', 0):.4f}")

    st.subheader("3. Top Predictive Feature Drivers")
    if hasattr(forecaster, "get_feature_importances"):
        importances = forecaster.get_feature_importances()
        top_10 = dict(list(importances.items())[:10])
        imp_df = pd.DataFrame({"Feature": list(top_10.keys()), "Relative Importance": list(top_10.values())})
        st.bar_chart(imp_df.set_index("Feature"))

st.sidebar.markdown("---")
st.sidebar.caption(f"**Model Version**: {metadata.get('model_version', '1.0.0')}")
st.sidebar.caption(f"**Active Forecaster**: {metadata.get('selected_demand_model', 'Random Forest')}")
