
import os
import pytest
from databricks.connect import DatabricksSession


@pytest.fixture(scope="session")
def spark():
    """Connect to Databricks Serverless for Spark tests."""

    profile = os.environ.get("DATABRICKS_CONFIG_PROFILE")

    if not profile:
        raise RuntimeError(
            "DATABRICKS_CONFIG_PROFILE is not set"
        )

    session = (
        DatabricksSession.builder
        .serverless()
        .profile(profile)
        .getOrCreate()
    )

    yield session

    session.stop()
