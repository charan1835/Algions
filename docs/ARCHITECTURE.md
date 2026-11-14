# System Architecture & Technical Specifications
**Algions AI Labs** | Pharmacy Medicine Demand & Expiry-Risk Decision Support System

---

## 1. High-Level System Architecture

The following diagram illustrates the complete end-to-end data preparation, model training, artifact persistence, and dual-interface inference architecture:

```mermaid
flowchart TD
    subgraph Data_Pipeline["1. Ingestion & Quality Validation"]
        A["Synthetic Data Generator<br/>(104 Weeks, 6 Products)"] --> B["data/processed/pharmacy_demand_expiry_data.csv"]
        C["Kaggle ATC Sales Pipeline<br/>(2014-2019 Daily Sales)"] --> D["data/processed/augmented_pharmacy_data.csv"]
        B --> E["PharmaDataLoader<br/>(Schema Validation & Zero-Value Checks)"]
        D --> E
    end

    subgraph Feature_Engineering["2. Anti-Leakage Feature Engine"]
        E --> F["FeatureEngineer"]
        F --> G["Autoregressive Lags (1, 2, 4, 8)"]
        F --> H["Rolling Stats (Mean, Std, Min, Max)"]
        F --> I["Cyclical Calendar Encodings (Sin/Cos)"]
        F --> J["Batch Lifecycles & Stock Cover Ratios"]
    end

    subgraph Chronological_Split["3. Leakage-Free Data Splitting"]
        G & H & I & J --> K["Chronological Splitter"]
        K --> L["Train Set (70%): Weeks 1-73"]
        K --> M["Val Set (15%): Weeks 74-88"]
        K --> N["Held-Out Test (15%): Weeks 89-104"]
    end

    subgraph Model_Development["4. Model Benchmarking & Serialization"]
        L & M --> O["Baselines: Naive, 4W-MA, Seasonal Naive"]
        L & M --> P["Candidate 1: Ridge Regression"]
        L & M --> Q["Candidate 2: Random Forest (Champion)"]
        L & M --> R["Candidate 3: Gradient Boosting"]
        L & M --> S["Batch Expiry Risk Engine"]
        N --> T["Evaluation Engine<br/>(MAE, RMSE, WAPE, Precision, Recall, F1)"]
        Q --> U["models/demand_forecaster.joblib"]
        S --> V["models/risk_classifier.joblib"]
        T --> W["models/metadata.json"]
    end

    subgraph Inference_Layer["5. Dual Inference Interfaces"]
        U & V & W --> X["FastAPI REST Service<br/>(Port 8000)"]
        U & V & W --> Y["Streamlit Decision Dashboard<br/>(Port 8501)"]
        X --> Z["REST Clients / ERP Integration"]
        Y --> AA["Pharmacy Inventory Managers"]
    end
```

---

## 2. Real-Time Inference Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Pharmacy Inventory Manager
    participant UI as Streamlit / FastAPI
    participant Engine as InventoryRiskEngine
    participant ML as RandomForestForecaster
    participant DB as Model Artifacts (.joblib)

    User->>UI: Request Demand Forecast (Product ID, Lags, Season)
    UI->>DB: Load Cached Model & Feature Pipeline
    UI->>ML: Pass Feature Vector (Zero-Leakage Lags)
    ML-->>UI: Return Point Forecast & 95% Confidence Interval
    User->>UI: Submit Batch Triage Query (Batch ID, Stock, Days to Expiry)
    UI->>Engine: Evaluate Batch (Stock Balance vs Projected Sales)
    Engine->>Engine: Compute Excess Units & Financial Exposure
    Engine-->>UI: Return Risk Tier (CRITICAL/WARNING/SAFE) & Operational Action
    UI-->>User: Display Interactive Triage Card + Advisory Notice
```

---

## 3. Data Contracts & Schemas

### 3.1 Weekly Processed Dataset Schema
* `Date` (datetime64): Weekly observation timestamp (Monday).
* `Product_ID` (string): Unique medicine identifier (e.g., `PROD_001`).
* `Product_Name` (string): Clinical commercial title (e.g., `Amoxicillin 500mg`).
* `Category` (string): Pharmacological therapeutic class (e.g., `Antibiotic`).
* `Unit_Price` (float): Unit acquisition cost in USD.
* `Batch_ID` (string): Unique lot batch identifier (e.g., `BAT_001_101`).
* `Manufacture_Date` (datetime64): Release date from manufacturing facility.
* `Expiry_Date` (datetime64): Regulatory expiration date.
* `Initial_Stock` (integer): Total units produced in lot batch.
* `Units_Sold` (integer): Actual physical units dispensed during week.
* `Stock_Balance` (integer): Non-negative units remaining on shelf.
* `Days_To_Expiry` (integer): Calendar days remaining until expiration.
* `Is_At_Risk` (integer binary): 1 if `Days_To_Expiry <= 60` and `Stock_Balance > 0`.

### 3.2 FastAPI REST Endpoints Contract
* `POST /predict/demand`:
  - Request: `{"product_id": "PROD_001", "month": 11, "demand_lag_1": 68.0, "rolling_mean_4": 64.0, ...}`
  - Response: `{"product_id": "PROD_001", "forecasted_demand": 71.4, "confidence_interval_95": {"lower": 62.8, "upper": 80.0}, ...}`
* `POST /batches/risk-assessment`:
  - Request: `{"batch_id": "BAT_001_CRIT", "stock_balance": 420, "days_to_expiry": 30, ...}`
  - Response: `{"risk_tier": "CRITICAL", "projected_waste_units": 355.7, "estimated_capital_at_risk": 4446.25, "recommended_action": "...", "disclaimer": "..."}`
