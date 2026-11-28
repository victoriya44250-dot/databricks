# Databricks notebook source
CHUNKS_TABLE = (
    "workspace.viktoriia_kalenichenko_lab12.document_chunks"
)

# Enable Change Data Feed for index synchronization.
spark.sql(f"""
    ALTER TABLE {CHUNKS_TABLE}
    SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

display(
    spark.sql(f"""
        SHOW TBLPROPERTIES {CHUNKS_TABLE}
        ('delta.enableChangeDataFeed')
    """)
)

# COMMAND ----------

# MAGIC %pip install databricks-ai-search==0.83

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from databricks.ai_search.client import AISearchClient

client = AISearchClient()

SCHEMA = "workspace.viktoriia_kalenichenko_lab12"

CHUNKS_TABLE = f"{SCHEMA}.document_chunks"
INDEX_NAME = f"{SCHEMA}.document_chunks_index"

ENDPOINT_NAME = "lab12_agri_search"
EMBEDDING_MODEL = "databricks-qwen3-embedding-0-6b"

# COMMAND ----------

if client.endpoint_exists(ENDPOINT_NAME):
    print(f"Endpoint already exists: {ENDPOINT_NAME}")
else:
    client.create_endpoint_and_wait(
        name=ENDPOINT_NAME,
        endpoint_type="STANDARD"
    )
    print(f"Endpoint created: {ENDPOINT_NAME}")

endpoint = client.get_endpoint(ENDPOINT_NAME)
assert endpoint["endpoint_type"] == "STANDARD", "Unexpected endpoint type"
display(endpoint)

# COMMAND ----------

if client.index_exists(
    endpoint_name=ENDPOINT_NAME,
    index_name=INDEX_NAME
):
    index = client.get_index(
        endpoint_name=ENDPOINT_NAME,
        index_name=INDEX_NAME
    )
    print(f"Index already exists: {INDEX_NAME}")

else:
    index = client.create_delta_sync_index_and_wait(
        endpoint_name=ENDPOINT_NAME,
        index_name=INDEX_NAME,
        source_table_name=CHUNKS_TABLE,
        pipeline_type="TRIGGERED",
        primary_key="chunk_id",
        embedding_source_column="chunk_text",
        embedding_model_endpoint_name=EMBEDDING_MODEL,
        sync_computed_embeddings=False
    )
    print(f"Index created: {INDEX_NAME}")

# Fail on configuration drift instead of silently reusing a different index.
description = index.describe()
assert description["primary_key"] == "chunk_id", "Unexpected index primary key"
assert description["index_type"] == "DELTA_SYNC", "Unexpected index type"
spec = description["delta_sync_index_spec"]
assert spec["source_table"] == CHUNKS_TABLE, "Unexpected source table"
assert spec["pipeline_type"] == "TRIGGERED", "Unexpected pipeline type"
assert any(
    column["name"] == "chunk_text"
    and column["embedding_model_endpoint_name"] == EMBEDDING_MODEL
    for column in spec["embedding_source_columns"]
), "Unexpected embedding configuration"
display(description)

# COMMAND ----------
