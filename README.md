# Pharmacy Medicine Demand & Expiry-Risk Forecasting
### Algions AI Labs Private Limited | Advanced Individual Project Assessment
**Internship Role**: AI & Machine Learning  
**Assigned Project**: Pharmacy Medicine Demand & Expiry-Risk Forecasting  
**Domain**: Pharmacy Management  

---

> [!IMPORTANT]
> **OPERATIONAL ADVISORY NOTICE**:  
> This system is designed solely as a **decision-support tool** for pharmacy supply-chain logistics, replenishment planning, and batch stock-rotation triage. Outputs and alerts are **strictly advisory** and must **never** be used as clinical, therapeutic, dosage, or medical treatment guidance.

---

## 🚀 Quickstart Guide

### 1. Environment Setup
Clone the repository and install dependencies in a clean Python 3.10+ virtual environment:

```bash
# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Dataset Ingestion & Generation
Generate both the benchmark synthetic weekly dataset (104 weeks, 6 products, 30 batches) and the augmented Kaggle ATC pharmacy dataset:

```bash
python data/build_datasets.py
```
*Outputs are saved to `data/processed/pharmacy_demand_expiry_data.csv` and `data/processed/augmented_pharmacy_data.csv`.*

### 3. Model Training & Evaluation Pipeline
Run the end-to-end reproducible training script (with fixed seed `42` and strict chronological splitting):

```bash
python src/train.py --data data/processed/pharmacy_demand_expiry_data.csv --out models --seed 42
```
*Outputs evaluation benchmarks to the console and persists artifacts to `models/`.*

### 4. Running Unit & Integration Tests
Execute the automated test suite verifying data loaders, anti-leakage guards, model uncertainty, and API endpoints:

```bash
pytest tests/ -v
```

### 5. Launching the Interactive Decision Dashboard (Streamlit)
Launch the interactive Streamlit application with live demand forecasting, batch triage surveillance, and what-if simulation:

```bash
streamlit run app/dashboard.py
```
Open your browser at `http://localhost:8501`.

### 6. Launching the Enterprise Web Frontend & REST API
Run the high-performance REST API with embedded enterprise single-page web application:

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```
- **Enterprise Web Frontend UI**: Open `http://localhost:8000` (or `http://localhost:8000/ui`)
- **Interactive Swagger Documentation**: Open `http://localhost:8000/docs`
- **Standalone Frontend**: You can also double-click and open `frontend/index.html` directly in any web browser without needing a server!

---

## 📊 Benchmark Evaluation Summary

All models were evaluated on a **strict chronological held-out test set** (final 15% of timeline) that was never seen during feature selection or model training:

### Demand Forecasting Comparison
| Model | MAE | RMSE | WAPE (%) | $R^2$ | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: Last-Value Naive** | 14.82 | 21.40 | 15.34% | 0.8120 | Reference |
| **Baseline 2: 4-Week Moving Average** | 12.15 | 17.65 | 12.58% | 0.8650 | Reference |
| **Baseline 3: Seasonal Naive** | 11.40 | 16.20 | 11.80% | 0.8840 | Reference |
| **Candidate 1: Ridge Regression** | 8.92 | 12.85 | 9.24% | 0.9270 | Linear ML |
| **Candidate 2: Random Forest** | **6.45** | **9.72** | **6.68%** | **0.9580** | **Champion Model** |
| **Candidate 3: Gradient Boosting** | 6.80 | 10.15 | 7.04% | 0.9540 | Non-linear ML |

*The Champion Random Forest model reduced WAPE from 15.34% down to 6.68% (a **56.5% error reduction**).*

### Batch Expiry Risk Classifier Performance
| Metric | Score | Operational Significance |
| :--- | :---: | :--- |
| **Precision** | **91.25%** | Minimizes false alarms; 91% of flagged batches truly faced excess spoilage. |
| **Recall** | **94.80%** | Captures 95% of all inventory write-off risks before expiration occurs. |
| **$F_1$-Score** | **0.9299** | High harmonic balance between precision and sensitivity. |
| **ROC-AUC** | **0.9840** | Strong discriminative ability across decision thresholds. |
| **Confusion Matrix** | $TP=73, FP=7, TN=172, FN=4$ | 4 missed risks out of 256 test evaluations. |

---

## 📁 Repository Structure

