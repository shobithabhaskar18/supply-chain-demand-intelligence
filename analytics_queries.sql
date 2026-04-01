-- ============================================================
-- Supply Chain Demand Intelligence Platform
-- SQL Analytics Queries
-- Author: Shobitha Bhaskar
-- ============================================================


-- ── 1. MONTHLY DEMAND vs SUPPLY VARIANCE ────────────────────
-- Tracks actual sales vs prior month to surface demand shifts

SELECT
    order_year,
    order_month,
    ROUND(SUM(sales), 2)                                          AS total_sales,
    ROUND(SUM(quantity), 0)                                       AS total_units,
    ROUND(AVG(profit_margin_pct), 1)                              AS avg_margin_pct,
    ROUND(
        SUM(sales) - LAG(SUM(sales)) OVER (ORDER BY order_year, order_month), 2
    )                                                             AS mom_sales_variance,
    ROUND(
        (SUM(sales) - LAG(SUM(sales)) OVER (ORDER BY order_year, order_month))
        / NULLIF(LAG(SUM(sales)) OVER (ORDER BY order_year, order_month), 0) * 100, 1
    )                                                             AS mom_growth_pct
FROM fact_orders
GROUP BY order_year, order_month
ORDER BY order_year, order_month;


-- ── 2. STOCK-OUT RISK BY PRODUCT CATEGORY ───────────────────
-- Identifies high-risk SKUs for demand planning intervention

SELECT
    product_type                                                  AS category,
    COUNT(*)                                                      AS total_orders,
    ROUND(SUM(sales), 2)                                          AS total_revenue,
    ROUND(AVG(stockout_risk_score), 3)                            AS avg_stockout_risk,
    SUM(CASE WHEN stockout_risk_tier = 'High' THEN 1 ELSE 0 END) AS high_risk_orders,
    ROUND(
        SUM(CASE WHEN stockout_risk_tier = 'High' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1
    )                                                             AS high_risk_pct
FROM fact_orders
GROUP BY product_type
ORDER BY avg_stockout_risk DESC;


-- ── 3. DELIVERY DELAY ANALYSIS BY REGION ────────────────────
-- Surfaces regional bottlenecks in customer delivery timelines

SELECT
    market                                                        AS region,
    COUNT(*)                                                      AS total_shipments,
    ROUND(AVG(delivery_delay_days), 1)                            AS avg_delay_days,
    MAX(delivery_delay_days)                                      AS max_delay_days,
    SUM(is_late_delivery)                                         AS late_deliveries,
    ROUND(AVG(is_late_delivery) * 100, 1)                         AS late_delivery_rate_pct,
    ROUND(SUM(sales), 2)                                          AS revenue_at_risk
FROM fact_orders
GROUP BY market
ORDER BY late_delivery_rate_pct DESC;


-- ── 4. SALES ACTUALS vs QUARTERLY PLAN TRACKING ─────────────
-- Quarter-over-quarter performance for planning team reporting

SELECT
    order_year                                                    AS year,
    order_quarter                                                 AS quarter,
    ROUND(SUM(sales), 2)                                          AS actual_sales,
    ROUND(SUM(quantity), 0)                                       AS units_sold,
    ROUND(AVG(profit_margin_pct), 1)                              AS avg_margin_pct,
    ROUND(
        SUM(sales) - LAG(SUM(sales)) OVER (ORDER BY order_year, order_quarter), 2
    )                                                             AS qoq_variance,
    ROUND(
        (SUM(sales) - LAG(SUM(sales)) OVER (ORDER BY order_year, order_quarter))
        / NULLIF(LAG(SUM(sales)) OVER (ORDER BY order_year, order_quarter), 0) * 100, 1
    )                                                             AS qoq_growth_pct
FROM fact_orders
GROUP BY order_year, order_quarter
ORDER BY order_year, order_quarter;


-- ── 5. TOP 10 PRODUCTS BY REVENUE CONTRIBUTION ──────────────
-- Pareto analysis: which SKUs drive the most revenue

SELECT
    product_name                                                  AS product,
    product_type                                                  AS category,
    COUNT(*)                                                      AS order_count,
    ROUND(SUM(sales), 2)                                          AS total_revenue,
    ROUND(SUM(quantity), 0)                                       AS total_units,
    ROUND(AVG(profit_margin_pct), 1)                              AS avg_margin_pct,
    ROUND(SUM(sales) * 100.0 / SUM(SUM(sales)) OVER (), 2)        AS revenue_share_pct
FROM fact_orders
GROUP BY product_name, product_type
ORDER BY total_revenue DESC
LIMIT 10;


-- ── 6. SUPPLY-DEMAND GAP: HIGH DEMAND, HIGH DELAY ───────────
-- Finds products with strong demand but poor delivery performance
-- These are the highest-priority items for supply chain intervention

SELECT
    product_type                                                  AS category,
    market                                                        AS region,
    ROUND(SUM(sales), 2)                                          AS total_revenue,
    ROUND(SUM(quantity), 0)                                       AS units_ordered,
    ROUND(AVG(delivery_delay_days), 1)                            AS avg_delay_days,
    ROUND(AVG(is_late_delivery) * 100, 1)                         AS late_rate_pct,
    ROUND(AVG(stockout_risk_score), 3)                            AS avg_stockout_risk,
    CASE
        WHEN AVG(delivery_delay_days) > 5 AND AVG(stockout_risk_score) > 0.5
            THEN 'CRITICAL — Intervene Now'
        WHEN AVG(delivery_delay_days) > 3 OR AVG(stockout_risk_score) > 0.5
            THEN 'WARNING — Monitor Closely'
        ELSE 'STABLE'
    END                                                           AS supply_demand_status
FROM fact_orders
GROUP BY product_type, market
ORDER BY avg_stockout_risk DESC, avg_delay_days DESC;


-- ── 7. CUSTOMER DELIVERY TIMELINE PERFORMANCE ───────────────
-- Tracks on-time vs late delivery by shipping mode

SELECT
    ship_mode                                                     AS shipping_mode,
    COUNT(*)                                                      AS total_orders,
    ROUND(AVG(delivery_delay_days), 1)                            AS avg_delay_days,
    SUM(is_late_delivery)                                         AS late_count,
    ROUND(AVG(is_late_delivery) * 100, 1)                         AS on_time_failure_pct,
    ROUND(SUM(sales), 2)                                          AS total_revenue
FROM fact_orders
GROUP BY ship_mode
ORDER BY on_time_failure_pct DESC;


-- ── 8. DEMAND SEASONALITY INDEX ─────────────────────────────
-- Month-level demand index to identify seasonal planning needs

SELECT
    order_month                                                   AS month,
    ROUND(AVG(sales), 2)                                          AS avg_monthly_sales,
    ROUND(
        AVG(sales) / AVG(AVG(sales)) OVER () * 100, 1
    )                                                             AS seasonality_index,
    CASE
        WHEN AVG(sales) / AVG(AVG(sales)) OVER () > 1.15 THEN 'Peak Demand'
        WHEN AVG(sales) / AVG(AVG(sales)) OVER () < 0.85 THEN 'Low Demand'
        ELSE 'Normal'
    END                                                           AS demand_tier
FROM fact_orders
GROUP BY order_month
ORDER BY order_month;
