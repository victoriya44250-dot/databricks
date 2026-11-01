import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_quality import (
    check_completeness,
    check_uniqueness,
    check_validity,
    check_consistency,
    reconcile_counts,
    reconcile_aggregates,
)


def test_completeness_passes(spark):
    """Check that complete data passes the quality check."""

    data = [
        ("Ukraine", "Wheat", 2022),
        ("France", "Barley", 2021),
    ]

    df = spark.createDataFrame(data, ["AREA", "ITEM", "YEAR"])

    result = check_completeness(df, ["AREA", "ITEM", "YEAR"])

    assert result["passed"] is True
    assert result["total_rows"] == 2
    assert result["missing_values"]["AREA"] == 0


def test_completeness_fails(spark):
    """Check that missing data fails the quality check."""

    data = [
        ("Ukraine", "Wheat", 2022),
        (None, "Barley", 2021),
    ]

    df = spark.createDataFrame(data, ["AREA", "ITEM", "YEAR"])

    result = check_completeness(df, ["AREA", "ITEM", "YEAR"])

    assert result["passed"] is False
    assert result["total_rows"] == 2
    assert result["missing_values"]["AREA"] == 1

def test_uniqueness_passes(spark):
    """Check that unique records pass."""

    data = [
        ("Ukraine", "Wheat", 2022),
        ("France", "Wheat", 2022),
    ]

    df = spark.createDataFrame(data, ["AREA", "ITEM", "YEAR"])

    result = check_uniqueness(df, ["AREA", "ITEM", "YEAR"])

    assert result["passed"] is True
    assert result["total_rows"] == 2
    assert result["unique_keys"] == 2
    assert result["duplicate_rows"] == 0


def test_uniqueness_fails(spark):
    """Check that duplicate records are detected."""

    data = [
        ("Ukraine", "Wheat", 2022),
        ("Ukraine", "Wheat", 2022),
    ]

    df = spark.createDataFrame(data, ["AREA", "ITEM", "YEAR"])

    result = check_uniqueness(df, ["AREA", "ITEM", "YEAR"])

    assert result["passed"] is False
    assert result["total_rows"] == 2
    assert result["unique_keys"] == 1
    assert result["duplicate_rows"] == 1


def test_validity_passes(spark):
    """Check that valid agriculture values pass."""

    data = [
        (2022, 1000.0, 500.0),
        (2021, 2000.0, 800.0),
    ]

    columns = ["YEAR", "PRODUCTION_QUANTITY", "AREA_HARVESTED"]
    df = spark.createDataFrame(data, columns)

    result = check_validity(df)

    assert result["passed"] is True
    assert result["invalid_year"] == 0
    assert result["negative_production"] == 0
    assert result["negative_area"] == 0


def test_validity_fails(spark):
    """Check that invalid agriculture values are detected."""

    data = [
        (2022, 1000.0, 500.0),
        (1800, -100.0, 300.0),
        (2021, 500.0, -50.0),
    ]

    columns = ["YEAR", "PRODUCTION_QUANTITY", "AREA_HARVESTED"]
    df = spark.createDataFrame(data, columns)

    result = check_validity(df)

    assert result["passed"] is False
    assert result["invalid_year"] == 1
    assert result["negative_production"] == 1
    assert result["negative_area"] == 1


def test_consistency_passes(spark):
    """Check that all countries exist in the reference table."""

    agriculture = spark.createDataFrame(
        [("Ukraine",), ("France",)],
        ["AREA"],
    )

    countries = spark.createDataFrame(
        [("Ukraine",), ("France",)],
        ["country_name"],
    )

    result = check_consistency(
        agriculture,
        countries,
        "AREA",
        "country_name",
    )

    assert result["passed"] is True
    assert result["unmatched_rows"] == 0


def test_consistency_fails(spark):
    """Check that unmatched countries are detected."""

    agriculture = spark.createDataFrame(
        [("Ukraine",), ("Atlantis",)],
        ["AREA"],
    )

    countries = spark.createDataFrame(
        [("Ukraine",), ("France",)],
        ["country_name"],
    )

    result = check_consistency(
        agriculture,
        countries,
        "AREA",
        "country_name",
    )

    assert result["passed"] is False
    assert result["unmatched_rows"] == 1



def test_reconciliation_passes():
    """Check that matching row counts pass."""

    result = reconcile_counts(3152, 3152)

    assert result["passed"] is True
    assert result["expected_rows"] == 3152
    assert result["actual_rows"] == 3152
    assert result["difference"] == 0


def test_reconciliation_fails():
    """Check that missing rows are detected."""

    result = reconcile_counts(3152, 3150)

    assert result["passed"] is False
    assert result["expected_rows"] == 3152
    assert result["actual_rows"] == 3150
    assert result["difference"] == 2


def test_aggregate_reconciliation_passes():
    """Check that small aggregate differences are accepted."""

    result = reconcile_aggregates(
        expected_total=1000.00,
        actual_total=1000.005,
    )

    assert result["passed"] is True
    assert result["difference"] <= 0.01


def test_aggregate_reconciliation_fails():
    """Check that significant aggregate differences are detected."""

    result = reconcile_aggregates(
        expected_total=1000.00,
        actual_total=950.00,
    )

    assert result["passed"] is False
    assert result["difference"] == 50.0


def test_consistency_same_column_name(spark):
    """Check matching when both tables use the same column name."""

    agriculture = spark.createDataFrame(
        [("Ukraine",), ("France",)],
        ["AREA"],
    )

    countries = spark.createDataFrame(
        [("Ukraine",), ("France",)],
        ["AREA"],
    )

    result = check_consistency(
        agriculture,
        countries,
        "AREA",
        "AREA",
    )

    assert result["passed"] is True
    assert result["unmatched_rows"] == 0
