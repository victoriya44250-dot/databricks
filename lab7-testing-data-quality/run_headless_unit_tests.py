# Databricks notebook source
# MAGIC %pip install pytest==9.2.0

# COMMAND ----------

import sys
import importlib
from pathlib import Path
import pytest

sys.dont_write_bytecode = True
project_root = Path.cwd()
if not (project_root / "tests" / "test_data_quality.py").is_file():
    raise RuntimeError("Deploy the full Lab 7 folder; tests/ is missing beside this notebook.")
sys.path.insert(0, str(project_root))

for name in list(sys.modules):
    if name.rsplit(".", 1)[-1] in {"test_transformations", "test_data_quality", "conftest"}:
        del sys.modules[name]

import src.transformations as transformations
import src.data_quality as data_quality
from src import notebook_test_context

importlib.reload(transformations)
importlib.reload(data_quality)
notebook_test_context.spark_session = spark
try:
    result = pytest.main([
        "-v", "-p", "no:cacheprovider", "--assert=plain",
        str(project_root / "tests"),
    ])
finally:
    notebook_test_context.spark_session = None

print("Pytest exit code:", result)
if result != 0:
    raise RuntimeError(f"Unit tests failed (pytest exit code {result})")
