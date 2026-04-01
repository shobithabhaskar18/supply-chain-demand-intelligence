"""
Supply Chain Demand Intelligence Platform
Demand Forecasting — Fixed Version
Author: Shobitha Bhaskar
"""

import pandas as pd
import numpy as np
import sqlite3
import json
import os
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

DB_PATH = "data/supply_chain.db"
OUTPUT_PATH = "data/forecast_output.json"


def load_fact_table():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM fact_orders", conn)
    conn.close()
    print(f"[FORECAST] Loaded {len(df):,} rows from fact_orders")
    return df


def build_monthly_demand_series(df):
    sales_col = next((c for c in df.columns if "sales" in c or "revenue" in c or "amount" in c), None)
    month_col = "order_month"
    year_col = "order_year"

    if not sales_col or month_col not in df.columns:
        print("[FORECAST] Cannot build time series — missing columns")
        return None, None

    monthly = (
        df.groupby([year_col, month_col])[sales_col]
        .sum()
        .reset_index()
        .sort_values([year_col, month_col])
    )
    monthly["period"] = monthly[year_col].astype(str) + "-" + monthly[month_col].astype(str).str.zfill(2)
    monthly["t"] = range(len(monthly))
    print(f"[FORECAST] Monthly demand series: {len(monthly)} periods")
    return monthly, sales_col


def train_forecast_model(monthly, sales_col):
    X = monthly[["t"]].values
    y_vals = monthly[sales_col].values.copy()

    model = LinearRegression()
    model.fit(X, y_vals)

    last_t = monthly["t"].max()
    future_t = np.array([[last_t + i] for i in range(1, 7)])
    forecast = model.predict(future_t)

    last_year = int(monthly["order_year"].max())
    last_month = int(monthly["order_month"].max())
    future_periods = []
    yr, mo = last_year, last_month
    for _ in range(6):
        mo += 1
        if mo > 12:
            mo = 1
            yr += 1
        future_periods.append(f"{yr}-{str(mo).zfill(2)}")

    forecast_df = pd.DataFrame({
        "period": future_periods,
        "forecast_sales": forecast.round(2),
        "type": "forecast"
    })

    historical_df = monthly[["period", sales_col]].copy()
    historical_df.columns = ["period", "actual_sales"]
    historical_df["type"] = "actual"

    in_sample = model.predict(X)
    mae = mean_absolute_error(y_vals, in_sample)
    r2 = r2_score(y_vals, in_sample)
    print(f"[FORECAST] Linear Regression — MAE: {mae:,.0f} | R²: {r2:.3f}")

    return historical_df, forecast_df, {"mae": round(mae, 2), "r2": round(r2, 3)}


def train_ml_model(df):
    sales_col = next((c for c in df.columns if "sales" in c or "revenue" in c or "amount" in c), None)
    if not sales_col:
        return None

    feature_cols = [c for c in ["order_month", "order_quarter", "order_week", "order_year"] if c in df.columns]

    if "stockout_risk_tier" in df.columns:
        le = LabelEncoder()
        df["stockout_risk_tier_enc"] = le.fit_transform(df["stockout_risk_tier"].astype(str))
        feature_cols.append("stockout_risk_tier_enc")

    X = df[feature_cols].dropna()
    y_vals = df.loc[X.index, sales_col].values

    X_train, X_test, y_train, y_test = train_test_split(X, y_vals, test_size=0.2, random_state=42)

    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"[FORECAST] Random Forest — MAE: {mae:,.0f} | RMSE: {rmse:,.0f} | R²: {r2:.3f}")

    importance = dict(zip(feature_cols, rf.feature_importances_.round(4)))
    return {"mae": round(mae, 2), "rmse": round(rmse, 2), "r2": round(r2, 3), "feature_importance": importance}


def compute_kpis(df):
    sales_col = next((c for c in df.columns if "sales" in c or "revenue" in c or "amount" in c), None)
    profit_col = next((c for c in df.columns if "profit" in c and "margin" not in c and "pct" not in c), None)
    qty_col = next((c for c in df.columns if "qty" in c or "quantity" in c or "units" in c), None)

    kpis = {}
    if sales_col:
        kpis["total_revenue"] = round(float(df[sales_col].sum()), 2)
        kpis["avg_monthly_revenue"] = round(float(df.groupby(["order_year", "order_month"])[sales_col].sum().mean()), 2)
    if profit_col:
        kpis["total_profit"] = round(float(df[profit_col].sum()), 2)
    if qty_col:
        kpis["total_units_sold"] = int(df[qty_col].sum())
    if "delivery_delay_days" in df.columns:
        kpis["avg_delivery_delay_days"] = round(float(df["delivery_delay_days"].mean()), 1)
        kpis["late_delivery_rate_pct"] = round(float(df["is_late_delivery"].mean() * 100), 1)
    if "stockout_risk_tier" in df.columns:
        risk_counts = df["stockout_risk_tier"].value_counts().to_dict()
        kpis["stockout_risk_distribution"] = {str(k): int(v) for k, v in risk_counts.items()}
    if "profit_margin_pct" in df.columns:
        kpis["avg_profit_margin_pct"] = round(float(df["profit_margin_pct"].median()), 1)

    return kpis


def compute_regional_breakdown(df):
    region_col = next((c for c in df.columns if "region" in c or "market" in c or "country" in c), None)
    sales_col = next((c for c in df.columns if "sales" in c or "revenue" in c or "amount" in c), None)

    if not region_col or not sales_col:
        return []

    agg_dict = {"total_sales": (sales_col, "sum"), "order_count": (sales_col, "count")}
    if "delivery_delay_days" in df.columns:
        agg_dict["avg_delay"] = ("delivery_delay_days", "mean")
        agg_dict["late_rate"] = ("is_late_delivery", "mean")

    grp = df.groupby(region_col).agg(**agg_dict).reset_index()
    grp["total_sales"] = grp["total_sales"].round(2)
    if "avg_delay" in grp.columns:
        grp["avg_delay"] = grp["avg_delay"].round(1)
        grp["late_rate_pct"] = (grp["late_rate"] * 100).round(1)

    return grp.sort_values("total_sales", ascending=False).head(15).to_dict(orient="records")


def run_forecasting():
    print("\n" + "="*60)
    print("  SUPPLY CHAIN DEMAND INTELLIGENCE — FORECASTING")
    print("="*60 + "\n")

    if not os.path.exists(DB_PATH):
        print("[ERROR] Database not found. Run etl_pipeline.py first.")
        return

    df = load_fact_table()
    monthly, sales_col = build_monthly_demand_series(df)
    historical_df, forecast_df, lr_metrics = train_forecast_model(monthly, sales_col)
    rf_metrics = train_ml_model(df)
    kpis = compute_kpis(df)
    regional = compute_regional_breakdown(df)

    forecast_series = []
    for _, row in historical_df.iterrows():
        forecast_series.append({"period": row["period"], "actual_sales": row["actual_sales"], "forecast_sales": None})
    for _, row in forecast_df.iterrows():
        forecast_series.append({"period": row["period"], "actual_sales": None, "forecast_sales": row["forecast_sales"]})

    output = {
        "kpis": kpis,
        "forecast_series": forecast_series,
        "model_metrics": {"linear_regression": lr_metrics, "random_forest": rf_metrics},
        "regional_breakdown": regional,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n[FORECAST] Output saved to {OUTPUT_PATH}")
    print("\nKey KPIs:")
    for k, v in kpis.items():
        print(f"  {k}: {v}")
    print("\n[FORECAST] Complete.\n")


if __name__ == "__main__":
    run_forecasting()
