
import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime

RAW_DATA_PATH = "data/supply_chain_data.csv"
DB_PATH = "data/supply_chain.db"


def load_raw_data(path):
    print(f"[ETL] Loading raw data from {path}...")
    df = pd.read_csv(path, encoding='latin-1')
    print(f"[ETL] Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def clean_data(df):
    print("[ETL] Cleaning data...")

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )

    # Drop full duplicates
    before = len(df)
    df = df.drop_duplicates()
    print(f"[ETL] Removed {before - len(df)} duplicate rows")

    # Parse dates
    date_cols = [c for c in df.columns if "date" in c or "time" in c]
    for col in date_cols:
        try:
            df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
        except Exception:
            pass

    # Fill nulls in numeric cols with median
    num_cols = df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        median_val = df[col].median()
        null_count = df[col].isnull().sum()
        if null_count > 0:
            df[col] = df[col].fillna(median_val)
            print(f"[ETL] Filled {null_count} nulls in '{col}' with median={median_val:.2f}")

    # Fill nulls in string cols with 'Unknown'
    str_cols = df.select_dtypes(include=["object"]).columns
    for col in str_cols:
        df[col] = df[col].fillna("Unknown").str.strip()

    print(f"[ETL] Clean dataset: {len(df):,} rows")
    return df


def engineer_features(df):
    print("[ETL] Engineering features...")

    # Detect key columns dynamically
    cols = df.columns.tolist()

    # Sales / revenue
    sales_col = next((c for c in cols if "sales" in c or "revenue" in c or "amount" in c), None)
    # Order date
    order_date_col = next((c for c in cols if "order" in c and "date" in c), None)
    # Ship / delivery date
    ship_date_col = next((c for c in cols if "ship" in c or "delivery" in c or "dispatch" in c), None)
    # Product / category
    product_col = next((c for c in cols if "product" in c or "category" in c or "type" in c), None)
    # Region / market
    region_col = next((c for c in cols if "region" in c or "market" in c or "country" in c or "city" in c), None)
    # Quantity
    qty_col = next((c for c in cols if "qty" in c or "quantity" in c or "units" in c), None)
    # Profit
    profit_col = next((c for c in cols if "profit" in c), None)

    print(f"[ETL] Detected columns: sales={sales_col}, order_date={order_date_col}, "
          f"ship_date={ship_date_col}, product={product_col}, region={region_col}")

    # Time features
    if order_date_col and pd.api.types.is_datetime64_any_dtype(df[order_date_col]):
        df["order_year"] = df[order_date_col].dt.year
        df["order_month"] = df[order_date_col].dt.month
        df["order_quarter"] = df[order_date_col].dt.quarter
        df["order_week"] = df[order_date_col].dt.isocalendar().week.astype(int)
        df["order_dayofweek"] = df[order_date_col].dt.dayofweek

    # Delivery delay
    if order_date_col and ship_date_col:
        if (pd.api.types.is_datetime64_any_dtype(df[order_date_col]) and
                pd.api.types.is_datetime64_any_dtype(df[ship_date_col])):
            df["delivery_delay_days"] = (df[ship_date_col] - df[order_date_col]).dt.days
            df["is_late_delivery"] = (df["delivery_delay_days"] > 3).astype(int)
            late_pct = df["is_late_delivery"].mean() * 100
            print(f"[ETL] Late delivery rate: {late_pct:.1f}%")

    # Revenue per unit
    if sales_col and qty_col:
        df["revenue_per_unit"] = df[sales_col] / df[qty_col].replace(0, np.nan)

    # Profit margin
    if profit_col and sales_col:
        df["profit_margin_pct"] = (df[profit_col] / df[sales_col].replace(0, np.nan)) * 100

    # Stock-out risk score (low sales + high qty ordered = potential mismatch)
    if sales_col and qty_col:
        sales_zscore = (df[sales_col] - df[sales_col].mean()) / df[sales_col].std()
        qty_zscore = (df[qty_col] - df[qty_col].mean()) / df[qty_col].std()
        df["stockout_risk_score"] = (qty_zscore - sales_zscore).round(3)
        df["stockout_risk_tier"] = pd.cut(
            df["stockout_risk_score"],
            bins=[-np.inf, -0.5, 0.5, np.inf],
            labels=["Low", "Medium", "High"]
        )

    return df, {
        "sales_col": sales_col,
        "order_date_col": order_date_col,
        "ship_date_col": ship_date_col,
        "product_col": product_col,
        "region_col": region_col,
        "qty_col": qty_col,
        "profit_col": profit_col,
    }


