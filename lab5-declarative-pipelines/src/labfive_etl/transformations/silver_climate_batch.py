
from pyspark import pipelines as dp
from pyspark.sql.functions import col, trim

# Read configuration from the Lakeflow pipeline
catalog = spark.conf.get("lab5.catalog")
bronze_schema = spark.conf.get("lab5.bronze_schema")
silver_schema = spark.conf.get("lab5.silver_schema")

# Fully qualified Unity Catalog table names
bronze_table = (
    f"{catalog}.{bronze_schema}.bronze_climate_batch"
)

silver_table = (
    f"{catalog}.{silver_schema}.silver_climate_batch"
)


@dp.materialized_view(
    name=silver_table,
    comment="Clean batch climate data with quality expectations"
)
@dp.expect_or_drop(
    "valid_area",
    "AREA IS NOT NULL AND LENGTH(TRIM(AREA)) > 0"
)
@dp.expect_or_drop(
    "valid_item",
    "ITEM IS NOT NULL AND LENGTH(TRIM(ITEM)) > 0"
)
@dp.expect_or_drop(
    "valid_year",
    "YEAR IS NOT NULL AND YEAR BETWEEN 1990 AND 2022"
)
@dp.expect_or_drop(
    "valid_yield",
    "YIELD IS NULL OR YIELD >= 0"
)
@dp.expect_or_drop(
    "valid_production",
    "PRODUCTION_QUANTITY IS NULL OR PRODUCTION_QUANTITY >= 0"
)
def silver_climate_batch():
    return (
        spark.read.table(bronze_table)
        .withColumn("AREA", trim(col("AREA")))
        .withColumn("ITEM", trim(col("ITEM")))
        .withColumn("YEAR", col("YEAR").cast("int"))
        .withColumn("YIELD", col("YIELD").cast("double"))
        .withColumn(
            "PRODUCTION_QUANTITY",
            col("PRODUCTION_QUANTITY").cast("double")
        )
    )
