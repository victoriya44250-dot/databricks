import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Return the active Spark session for unit tests."""
    session = SparkSession.getActiveSession()

    if session is None:
        raise RuntimeError("No active Spark session available")

    return session