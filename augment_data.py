import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set seed for reproducible synthetic batch overlay
np.random.seed(42)

def augment_kaggle_pharma_data(file_path="salesdaily.csv"):
    try:
        # Load Kaggle daily sales dataset
        df_raw = pd.read_csv(file_path)
        print(f"Successfully loaded '{file_path}' with {len(df_raw)} daily records.")
    except FileNotFoundError:
        print(f"Warning: '{file_path}' not found. Generating mock structure based on Kaggle schema...")
        # Fallback simulation matching Kaggle schema (2014 to 2019)
        dates = pd.date_range(start="2014-01-01", end="2019-10-31", freq="D")
        df_raw = pd.DataFrame({"datum": dates})
        atc_categories = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]
        for cat in atc_categories:
            df_raw[cat] = np.random.poisson(lam=np.random.randint(5, 25), size=len(dates))

    # Identify date column (datum in Kaggle dataset)
    date_col = "datum" if "datum" in df_raw.columns else df_raw.columns[0]
    df_raw["Date"] = pd.to_datetime(df_raw[date_col])

    # 1. Unpivot/Melt drug categories into a tidy format
    atc_cols = [c for c in ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"] if c in df_raw.columns]
    
    df_long = df_raw.melt(
        id_vars=["Date"], 
        value_vars=atc_cols, 
        var_name="Product_ID", 
        value_name="Units_Sold"
    ).sort_values(by=["Product_ID", "Date"]).reset_index(drop=True)

    # Map ATC codes to human-readable names & categories
    category_map = {
        "M01AB": ("Anti-inflammatory (Acetic)", "Anti-inflammatory"),
        "M01AE": ("Anti-inflammatory (Propionic)", "Anti-inflammatory"),
        "N02BA": ("Analgesic (Salicylic)", "Analgesics"),
        "N02BE": ("Analgesic (Paracetamol)", "Analgesics"),
        "N05B": ("Anxiolytics", "Psycholeptics"),
        "N05C": ("Hypnotics & Sedatives", "Psycholeptics"),
        "R03": ("Airway Disease Meds", "Respiratory"),
        "R06": ("Antihistamines", "Respiratory")
    }
    
    df_long["Product_Name"] = df_long["Product_ID"].map(lambda x: category_map.get(x, (x, "General"))[0])
    df_long["Category"] = df_long["Product_ID"].map(lambda x: category_map.get(x, (x, "General"))[1])

    # 2. Inject Batch Metadata & Stock Lifecycle
    augmented_rows = []
    batch_counter = 1000

    for product_id, group in df_long.groupby("Product_ID"):
        group = group.sort_values("Date").reset_index(drop=True)
        min_date = group["Date"].min()
        max_date = group["Date"].max()

        # Generate overlapping batch lifecycles (every ~180 days)
        current_mfg = min_date
        while current_mfg < max_date:
            batch_id = f"BAT_{product_id}_{batch_counter}"
            batch_counter += 1
            
            shelf_life_months = np.random.choice([12, 18, 24])
            expiry_date = current_mfg + timedelta(days=int(shelf_life_months * 30.44))
            
            # Estimate total demand over this batch's shelf life to set realistic initial stock
            batch_sales = group[(group["Date"] >= current_mfg) & (group["Date"] <= expiry_date)]["Units_Sold"].sum()
            initial_stock = int(batch_sales * np.random.uniform(0.85, 1.25)) + 50
            current_stock = initial_stock
            
            # Filter daily sales during batch active window
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
                    "Batch_ID": batch_id,
                    "Manufacture_Date": current_mfg.strftime("%Y-%m-%d"),
                    "Expiry_Date": expiry_date.strftime("%Y-%m-%d"),
                    "Initial_Stock": initial_stock,
                    "Units_Sold": units,
                    "Stock_Balance": max(0, current_stock),
                    "Days_To_Expiry": days_to_exp
                })

            current_mfg += timedelta(days=180)

    # 3. Final DataFrame
    final_df = pd.DataFrame(augmented_rows)
    output_filename = "augmented_pharmacy_data.csv"
    final_df.to_csv(output_filename, index=False)
    
    print(f"Successfully generated {len(final_df)} records saved to '{output_filename}'.")
    return final_df

if __name__ == "__main__":
    augment_kaggle_pharma_data("salesdaily.csv")
