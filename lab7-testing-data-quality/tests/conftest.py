import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import notebook_test_context


@pytest.fixture(scope="session")
def spark():
    """Use notebook Spark for Jobs, or Databricks Connect for local tests."""
    if notebook_test_context.spark_session is not None:
        yield notebook_test_context.spark_session
        # The notebook owns this session; never stop it here.
        return

    profile = os.environ.get("DATABRICKS_CONFIG_PROFILE")
    if not profile:
        raise RuntimeError("DATABRICKS_CONFIG_PROFILE is not set")

    from databricks.connect import DatabricksSession

    session = DatabricksSession.builder.serverless().profile(profile).getOrCreate()
    try:
        yield session
    finally:
        session.stop()
