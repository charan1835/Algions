import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set seed for reproducible synthetic data
np.random.seed(42)

# 1. Define product catalog with baseline demand and seasonality rules
products = [
    {"id": "PROD_001", "name": "Amoxicillin 500mg", "category": "Antibiotic", "base_demand": 60, "seasonality": "winter"},
    {"id": "PROD_002", "name": "Metformin 500mg", "category": "Chronic Care", "base_demand": 140, "seasonality": "none"},
    {"id": "PROD_003", "name": "Paracetamol 650mg", "category": "Analgesic", "base_demand": 220, "seasonality": "monsoon"},
    {"id": "PROD_004", "name": "Cetirizine 10mg", "category": "Antihistamine", "base_demand": 50, "seasonality": "spring"},
    {"id": "PROD_005", "name": "Atorvastatin 10mg", "category": "Chronic Care", "base_demand": 110, "seasonality": "none"},
    {"id": "PROD_006", "name": "Azithromycin 500mg", "category": "Antibiotic", "base_demand": 45, "seasonality": "winter"}
]

# 2. Timeline: 2 Years of weekly data (104 weeks)
start_date = datetime(2024, 1, 1)
weekly_dates = [start_date + timedelta(weeks=i) for i in range(104)]

dataset_rows = []
batch_counter = 101

# 3. Generate batch records & sales timeline
for prod in products:
    # Each product gets 4 batches overlapping across the 2-year timeline
    for batch_idx in range(4):
        batch_id = f"BAT_{prod['id'][-3:]}_{batch_counter}"
        batch_counter += 1
        
        # Batch lifecycle metadata
        mfg_offset_weeks = (batch_idx * 22) + np.random.randint(-2, 3)
        mfg_date = start_date + timedelta(weeks=mfg_offset_weeks)
        shelf_life_months = np.random.choice([12, 18, 24])
        exp_date = mfg_date + timedelta(days=int(shelf_life_months * 30.44))
        
        initial_stock = int(np.random.randint(400, 1200))
        current_stock = initial_stock
        
        for date in weekly_dates:
            # Skip if batch was not manufactured yet or was disposed post-expiry
            if date < mfg_date or date > (exp_date + timedelta(days=30)):
                continue
            
            # Apply seasonal multiplier
            month = date.month
            season_mult = 1.0
            if prod["seasonality"] == "monsoon" and month in [6, 7, 8, 9]:
                season_mult = 1.75
            elif prod["seasonality"] == "winter" and month in [11, 12, 1]:
                season_mult = 1.50
            elif prod["seasonality"] == "spring" and month in [2, 3, 4]:
                season_mult = 1.35
            
            # Calculate sales demand with random variation
            noise = np.random.normal(0, prod["base_demand"] * 0.15)
            weekly_demand = int(max(5, (prod["base_demand"] * season_mult) + noise))
            
            # Actual units sold cannot exceed available stock
            units_sold = min(current_stock, weekly_demand) if current_stock > 0 else 0
            current_stock -= units_sold
            
            days_to_expiry = (exp_date - date).days
            
            dataset_rows.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Product_ID": prod["id"],
                "Product_Name": prod["name"],
                "Category": prod["category"],
                "Batch_ID": batch_id,
                "Manufacture_Date": mfg_date.strftime("%Y-%m-%d"),
                "Expiry_Date": exp_date.strftime("%Y-%m-%d"),
                "Initial_Stock": initial_stock,
                "Units_Sold": units_sold,
                "Stock_Balance": current_stock,
                "Days_To_Expiry": days_to_expiry
            })

# 4. Save to CSV
df = pd.DataFrame(dataset_rows)
df.to_csv("pharmacy_demand_expiry_data.csv", index=False)

print(f"Data generation complete! Successfully saved {len(df)} records to 'pharmacy_demand_expiry_data.csv'.")
