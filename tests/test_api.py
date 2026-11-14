"""
Integration tests for FastAPI endpoints and frontend serving.
"""

import pytest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_api_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_frontend_ui_serving():
    response = client.get("/")
    assert response.status_code == 200
    assert "Algions" in response.text

def test_frontend_ui_alias_endpoint():
    response = client.get("/ui")
    assert response.status_code == 200
    assert "Demand Forecasting Studio" in response.text

def test_frontend_assets_serving():
    css_res = client.get("/style.css")
    assert css_res.status_code == 200
    assert "font-sans" in css_res.text or "badge-critical" in css_res.text

    js_res = client.get("/app.js")
    assert js_res.status_code == 200
    assert "triageBatchRecord" in js_res.text

def test_api_products_endpoint():
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    assert len(data["products"]) >= 6

def test_api_summary_endpoint():
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "active_medicines" in data
    assert "capital_at_risk_usd" in data

def test_demand_prediction_endpoint():
    payload = {
        "product_id": "PROD_001",
        "product_name": "Amoxicillin 500mg",
        "category": "Antibiotic",
        "month": 11,
        "week_of_year": 46,
        "demand_lag_1": 68.0,
        "demand_lag_2": 65.0,
        "demand_lag_4": 60.0,
        "demand_lag_8": 55.0,
        "rolling_mean_4": 64.0,
        "rolling_std_4": 4.5,
        "rolling_mean_8": 61.0,
        "rolling_mean_12": 58.0
    }
    response = client.post("/predict/demand", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "forecasted_demand" in data
    assert "confidence_interval_95" in data
    assert data["confidence_interval_95"]["lower"] <= data["forecasted_demand"]
    assert data["confidence_interval_95"]["upper"] >= data["forecasted_demand"]

def test_batch_risk_assessment_endpoint():
    payload = {
        "batch_id": "BAT_TEST_99",
        "product_id": "PROD_001",
        "product_name": "Amoxicillin 500mg",
        "stock_balance": 350,
        "initial_stock": 600,
        "days_to_expiry": 35,
        "unit_price": 12.50,
        "custom_weekly_demand_override": 20.0
    }
    response = client.post("/batches/risk-assessment", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "BAT_TEST_99"
    assert "risk_tier" in data
    assert "projected_waste_units" in data
    assert "recommended_action" in data
    assert "disclaimer" in data
