"""
Integration tests for FastAPI endpoints.
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
