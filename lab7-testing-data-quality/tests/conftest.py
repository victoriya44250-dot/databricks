import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Use the active Databricks Spark session."""
    session = SparkSession.getActiveSession()

    if session is None:
        raise RuntimeError("No active Spark session available")

    return session