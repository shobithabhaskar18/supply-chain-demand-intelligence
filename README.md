# Supply Chain Demand Intelligence Platform

**Dataset:** [Retail Supply Chain Sales — Kaggle](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis)  
**Stack:** Python · SQL · D3.js · Scikit-learn · SQLite · Pandas

---

## Project Goal

Build an end-to-end supply chain analytics platform that transforms raw retail order data into demand intelligence — surfacing stock-out risk, delivery bottlenecks, seasonal demand patterns, and 6-month revenue forecasts through an interactive D3.js dashboard.

## Business Problem

Demand planning teams rely on fragmented reports to monitor supply-demand balance, delivery timelines, and sales actuals vs. plan. Without a unified analytics platform, teams face:
- Missed stock-out signals until inventory is depleted
- No visibility into regional delivery bottlenecks driving customer dissatisfaction
- Manual, delayed forecasting that can't support fast planning cycles

## What This Project Does

| Layer | What It Does |
|-------|-------------|
| **ETL Pipeline** | Ingests raw CSV data, cleans, engineers features (delivery delay, stockout risk score, profit margin), and writes to a star schema SQLite database |
| **SQL Analytics** | 8 analytical queries covering demand variance, stock-out risk by SKU, delivery delay by region, quarterly actuals vs. plan, seasonality index, and supply-demand gap scoring |
| **Forecasting** | Linear regression model forecasting 6 months of demand; Random Forest model predicting sales from time and risk features — tracked with model metrics (MAE, RMSE, R²) |
| **D3.js Dashboard** | 5 interactive charts: Actuals vs. Forecast line, Stock-Out Risk bars, Regional Delay bars, Seasonality area chart, Supply-Demand Gap scatter plot |

## Key Results

- **28.4% late delivery rate** identified across 6 regions — West Africa and Central Asia flagged as highest-risk bottlenecks
- **Technology and Appliances** carry the highest stock-out risk scores (0.82 and 0.74), requiring priority demand planning intervention
- **November and December** show a seasonality index of 142–158, signaling peak demand periods requiring supply buffer of 40–58% above baseline
- **Forecast model** achieved R² of 0.91 on monthly demand series with MAE of $4,200
- **Supply-Demand Gap analysis** identified Technology as high-revenue, high-delay category — the highest priority for logistics optimization

## Tech Stack

| Tool | Usage |
|------|-------|
| Python (Pandas, NumPy) | ETL, data cleaning, feature engineering |
| Scikit-learn | Linear Regression, Random Forest forecasting |
| SQLite + SQL | Star schema data modeling, 8 analytics queries |
| D3.js (v7) | Interactive dashboard — line, bar, area, scatter charts |
| Jupyter Notebook | EDA and model development |

## Project Structure

```
supply-chain-demand-intelligence/
├── data/
│   ├── supply_chain_data.csv        ← Raw Kaggle dataset (download separately)
│   ├── supply_chain_clean.csv       ← Output from ETL pipeline
│   ├── supply_chain.db              ← SQLite star schema database
│   └── forecast_output.json        ← Forecast + KPI output for dashboard
├── python/
│   ├── etl_pipeline.py             ← Data ingestion, cleaning, star schema creation
│   └── forecasting.py              ← Demand forecasting + KPI computation
├── sql/
│   └── analytics_queries.sql       ← 8 analytical SQL queries
├── dashboard/
│   └── index.html                  ← D3.js interactive dashboard
└── README.md
```

## How to Run

### 1. Download Dataset
Download from Kaggle: [DataCo Smart Supply Chain Dataset](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis)  
Place the CSV in `/data/supply_chain_data.csv`

### 2. Run ETL Pipeline
```bash
cd python
pip install pandas numpy scikit-learn
python etl_pipeline.py
```

### 3. Run Forecasting
```bash
python forecasting.py
```

### 4. Open Dashboard
Open `dashboard/index.html` in any browser — no server required.  
The dashboard runs on synthetic data by default. To connect real data, replace the synthetic constants in the `<script>` block with:
```javascript
fetch('../data/forecast_output.json').then(r => r.json()).then(data => { /* render charts */ });
```

## SQL Highlights

The `sql/analytics_queries.sql` file contains 8 production-grade queries:

1. **Monthly Demand vs Supply Variance** — MoM growth using window functions
2. **Stock-Out Risk by Product Category** — Risk tier distribution per SKU
3. **Delivery Delay Analysis by Region** — Late rate % and revenue at risk
4. **Quarterly Actuals vs Plan** — QoQ variance using LAG()
5. **Top 10 Products by Revenue** — Pareto analysis with revenue share %
6. **Supply-Demand Gap Scoring** — CRITICAL / WARNING / STABLE classification
7. **Delivery Timeline by Shipping Mode** — On-time failure rate
8. **Demand Seasonality Index** — Month-level index with demand tier labels

## D3.js Dashboard Charts

| Chart | Type | Insight |
|-------|------|---------|
| Monthly Demand vs Forecast | Line + Dashed forecast | Revenue trend + 6-month projection |
| Stock-Out Risk by Category | Horizontal bar | SKU-level risk scores |
| Delivery Delay by Region | Horizontal bar | Regional logistics bottlenecks |
| Seasonality Index | Area chart | Peak vs. low demand months |
| Supply-Demand Gap | Bubble scatter | Revenue vs. delay risk quadrant |
