
from typing import Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_country_name(name: Optional[str]) -> Optional[str]:
    """Remove leading and trailing spaces from a country name."""
    if name is None:
        return None

    return name.strip()


def parse_year(value: Optional[str]) -> Optional[int]:
    """Convert a year value to an integer."""
    if value is None:
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def is_valid_production(value: Optional[float]) -> bool:
    """Check whether production is non-negative."""
    if value is None:
        return False

    return value >= 0


def prepare_agriculture(df: DataFrame) -> DataFrame:
    """Clean country, crop, and year columns in a Spark DataFrame."""
    return (
        df.withColumn("AREA", F.trim(F.col("AREA")))
        .withColumn("ITEM", F.trim(F.col("ITEM")))
        .withColumn("YEAR", F.col("YEAR").cast("int"))
    )


def join_agriculture_country(
    agriculture: DataFrame,
    countries: DataFrame,
) -> DataFrame:
    """Join agriculture records with the country dimension."""
    a = agriculture.alias("a")
    c = countries.alias("c")

    return (
        a.join(
            c,
            F.trim(F.col("a.AREA")) == F.col("c.country_name"),
            "inner",
        )
        .select(
            F.col("c.country_code").alias("country_key"),
            F.col("a.AREA").alias("AREA"),
            F.col("a.ITEM").alias("ITEM"),
            F.col("a.YEAR").alias("YEAR"),
            F.col("a.PRODUCTION_QUANTITY").alias("PRODUCTION_QUANTITY"),
        )
    )
