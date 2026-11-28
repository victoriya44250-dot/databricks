# Databricks notebook source

from databricks.ai_search.client import AISearchClient
from pyspark.sql import functions as F

import sys
from pathlib import Path

# Bundle passes its absolute Workspace Files directory. Set this widget for manual runs.
dbutils.widgets.text("project_root", "")
project_root = Path(dbutils.widgets.get("project_root"))
if not project_root.is_absolute() or not (project_root / "src/rag_helpers.py").is_file():
    raise ValueError("Set project_root to the absolute /Workspace directory containing src/rag_helpers.py")
sys.path.insert(0, str(project_root))

from src.rag_helpers import ALLOWED_PAGES, parse_results

SCHEMA = "workspace.viktoriia_kalenichenko_lab12"

PAGES_TABLE = f"{SCHEMA}.document_pages"
CHUNKS_TABLE = f"{SCHEMA}.document_chunks"
INDEX_NAME = f"{SCHEMA}.document_chunks_index"

# Validate the ingested document.
pages_count = spark.table(PAGES_TABLE).count()

assert pages_count == 147, \
    f"Expected 147 pages, got {pages_count}"

print(f"PASS: {pages_count} document pages")

# Validate document chunks.
chunks = spark.table(CHUNKS_TABLE)

stats = chunks.agg(
    F.count("*").alias("n"),
    F.countDistinct("chunk_id").alias("unique_ids"),
    F.countDistinct("page_number").alias("pages"),
    F.sum(
        F.when(
            F.col("chunk_id").isNull()
            | F.col("chunk_text").isNull()
            | (F.length(F.trim("chunk_text")) == 0)
            | (F.length("chunk_text") > 1200),
            1
        ).otherwise(0)
    ).alias("invalid")
).first()

assert stats["n"] == 550, \
    f"Expected 550 chunks, got {stats['n']}"

assert stats["n"] == stats["unique_ids"], \
    "Duplicate or null chunk IDs detected"

assert stats["pages"] == 144, f"Expected 144 chunked pages, got {stats['pages']}"

assert stats["invalid"] == 0, \
    "Invalid chunks detected"

print(f"PASS: {stats['n']} valid unique chunks")

# Verify filtered retrieval.
client = AISearchClient()
index = client.get_index(index_name=INDEX_NAME)

response = index.similarity_search(
    query_text="Which catastrophic risks affect Italian agriculture?",
    query_type="ANN",
    num_results=5,
    columns=["chunk_id", "page_number", "chunk_text"],
    filters={"page_number": ALLOWED_PAGES},
)

rows = parse_results(response)

assert len(rows) == 5, f"Expected five valid results, got {len(rows)}"
assert len(response.get("result", {}).get("data_array", [])) == len(rows), \
    "Retrieved rows contain empty passages"
assert len({row["chunk_id"] for row in rows}) == len(rows), "Duplicate retrieved chunk IDs"

for row in rows:
    assert row["page_number"] in ALLOWED_PAGES, \
        "Unexpected page returned"

    assert row["chunk_text"].strip(), \
        "Empty retrieved chunk"

print(f"PASS: Retrieval returned {len(rows)} valid chunks")
print("All smoke tests passed")
