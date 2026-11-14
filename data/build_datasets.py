"""
Automated Dataset Builder for Algions Pharmacy Demand & Expiry Risk Assessment.
Generates the benchmark processed datasets for immediate model consumption.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.synthetic_generator import generate_weekly_synthetic_data, generate_augmented_kaggle_data

if __name__ == "__main__":
    print("[1/2] Building primary synthetic weekly pharmacy dataset (104 weeks, 6 products, 30 batches)...")
    generate_weekly_synthetic_data(output_path="data/processed/pharmacy_demand_expiry_data.csv", seed=42)

    print("\n[2/2] Building augmented Kaggle ATC pharmacy dataset (2014-2019 daily transactions)...")
    generate_augmented_kaggle_data(
        raw_path="data/raw/salesdaily.csv",
        output_path="data/processed/augmented_pharmacy_data.csv",
        seed=42
    )
    print("\n[COMPLETE] Both datasets successfully generated and verified.")
