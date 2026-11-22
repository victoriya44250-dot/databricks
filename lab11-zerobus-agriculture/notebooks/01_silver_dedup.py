
# Databricks notebook source
# Lab 11: Bronze to Silver — idempotent processing

dbutils.widgets.text("catalog", "dbr_dev_ua5816bd")
dbutils.widgets.text("schema", "viktoriia_kalenichenko_lab11")

dbutils.widgets.text("bronze_table", "bronze_agriculture_events")
dbutils.widgets.text("silver_table", "silver_agriculture_events")

dbutils.widgets.text(
    "checkpoint_path",
    "/Volumes/dbr_dev_ua5816bd/viktoriia_kalenichenko_lab11/checkpoints/silver_agriculture_events"
)

# COMMAND ----------
from delta.tables import DeltaTable
from pyspark.sql import functions as F, Window

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

BRONZE = f"{CATALOG}.{SCHEMA}.{dbutils.widgets.get('bronze_table')}"
SILVER = f"{CATALOG}.{SCHEMA}.{dbutils.widgets.get('silver_table')}"

CHECKPOINT = dbutils.widgets.get("checkpoint_path")

# COMMAND ----------
def merge_batch(batch_df, batch_id):
    window = Window.partitionBy("event_id").orderBy("producer_sent_at")

    deduped = (
        batch_df
        .withColumn("rn", F.row_number().over(window))
        .filter(F.col("rn") == 1)
        .drop("rn")
        .withColumn("processed_at", F.current_timestamp())
    )

    (
        DeltaTable.forName(spark, SILVER)
        .alias("target")
        .merge(
            deduped.alias("source"),
            "target.event_id = source.event_id"
        )
        .whenNotMatchedInsertAll()
        .execute()
    )

# COMMAND ----------
(
    spark.readStream.table(BRONZE)
    .writeStream
    .foreachBatch(merge_batch)
    .option("checkpointLocation", CHECKPOINT)
    .trigger(availableNow=True)
    .start()
    .awaitTermination()
)