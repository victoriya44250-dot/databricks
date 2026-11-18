
-- Databricks notebook source
-- Lakehouse Federation
-- Querying Azure SQL through a foreign catalog and comparing it with Delta Lake.

-- COMMAND ----------

-- 1. Query external tables

SHOW TABLES IN victoriya44250_lab10_adventureworkslt.saleslt;

SELECT CustomerID, FirstName, LastName, CompanyName
FROM victoriya44250_lab10_adventureworkslt.saleslt.customer
LIMIT 10;

-- COMMAND ----------

-- 2. Query pushdown: filtering and aggregation

-- Filter and projection pushdown
EXPLAIN FORMATTED
SELECT CustomerID, FirstName, LastName, CompanyName
FROM victoriya44250_lab10_adventureworkslt.saleslt.customer
WHERE CustomerID BETWEEN 100 AND 200;

-- Aggregation pushdown check
EXPLAIN FORMATTED
SELECT
    Status,
    COUNT(*) AS order_count,
    SUM(TotalDue) AS total_revenue
FROM victoriya44250_lab10_adventureworkslt.saleslt.salesorderheader
GROUP BY Status;

-- COMMAND ----------

-- 3. Federation vs Delta ingestion

-- Create a local Delta snapshot of external orders
CREATE OR REPLACE TABLE
dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.salesorder_snapshot
AS
SELECT
    *,
    current_timestamp() AS ingested_at
FROM victoriya44250_lab10_adventureworkslt.saleslt.salesorderheader;

-- Verify the snapshot
SELECT
    COUNT(*) AS total_orders,
    MAX(ingested_at) AS ingestion_time
FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.salesorder_snapshot;

-- COMMAND ----------

-- Compare the same aggregation using Federation and Delta

-- Federation: live Azure SQL data
SELECT
    ShipMethod,
    COUNT(*) AS order_count,
    ROUND(SUM(TotalDue), 2) AS total_revenue,
    ROUND(AVG(TotalDue), 2) AS avg_order_value
FROM victoriya44250_lab10_adventureworkslt.saleslt.salesorderheader
GROUP BY ShipMethod
ORDER BY total_revenue DESC;

-- Delta: ingested snapshot
SELECT
    ShipMethod,
    COUNT(*) AS order_count,
    ROUND(SUM(TotalDue), 2) AS total_revenue,
    ROUND(AVG(TotalDue), 2) AS avg_order_value
FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.salesorder_snapshot
GROUP BY ShipMethod
ORDER BY total_revenue DESC;

-- COMMAND ----------

-- 4. Cross-source JOIN: Azure SQL customers + Delta orders

SELECT
    c.CustomerID,
    CONCAT(c.FirstName, ' ', c.LastName) AS customer_name,
    c.CompanyName,
    COUNT(o.SalesOrderID) AS order_count,
    ROUND(SUM(o.TotalDue), 2) AS total_spent
FROM victoriya44250_lab10_adventureworkslt.saleslt.customer AS c
JOIN dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.salesorder_snapshot AS o
    ON c.CustomerID = o.CustomerID
GROUP BY
    c.CustomerID,
    c.FirstName,
    c.LastName,
    c.CompanyName
ORDER BY total_spent DESC
LIMIT 10;
