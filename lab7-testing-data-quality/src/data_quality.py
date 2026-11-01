from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def check_completeness(df: DataFrame, required_columns: list[str]) -> dict:
    """Check for missing values in required columns."""

    total_rows = df.count()

    missing = {
        column: df.filter(F.col(column).isNull()).count()
        for column in required_columns
    }

    return {
        "check_name": "completeness",
        "total_rows": total_rows,
        "missing_values": missing,
        "passed": all(count == 0 for count in missing.values()),
    }


def check_uniqueness(df: DataFrame, key_columns: list[str]) -> dict:
    """Check that key combinations are unique."""

    total_rows = df.count()

    unique_keys = df.select(*key_columns).distinct().count()

    duplicate_rows = total_rows - unique_keys

    return {
        "check_name": "uniqueness",
        "total_rows": total_rows,
        "unique_keys": unique_keys,
        "duplicate_rows": duplicate_rows,
        "passed": duplicate_rows == 0,
    }

def check_validity(df: DataFrame) -> dict:
    """Check year range and non-negative agriculture metrics."""

    invalid_year = df.filter(
        F.col("YEAR").isNull()
        | ~F.col("YEAR").between(1990, 2022)
    ).count()

    negative_production = df.filter(
        F.col("PRODUCTION_QUANTITY") < 0
    ).count()

    negative_area = df.filter(
        F.col("AREA_HARVESTED") < 0
    ).count()

    return {
        "check_name": "validity",
        "invalid_year": invalid_year,
        "negative_production": negative_production,
        "negative_area": negative_area,
        "passed": (
            invalid_year == 0
            and negative_production == 0
            and negative_area == 0
        ),
    }


def check_consistency(
    source: DataFrame,
    reference: DataFrame,
    source_key: str,
    reference_key: str,
) -> dict:
    """Check that source values exist in the reference table."""

    s = source.alias("s")
    r = reference.alias("r")

    unmatched = s.join(
        r,
        F.trim(F.col(f"s.{source_key}")) == F.trim(F.col(f"r.{reference_key}")),
        "left_anti",
    )

    unmatched_rows = unmatched.count()

    return {
        "check_name": "consistency",
        "unmatched_rows": unmatched_rows,
        "passed": unmatched_rows == 0,
    }

def reconcile_counts(
    expected_rows: int,
    actual_rows: int,
) -> dict:
    """Compare expected and actual row counts."""

    return {
        "check_name": "row_reconciliation",
        "expected_rows": expected_rows,
        "actual_rows": actual_rows,
        "difference": expected_rows - actual_rows,
        "passed": expected_rows == actual_rows,
    }

def reconcile_aggregates(
    expected_total: float,
    actual_total: float,
    tolerance: float = 0.01,
) -> dict:
    """Compare aggregate values within a tolerance."""

    difference = abs(expected_total - actual_total)

    return {
        "check_name": "aggregate_reconciliation",
        "expected_total": expected_total,
        "actual_total": actual_total,
        "difference": difference,
        "tolerance": tolerance,
        "passed": difference <= tolerance,
    }