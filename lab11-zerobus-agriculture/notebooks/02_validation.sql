-- Databricks notebook source
-- Lab 11: Validate deduplication and reconciliation

-- COMMAND ----------
-- Compare total deliveries and unique events in Bronze and Silver.
SELECT
    'bronze' AS layer,
    COUNT(*) AS total_records,
    COUNT(DISTINCT event_id) AS unique_events,
    COUNT(*) - COUNT(DISTINCT event_id) AS duplicates
FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.bronze_agriculture_events

UNION ALL

SELECT
    'silver',
    COUNT(*),
    COUNT(DISTINCT event_id),
    COUNT(*) - COUNT(DISTINCT event_id)
FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.silver_agriculture_events;

-- COMMAND ----------
-- Inspect repeated event deliveries in Bronze.
SELECT event_id, COUNT(*) AS deliveries
FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.bronze_agriculture_events
GROUP BY event_id
HAVING COUNT(*) > 1
ORDER BY event_id;

-- COMMAND ----------
-- Confirm that every unique Bronze event exists in Silver.
SELECT COUNT(*) AS missing_events
FROM (
    SELECT DISTINCT event_id
    FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.bronze_agriculture_events

    EXCEPT

    SELECT event_id
    FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.silver_agriculture_events
) AS missing;
