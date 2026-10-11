
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

# Pipeline configuration
catalog = spark.conf.get("lab5.catalog")
bronze_schema = spark.conf.get("lab5.bronze_schema")
raw_volume_path = spark.conf.get("lab5.raw_volume_path")

# Destination: existing Bronze schema, new Lab 5 table
bronze_table = (
    f"{catalog}.{bronze_schema}.bronze_climate_stream"
)

# Dedicated directory for incremental CSV ingestion
source_path = (
    raw_volume_path.rstrip("/") + "/lab5-streaming/"
)


@dp.table(
    name=bronze_table,
    comment="Incremental CSV ingestion using Auto Loader"
)
def bronze_climate_stream():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.inferColumnTypes", "true")
        .load(source_path)
        .withColumn(
            "bronze_ingestion_timestamp",
            current_timestamp()
        )
    )
