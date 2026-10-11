
from pyspark import pipelines as dp

# Read settings from the pipeline configuration
catalog = spark.conf.get("lab5.catalog")
bronze_schema = spark.conf.get("lab5.bronze_schema")
raw_volume_path = spark.conf.get("lab5.raw_volume_path")

# Destination table in the existing Bronze schema
bronze_table = (
    f"{catalog}.{bronze_schema}.bronze_climate_batch"
)

# Source CSV in the existing Unity Catalog Volume
csv_path = (
    raw_volume_path.rstrip("/")
    + "/europe_cereal_yield_climate_1990_2022.csv"
)


@dp.materialized_view(
    name=bronze_table,
    comment="Batch ingestion of cereal yield and climate CSV data"
)
def bronze_climate_batch():
    return (
        spark.read
        .format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .load(csv_path)
    )
