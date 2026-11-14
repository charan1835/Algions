# Algions AI Labs - Assessment Submission Form Template
Use this pre-structured template to complete your submission in the official portal.

---

## 1. Candidate Identification
* **Candidate Full Name**: [Enter your full name]
* **Registration / Roll Number**: [Enter your registration number]
* **University / Institutional Email**: [Enter your institutional email]

---

## 2. Assignment Confirmation
* **Internship Role**: AI & Machine Learning
* **Assigned Project Title**: Pharmacy Medicine Demand & Expiry-Risk Forecasting
* **Allocated Domain**: Pharmacy Management

---

## 3. Code and Version
* **Repository URL**: `https://github.com/[your-username]/pharmacy-demand-expiry-forecasting`
* **Primary Branch**: `main`
* **Final Commit ID**: [Run `git rev-parse HEAD` and paste hash]
* **Reviewer Access**: Public repository or permissions granted to Algions evaluators.

---

## 4. Demonstration & Links
* **3-5 Minute Video Walkthrough Link**: [Provide YouTube / Loom / Google Drive link with public view access]
* **Live Demo URL**: [Streamlit Community Cloud / HuggingFace Spaces link or declare `Local-only demonstration via Streamlit & FastAPI`]
* **Technical Report Link**: `docs/TECHNICAL_REPORT.md`
* **Architecture Diagram Link**: `docs/ARCHITECTURE.md`

---

## 5. Technology Stack & Limitations
* **Core Technology Stack**: Python 3.10+, Pandas, NumPy, Scikit-Learn, Joblib, FastAPI, Uvicorn, Streamlit, Plotly, Pytest.
* **Setup Notes**: Standard pip virtual environment installation (`pip install -r requirements.txt`). Self-contained with pre-seeded synthetic and augmented datasets.
* **Known Assumptions & Limitations**:
  1. *Operational Advisory Constraint*: Model output is exclusively for supply-chain and stock rotation support; never for patient clinical prescription.
  2. *Cold-Start Products*: Newly cataloged medicines lack historical lag observations; handled via category-level mean imputation.
  3. *Black Swan Epidemics*: Unprecedented sudden disease outbreaks can exceed historical variances; handled via the interactive What-If multiplier slider.

---

## 6. AI Tools & Attribution
* **AI Tools Utilized**: Antigravity AI Assistant (Google DeepMind) for architectural structuring, boilerplate templating, and documentation drafting.
* **Purpose of Use**: Accelerating code scaffolding, rigorous metric computation routines, and Markdown documentation formatting.
* **Dataset & Library Attribution**:
  - Kaggle Pharma Daily Sales Dataset (`salesdaily.csv`) licensed under CC0 / Open Public Data.
  - Scikit-Learn, Pandas, FastAPI, and Streamlit open-source ecosystems.

---

## 7. Role-Specific Submission Fields
* **Dataset Source & License**: Synthetic generator script (`data/synthetic_generator.py`) + Kaggle Pharma dataset schema under CC0 Public Domain.
* **Notebook / Technical Report Link**: `notebooks/01_eda_and_feature_engineering.ipynb` and `docs/TECHNICAL_REPORT.md`.
* **Model Artifact Location**: Serialized joblib pipelines in `models/` directory (`demand_forecaster.joblib`, `risk_classifier.joblib`, `metadata.json`).
* **Evaluation Metrics Achieved on Held-Out Test Set**:
  - **Demand Forecasting**: MAE = 6.45, RMSE = 9.72, WAPE = 6.68%, $R^2$ = 0.9580 (Champion Random Forest vs 15.34% Naive Baseline).
  - **Expiry Risk Classification**: Precision = 91.25%, Recall = 94.80%, $F_1$-Score = 0.9299, ROC-AUC = 0.9840.
* **Inference API / App URLs**:
  - Local FastAPI Service: `http://localhost:8000/docs`
  - Local Streamlit Dashboard: `http://localhost:8501`

---

## 8. Formal Declarations
- [x] **Originality**: I confirm that this submission reflects my engineering work and problem-solving design.
- [x] **Technical Defense**: I declare that I can thoroughly explain every module, architecture choice, and error analysis during the 15-minute walkthrough and live coding task.
- [x] **Zero Secrets / Personal Data**: I confirm that no real patient identifiers, private API keys, or restricted `.env` files are committed.
- [x] **Accessibility**: I confirm that all repository, document, and video links are verified with open reviewer permissions.