```
Algions/
├── data/
│   ├── build_datasets.py              # Automated builder for all benchmark datasets
│   ├── synthetic_generator.py          # Generator for weekly synthetic & Kaggle-augmented data
│   ├── raw/                           # Placeholder for optional raw Kaggle salesdaily.csv
│   └── processed/
│       ├── pharmacy_demand_expiry_data.csv  # Primary weekly pharmacy dataset
│       └── augmented_pharmacy_data.csv      # Kaggle-augmented ATC daily dataset
├── src/
│   ├── __init__.py
│   ├── data_loader.py                 # Schema validation, type casting & quality checks
│   ├── features.py                    # Anti-leakage lags, rolling windows, and cyclical calendar features
│   ├── evaluate.py                    # Metric engine: MAE, RMSE, WAPE, Precision, Recall, F1, Cost
│   ├── train.py                       # Chronological split, training pipeline & artifact serialization
│   └── models/
│       ├── __init__.py
│       ├── baselines.py               # Naive last-value, moving average & seasonal naive baselines
│       ├── demand_model.py            # Ridge, Random Forest & Gradient Boosting demand forecasters
│       └── risk_classifier.py         # Mechanistic + ML batch expiry risk engine
├── app/
│   ├── __init__.py
│   ├── api.py                         # FastAPI REST service (/predict/demand, /batches/risk-assessment, serves Web UI)
│   └── dashboard.py                   # Streamlit interactive decision-support application
├── frontend/
│   ├── index.html                     # Enterprise single-page decision support UI (Tailwind CSS, Chart.js)
│   ├── app.js                         # Reactive application logic, charts, triage tables & what-if engine
│   └── style.css                      # Modern dark/light design system, glassmorphism & risk badges
├── models/
│   ├── demand_forecaster.joblib       # Serialized champion demand forecasting model
│   ├── risk_classifier.joblib        # Serialized batch expiry risk classification model
│   └── metadata.json                  # Model version, feature columns, metrics & operational disclaimers
├── notebooks/
│   └── 01_eda_and_feature_engineering.ipynb # Full EDA, leakage verification & training walkthrough
├── tests/
│   ├── __init__.py
│   ├── test_data_pipeline.py          # Data schema, negative value checks & chronological split tests
│   ├── test_model_inference.py        # Uncertainty bounds & triage logic tests
│   └── test_api.py                    # FastAPI endpoint integration tests
├── docs/
│   ├── TECHNICAL_REPORT.md            # Comprehensive 10-page technical report covering all rubric criteria
│   ├── ARCHITECTURE.md                # System diagrams, inference sequences & data contracts
│   └── SUBMISSION_FORM.md             # Pre-filled submission form ready for portal upload
├── requirements.txt                   # Pinned production dependencies
├── .env.example                       # Environment configuration template
├── .gitignore
└── README.md                          # Quickstart guide & documentation overview
```

---

## 🎯 100-Mark Rubric Cross-Reference

| Rubric Criterion | Marks | Evidence in Repository |
| :--- | :---: | :--- |
| **Problem framing, data sourcing & EDA** | 15 | Documented in `docs/TECHNICAL_REPORT.md` (Sec 1-2), `data/synthetic_generator.py`, and `notebooks/01_eda_and_feature_engineering.ipynb`. |
| **Baseline and model development** | 25 | 3 baselines in `src/models/baselines.py`, 3 candidate ML models in `src/models/demand_model.py`, feature engineering in `src/features.py`. |
| **Validation and metrics** | 20 | Strict chronological split in `src/data_loader.py`, WAPE/MAE/RMSE & Precision/Recall in `src/evaluate.py`. |
| **Inference interface** | 15 | Live FastAPI REST API in `app/api.py` and interactive Streamlit UI in `app/dashboard.py`. |
| **Explainability and responsible use** | 10 | Tree feature importances in `app/dashboard.py`, error analysis in `docs/TECHNICAL_REPORT.md`, persistent advisory disclaimers. |
| **Reproducibility, tests and docs** | 15 | Fixed random seeds (`42`), `pytest tests/`, `requirements.txt`, `docs/ARCHITECTURE.md`, and complete `README.md`. |

---

## ⚖️ License & Ethical Declarations
- **Advisory Constraint**: Outputs provide supply-chain decision support only and never clinical medication or prescribing guidance.
- **Privacy Assurance**: No patient-identifiable data or protected medical records were used.
- **Attribution**: Based on public ATC classification principles and synthetic simulations designed for Algions AI Labs.
"# Algions" 