def create_star_schema(df, cols, conn):
    print("[ETL] Creating star schema tables...")

    sales_col = cols["sales_col"]
    order_date_col = cols["order_date_col"]
    product_col = cols["product_col"]
    region_col = cols["region_col"]
    qty_col = cols["qty_col"]
    profit_col = cols["profit_col"]

    # dim_product
    if product_col:
        dim_product = df[[product_col]].drop_duplicates().reset_index(drop=True)
        dim_product.index.name = "product_id"
        dim_product = dim_product.reset_index()
        dim_product.to_sql("dim_product", conn, if_exists="replace", index=False)
        print(f"[ETL] dim_product: {len(dim_product)} rows")

    # dim_region
    if region_col:
        dim_region = df[[region_col]].drop_duplicates().reset_index(drop=True)
        dim_region.index.name = "region_id"
        dim_region = dim_region.reset_index()
        dim_region.to_sql("dim_region", conn, if_exists="replace", index=False)
        print(f"[ETL] dim_region: {len(dim_region)} rows")

    # dim_date
    if order_date_col and pd.api.types.is_datetime64_any_dtype(df[order_date_col]):
        dates = df[order_date_col].dropna().drop_duplicates().sort_values()
        dim_date = pd.DataFrame({
            "date": dates,
            "year": dates.dt.year,
            "quarter": dates.dt.quarter,
            "month": dates.dt.month,
            "week": dates.dt.isocalendar().week.astype(int).values,
            "day": dates.dt.day,
            "day_of_week": dates.dt.day_name(),
        })
        dim_date.to_sql("dim_date", conn, if_exists="replace", index=False)
        print(f"[ETL] dim_date: {len(dim_date)} rows")

    # fact_orders — main fact table
    fact_cols = [c for c in [
        order_date_col, product_col, region_col,
        sales_col, qty_col, profit_col,
        "delivery_delay_days", "is_late_delivery",
        "revenue_per_unit", "profit_margin_pct",
        "stockout_risk_score", "stockout_risk_tier",
        "order_year", "order_month", "order_quarter", "order_week"
    ] if c and c in df.columns]

    fact_orders = df[fact_cols].copy()
    if order_date_col in fact_orders.columns:
        fact_orders[order_date_col] = fact_orders[order_date_col].astype(str)
    fact_orders.to_sql("fact_orders", conn, if_exists="replace", index=False)
    print(f"[ETL] fact_orders: {len(fact_orders):,} rows")

    return True


def run_pipeline():
    print("\n" + "="*60)
    print("  SUPPLY CHAIN DEMAND INTELLIGENCE — ETL PIPELINE")
    print("="*60 + "\n")

    if not os.path.exists(RAW_DATA_PATH):
        print(f"[ERROR] Raw data not found at {RAW_DATA_PATH}")
        print("Please download dataset from Kaggle and place CSV idata/")
        return

    df = load_raw_data(RAW_DATA_PATH)
    df = clean_data(df)
    df, cols = engineer_features(df)

    conn = sqlite3.connect(DB_PATH)
    create_star_schema(df, cols, conn)
    conn.close()

    # Save clean data for dashboard
    df.to_csv("data/supply_chain_clean.csv", index=False)
    print(f"\n[ETL] Clean data saved tdata/supply_chain_clean.csv")
    print(f"[ETL] Star schema saved tdata/supply_chain.db")
    print("\n[ETL] Pipeline complete.\n")


if __name__ == "__main__":
    run_pipeline()
