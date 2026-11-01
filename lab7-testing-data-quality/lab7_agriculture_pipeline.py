from pyspark import pipelines as dp


@dp.materialized_view(name="lab7_raw_agriculture")
def raw_agriculture():
    """Create sample agriculture data for DQ testing."""

    return spark.sql("""
        SELECT 'Ukraine' AS AREA, 'Wheat' AS ITEM,
               2022 AS YEAR, 1000.0 AS PRODUCTION_QUANTITY,
               500.0 AS AREA_HARVESTED

        UNION ALL

        SELECT 'France', 'Barley', 2021, 2000.0, 800.0

        UNION ALL

        SELECT 'Germany', 'Wheat', 1800, 1500.0, 600.0

        UNION ALL

        SELECT 'Poland', 'Barley', 2022, -100.0, 300.0

        UNION ALL

        SELECT 'Spain', 'Wheat', 2020, 900.0, -50.0
    """)



from pyspark.sql import functions as F


# Data Quality rules
DQ_RULES = """
    YEAR IS NOT NULL
    AND YEAR BETWEEN 1990 AND 2022
    AND PRODUCTION_QUANTITY IS NOT NULL
    AND PRODUCTION_QUANTITY >= 0
    AND AREA_HARVESTED IS NOT NULL
    AND AREA_HARVESTED >= 0
"""


# Clean data: drop rows that fail the expectation
@dp.materialized_view(name="lab7_clean_agriculture")
@dp.expect_or_drop("valid_agriculture_data", DQ_RULES)
def clean_agriculture():
    return spark.read.table("lab7_raw_agriculture")


# Quarantine: preserve invalid rows for investigation
@dp.materialized_view(name="lab7_quarantine_agriculture")
def quarantine_agriculture():
    df = spark.read.table("lab7_raw_agriculture")

    return (
        df.filter(~F.expr(DQ_RULES))
        .withColumn(
            "failure_reason",
            F.when(
                F.col("YEAR").isNull()
                | ~F.col("YEAR").between(1990, 2022),
                "Invalid year"
            )
            .when(
                F.col("PRODUCTION_QUANTITY").isNull()
                | (F.col("PRODUCTION_QUANTITY") < 0),
                "Invalid production quantity"
            )
            .when(
                F.col("AREA_HARVESTED").isNull()
                | (F.col("AREA_HARVESTED") < 0),
                "Invalid harvested area"
            )
            .otherwise("Unknown validation error")
        )
    )
