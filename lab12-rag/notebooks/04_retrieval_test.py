# Databricks notebook source
# MAGIC %pip install databricks-ai-search==0.83

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import sys
from pathlib import Path

# Bundle passes its absolute Workspace Files directory. Set this widget for manual runs.
dbutils.widgets.text("project_root", "")
project_root = Path(dbutils.widgets.get("project_root"))
if not project_root.is_absolute() or not (project_root / "src/rag_helpers.py").is_file():
    raise ValueError("Set project_root to the absolute /Workspace directory containing src/rag_helpers.py")
sys.path.insert(0, str(project_root))

from src.rag_helpers import ALLOWED_PAGES, parse_results

from databricks.ai_search.client import AISearchClient

INDEX_NAME = (
    "workspace.viktoriia_kalenichenko_lab12.document_chunks_index"
)

client = AISearchClient()
index = client.get_index(index_name=INDEX_NAME)


results = index.similarity_search(
    query_text="What agricultural risk management tools are used in Italy?",
    query_type="ANN",
    columns=["chunk_id", "page_number", "chunk_text"],
    filters={"page_number": ALLOWED_PAGES},
    num_results=5,
)

rows = parse_results(results)
assert rows, "Search returned no passages."

for rank, row in enumerate(rows, start=1):
    print(f"\n===== Result {rank}: page {row['page_number']} =====\n")
    print(row["chunk_text"])

# COMMAND ----------
