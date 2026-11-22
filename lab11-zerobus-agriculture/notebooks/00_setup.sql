-- Databricks notebook source
-- Lab 11: Zerobus agricultural data setup

-- COMMAND ----------
CREATE SCHEMA IF NOT EXISTS
dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11;

-- COMMAND ----------
CREATE TABLE IF NOT EXISTS
dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.bronze_agriculture_events (
    event_id STRING,
    area STRING,
    item STRING,
    year INT,
    crop_yield DOUBLE,
    area_harvested DOUBLE,
    production_quantity DOUBLE,
    producer_sent_at TIMESTAMP
)
USING DELTA;

-- COMMAND ----------
CREATE TABLE IF NOT EXISTS
dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.silver_agriculture_events (
    event_id STRING NOT NULL,
    area STRING,
    item STRING,
    year INT,
    crop_yield DOUBLE,
    area_harvested DOUBLE,
    production_quantity DOUBLE,
    producer_sent_at TIMESTAMP,
    processed_at TIMESTAMP
)
USING DELTA;

-- COMMAND ----------
CREATE VOLUME IF NOT EXISTS
dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.checkpoints;
GRANT USE CATALOG ON CATALOG dbr_dev_ua5816bd TO `11b58d2f-4208-4d1f-9b5e-fdfd91843aed`;
GRANT USE SCHEMA ON SCHEMA dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11 TO `11b58d2f-4208-4d1f-9b5e-fdfd91843aed`;
GRANT SELECT, MODIFY ON TABLE dbr_dev_ua5816bd.viktoriia_kalenichenko_lab11.bronze_agriculture_events 
    TO `11b58d2f-4208-4d1f-9b5e-fdfd91843aed`;