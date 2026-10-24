
import sys
from pathlib import Path

# Add the project root to Python's import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.transformations import (
    clean_country_name,
    parse_year,
    is_valid_production,
    prepare_agriculture,
    join_agriculture_country,
)

def test_clean_country_name():
    assert clean_country_name(" Ukraine ") == "Ukraine"
    assert clean_country_name("France") == "France"
    assert clean_country_name(None) is None


def test_parse_year():
    assert parse_year("2022") == 2022
    assert parse_year("1990") == 1990
    assert parse_year("unknown") is None
    assert parse_year(None) is None


def test_is_valid_production():
    assert is_valid_production(1500) is True
    assert is_valid_production(0) is True
    assert is_valid_production(-100) is False
    assert is_valid_production(None) is False


from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def test_prepare_agriculture(spark):
    """Test cleaning agriculture data with PySpark."""

    # Create a small test DataFrame
    data = [
        (" Ukraine ", " Wheat ", "2022"),
        (" France ", " Barley ", "2021"),
    ]

    columns = ["AREA", "ITEM", "YEAR"]

    df = spark.createDataFrame(data, columns)

    # Apply our transformation
    result = prepare_agriculture(df)

    # Collect the transformed rows
    rows = result.collect()

    # Check the results
    assert rows[0]["AREA"] == "Ukraine"
    assert rows[0]["ITEM"] == "Wheat"
    assert rows[0]["YEAR"] == 2022

    assert rows[1]["AREA"] == "France"
    assert rows[1]["ITEM"] == "Barley"
    assert rows[1]["YEAR"] == 2021

    # Check the YEAR column type
    assert dict(result.dtypes)["YEAR"] == "int"

def test_join_agriculture_country(spark):
    """Test joining agriculture data with country dimension."""

    agriculture_data = [
        ("Ukraine", "Wheat", 2022, 1000.0),
        ("France", "Barley", 2022, 2000.0),
        ("Atlantis", "Wheat", 2022, 500.0),
    ]

    agriculture_columns = [
        "AREA",
        "ITEM",
        "YEAR",
        "PRODUCTION_QUANTITY",
    ]

    agriculture_df = spark.createDataFrame(
        agriculture_data,
        agriculture_columns
    )

    country_data = [
        ("Ukraine", "UKR"),
        ("France", "FRA"),
    ]

    country_columns = ["country_name", "country_code"]

    countries_df = spark.createDataFrame(
        country_data,
        country_columns
    )

    # Apply the JOIN transformation
    result = join_agriculture_country(
        agriculture_df,
        countries_df
    )

    rows = result.collect()

    # INNER JOIN should exclude Atlantis
    assert result.count() == 2

    # Verify country keys
    country_keys = {row["country_key"] for row in rows}

    assert country_keys == {"UKR", "FRA"}

    # Verify production values
    production_by_country = {
        row["country_key"]: row["PRODUCTION_QUANTITY"]
        for row in rows
    }

    assert production_by_country["UKR"] == 1000.0
    assert production_by_country["FRA"] == 2000.0

