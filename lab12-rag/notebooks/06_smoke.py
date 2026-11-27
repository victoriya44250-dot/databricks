# Databricks notebook source
# Read-only pre-deployment smoke test; does not call an LLM or change an index.
from databricks.ai_search.client import AISearchClient
from pyspark.sql import functions as F

TARGET = "workspace.viktoriia_kalenichenko_lab12"
chunks = spark.table(f"{TARGET}.document_chunks")
stats = chunks.agg(
    F.count("*").alias("n"),
    F.countDistinct("chunk_id").alias("unique_ids"),
    F.sum(F.when(F.col("chunk_id").isNull() | F.col("chunk_text").isNull() | (F.length(F.trim("chunk_text")) == 0), 1).otherwise(0)).alias("invalid")
).first()
assert stats["n"] == 550, f"Expected the reviewed 550-chunk corpus, got {stats['n']}"
assert stats["n"] == stats["unique_ids"], "Duplicate or null chunk IDs"
assert stats["invalid"] == 0, "Empty text or missing ID"

index = AISearchClient().get_index(index_name=f"{TARGET}.document_chunks_index")
response = index.similarity_search(
    query_text="Which catastrophic risks affect Italian agriculture?", query_type="ANN",
    num_results=3, columns=["chunk_id", "page_number", "chunk_text"],
    filters={"page_number": [p for p in range(7, 147) if p not in {96, 97}]},
)
assert response.get("result", {}).get("data_array"), "Search returned no evidence"
print("PASS: 550 valid unique chunks; filtered retrieval returned evidence.")
