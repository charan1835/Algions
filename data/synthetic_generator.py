"""
Synthetic and Kaggle-Augmented Data Generator for Pharmacy Demand & Expiry Risk Forecasting.
Generates reproducible datasets with realistic pharmaceutical demand, seasonality,
batch lifecycles, shelf-life degradation, and stock balance tracking.
"""

import os
import argparse
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

def generate_weekly_synthetic_data(output_path="data/processed/pharmacy_demand_expiry_data.csv", seed=42):
    """
    Generates 2 years of weekly pharmacy product and batch inventory records.
    Covers antibiotics, chronic care, analgesics, antihistamines with seasonal patterns.
    """
    np.random.seed(seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    products = [
        {"id": "PROD_001", "name": "Amoxicillin 500mg", "category": "Antibiotic", "base_demand": 65, "seasonality": "winter", "unit_price": 12.50},
        {"id": "PROD_002", "name": "Metformin 500mg", "category": "Chronic Care", "base_demand": 140, "seasonality": "none", "unit_price": 8.20},
        {"id": "PROD_003", "name": "Paracetamol 650mg", "category": "Analgesic", "base_demand": 220, "seasonality": "monsoon", "unit_price": 3.50},
        {"id": "PROD_004", "name": "Cetirizine 10mg", "category": "Antihistamine", "base_demand": 55, "seasonality": "spring", "unit_price": 6.00},
        {"id": "PROD_005", "name": "Atorvastatin 10mg", "category": "Chronic Care", "base_demand": 115, "seasonality": "none", "unit_price": 15.00},
        {"id": "PROD_006", "name": "Azithromycin 500mg", "category": "Antibiotic", "base_demand": 50, "seasonality": "winter", "unit_price": 22.00}
    ]

    # Timeline: 104 weeks (Jan 2024 to Dec 2025)
    start_date = datetime(2024, 1, 1)
    weekly_dates = [start_date + timedelta(weeks=i) for i in range(104)]

    dataset_rows = []
    batch_counter = 101

    for prod in products:
        # 5 staggered batches per product to ensure continuous inventory overlap
        for batch_idx in range(5):
            batch_id = f"BAT_{prod['id'][-3:]}_{batch_counter}"
            batch_counter += 1

            # Batch manufacture offset
            mfg_offset_weeks = (batch_idx * 20) + int(np.random.randint(-2, 3))
            mfg_date = start_date + timedelta(weeks=mfg_offset_weeks)
            # Staggered shelf life (6, 12, 18, 24 months)
            shelf_life_months = int(np.random.choice([6, 12, 18, 24], p=[0.25, 0.35, 0.25, 0.15]))
            exp_date = mfg_date + timedelta(days=int(shelf_life_months * 30.44))

            # Stock sizing: 30% of batches receive an overstock buffer simulating procurement variance
            overstock_factor = float(np.random.choice([0.75, 0.95, 1.25, 1.60], p=[0.30, 0.40, 0.20, 0.10]))
            total_active_weeks = int(shelf_life_months * 4.3)
            expected_total_sales = prod["base_demand"] * total_active_weeks
            initial_stock = max(250, int(expected_total_sales * overstock_factor))
            current_stock = initial_stock

            batch_timeline = []

            for date in weekly_dates:
                # Active batch window
                if date < mfg_date or date > (exp_date + timedelta(days=21)):
                    continue

                # Seasonality factor
                month = date.month
                season_mult = 1.0
                if prod["seasonality"] == "monsoon" and month in [6, 7, 8, 9]:
                    season_mult = 1.65
                elif prod["seasonality"] == "winter" and month in [11, 12, 1, 2]:
                    season_mult = 1.50
                elif prod["seasonality"] == "spring" and month in [3, 4, 5]:
                    season_mult = 1.30

                # Noise & weekly demand
                noise = np.random.normal(0, prod["base_demand"] * 0.15)
                weekly_demand = int(max(4, (prod["base_demand"] * season_mult) + noise))

                # Sales bounded by current stock
                units_sold = min(current_stock, weekly_demand) if current_stock > 0 else 0
                current_stock -= units_sold

                days_to_expiry = (exp_date - date).days

                batch_timeline.append({
                    "Date": date.strftime("%Y-%m-%d"),
                    "Week_Index": (date - start_date).days // 7,
                    "Product_ID": prod["id"],
                    "Product_Name": prod["name"],
                    "Category": prod["category"],
                    "Unit_Price": prod["unit_price"],
                    "Batch_ID": batch_id,
                    "Manufacture_Date": mfg_date.strftime("%Y-%m-%d"),
                    "Expiry_Date": exp_date.strftime("%Y-%m-%d"),
                    "Initial_Stock": initial_stock,
                    "Units_Sold": units_sold,
                    "Stock_Balance": max(0, current_stock),
                    "Days_To_Expiry": days_to_expiry,
                    "Is_Expired": int(days_to_expiry <= 0)
                })

            # Ground truth: Did this batch actually expire with unsold stock?
            final_stock_at_expiry = max(0, current_stock)
            batch_wasted = 1 if final_stock_at_expiry > 0 else 0

            # Attach stochastic ground-truth risk label:
            # At-risk if batch is within 60 days of expiry AND ultimately spoils with unsold stock
            for r in batch_timeline:
                r["Is_At_Risk"] = int(r["Days_To_Expiry"] <= 60 and batch_wasted == 1)
                dataset_rows.extend([r])

    df = pd.DataFrame(dataset_rows)
    df.sort_values(by=["Product_ID", "Date", "Batch_ID"], inplace=True)
    df.to_csv(output_path, index=False)
    print(f"[OK] Generated {len(df)} records -> {output_path}")
    return df

def generate_augmented_kaggle_data(raw_path="data/raw/salesdaily.csv", 
                                   output_path="data/processed/augmented_pharmacy_data.csv", 
                                   seed=42):
    """
    Augments Kaggle Pharma dataset (or creates high-fidelity fallback).
    Maps ATC drug classes to clinical categories and attaches synthetic batch lifecycles.
    """
    np.random.seed(seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if os.path.exists(raw_path):
        df_raw = pd.read_csv(raw_path)
        print(f"[INFO] Loaded existing Kaggle source '{raw_path}' with {len(df_raw)} records.")
    else:
        print(f"[INFO] '{raw_path}' not found. Generating compliant Kaggle ATC schema (2014-2019)...")
        dates = pd.date_range(start="2014-01-01", end="2019-10-31", freq="D")
        df_raw = pd.DataFrame({"datum": dates})
        atc_categories = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]
        for cat in atc_categories:
            base_lam = np.random.randint(6, 28)
            # Add mild annual seasonality
            season_component = 1.0 + 0.3 * np.sin(2 * np.pi * dates.dayofyear / 365.25)
            df_raw[cat] = np.random.poisson(lam=base_lam * season_component)

    date_col = "datum" if "datum" in df_raw.columns else df_raw.columns[0]
    df_raw["Date"] = pd.to_datetime(df_raw[date_col])

    atc_cols = [c for c in ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"] if c in df_raw.columns]
    df_long = df_raw.melt(
        id_vars=["Date"],
        value_vars=atc_cols,
        var_name="Product_ID",
        value_name="Units_Sold"
    ).sort_values(by=["Product_ID", "Date"]).reset_index(drop=True)

    category_map = {
        "M01AB": ("Anti-inflammatory (Acetic)", "Anti-inflammatory", 14.50),
        "M01AE": ("Anti-inflammatory (Propionic)", "Anti-inflammatory", 11.00),
        "N02BA": ("Analgesic (Salicylic)", "Analgesics", 4.20),
        "N02BE": ("Analgesic (Paracetamol)", "Analgesics", 3.80),
        "N05B": ("Anxiolytics", "Psycholeptics", 19.50),
        "N05C": ("Hypnotics & Sedatives", "Psycholeptics", 22.00),
        "R03": ("Airway Disease Meds", "Respiratory", 31.00),
        "R06": ("Antihistamines", "Respiratory", 7.50)
    }

    df_long["Product_Name"] = df_long["Product_ID"].map(lambda x: category_map.get(x, (x, "General", 10.0))[0])
    df_long["Category"] = df_long["Product_ID"].map(lambda x: category_map.get(x, (x, "General", 10.0))[1])
    df_long["Unit_Price"] = df_long["Product_ID"].map(lambda x: category_map.get(x, (x, "General", 10.0))[2])

    augmented_rows = []
    batch_counter = 2000

    for product_id, group in df_long.groupby("Product_ID"):
        group = group.sort_values("Date").reset_index(drop=True)
        min_date = group["Date"].min()
        max_date = group["Date"].max()

        current_mfg = min_date
        while current_mfg < max_date:
            batch_id = f"BAT_{product_id}_{batch_counter}"
            batch_counter += 1

            shelf_life_months = int(np.random.choice([12, 18, 24]))
            expiry_date = current_mfg + timedelta(days=int(shelf_life_months * 30.44))

            batch_sales = group[(group["Date"] >= current_mfg) & (group["Date"] <= expiry_date)]["Units_Sold"].sum()
            initial_stock = int(batch_sales * np.random.uniform(0.85, 1.25)) + 50
            current_stock = initial_stock

            active_mask = (group["Date"] >= current_mfg) & (group["Date"] <= expiry_date)
            active_days = group[active_mask].copy()

            for _, row in active_days.iterrows():
                units = min(current_stock, int(row["Units_Sold"]))
                current_stock -= units
                days_to_exp = (expiry_date - row["Date"]).days

                augmented_rows.append({
                    "Date": row["Date"].strftime("%Y-%m-%d"),
                    "Product_ID": product_id,
                    "Product_Name": row["Product_Name"],
                    "Category": row["Category"],
                    "Unit_Price": row["Unit_Price"],
                    "Batch_ID": batch_id,
                    "Manufacture_Date": current_mfg.strftime("%Y-%m-%d"),
                    "Expiry_Date": expiry_date.strftime("%Y-%m-%d"),
                    "Initial_Stock": initial_stock,
                    "Units_Sold": units,
                    "Stock_Balance": max(0, current_stock),
                    "Days_To_Expiry": days_to_exp,
                    "Is_Expired": int(days_to_exp <= 0),
                    "Is_At_Risk": int(days_to_exp <= 60 and current_stock > 0)
                })

            current_mfg += timedelta(days=180)

    final_df = pd.DataFrame(augmented_rows)
    final_df.to_csv(output_path, index=False)
    print(f"[OK] Generated {len(final_df)} records -> {output_path}")
    return final_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic or augmented pharma datasets.")
    parser.add_argument("--mode", choices=["all", "weekly", "kaggle"], default="all")
    args = parser.parse_args()

    if args.mode in ["all", "weekly"]:
        generate_weekly_synthetic_data()
    if args.mode in ["all", "kaggle"]:
        generate_augmented_kaggle_data()
