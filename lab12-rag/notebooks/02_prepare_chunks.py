# Databricks notebook source
# MAGIC %pip install langchain-text-splitters==1.1.0

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql import functions as F

SOURCE_TABLE = ("workspace.viktoriia_kalenichenko_lab12.document_pages")

pages_df = spark.table(SOURCE_TABLE)

print(f"Read from Delta: {pages_df.count()} pages")

# COMMAND ----------

prepared_df = pages_df.withColumn(
    "clean_text",
    F.regexp_replace(F.col("text"), r"\r\n?", "\n")
)

prepared_df = prepared_df.withColumn(
    "clean_text",
    F.regexp_replace("clean_text", "\u0000", "")
)

prepared_df = prepared_df.withColumn(
    "clean_text",
    F.regexp_replace("clean_text", r"^\s*\d+[ \t]*\n", "")
)

prepared_df = prepared_df.withColumn(
    "clean_text",
    F.regexp_replace("clean_text", r"[ \t\u00A0]+", " ")
)

prepared_df = prepared_df.withColumn(
    "clean_text",
    F.trim(
        F.regexp_replace(
            F.regexp_replace("clean_text", r" *\n *", "\n"),
            r"\n{3,}",
            "\n\n"
        )
    )
)

prepared_df = (
    prepared_df
    .withColumn("clean_char_count", F.length("clean_text"))
    .filter(F.col("clean_char_count") > 0)
    .filter(~F.col("page_number").isin(1, 2))
)

print(f"Pages to split: {prepared_df.count()}")

sample = (
    prepared_df
    .filter(F.col("page_number") == 20)
    .select("clean_text")
    .first()
)

print(sample["clean_text"][:1500])

# COMMAND ----------

from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
    is_separator_regex=False,
)

page_text = (
    prepared_df
    .filter(F.col("page_number") == 20)
    .select("clean_text")
    .first()["clean_text"]
)

test_chunks = splitter.split_text(page_text)

print(f"Fragments created on page 20: {len(test_chunks)}")

for number, chunk in enumerate(test_chunks, start=1):
    print(f"\n===== Fragment {number}: {len(chunk)} symbols =====\n")
    print(chunk)

# COMMAND ----------

import hashlib

PROFILE = "recursive_chars_1200_overlap_200_v1"
chunk_rows = []

pages = (
    prepared_df
    .select("file_name", "source_sha256", "page_number", "clean_text")
    .orderBy("file_name", "page_number")
    .collect()
)

for page in pages:
    # We use the same splitter as in the test on page 20.
    fragments = splitter.split_text(page["clean_text"])

    for chunk_index, chunk_text in enumerate(fragments, start=1):
        identity = (
            f'{page["source_sha256"]}|{page["page_number"]}|'
            f'{PROFILE}|{chunk_index}|{chunk_text}'
        )
        chunk_id = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

        chunk_rows.append((
            chunk_id,
            PROFILE,
            page["file_name"],
            page["source_sha256"],
            page["page_number"],
            chunk_index,
            chunk_text,
            len(chunk_text),
        ))

chunks_df = spark.createDataFrame(
    chunk_rows,
    schema="""
        chunk_id STRING,
        chunk_profile STRING,
        file_name STRING,
        source_sha256 STRING,
        page_number INT,
        chunk_index INT,
        chunk_text STRING,
        char_count INT
    """
)

# Checking the result before saving.
assert len(pages) == 144, "Expected 144 pages"
assert chunks_df.select("page_number").distinct().count() == 144, \
    "Not all pages were split into chunks"
assert chunks_df.select("chunk_id").distinct().count() == len(chunk_rows), \
    "Duplicate chunk IDs detected"
assert all(0 < row[-1] <= 1200 for row in chunk_rows), \
    "Empty or oversized chunks detected"

print(f"Pages processed: {len(pages)}")
print(f"Chunks created: {len(chunk_rows)}")
print("All validation checks passed")

display(
    chunks_df.select(
        "page_number",
        "chunk_index",
        "char_count",
        F.substring("chunk_text", 1, 150).alias("preview")
    )
    .orderBy("page_number", "chunk_index")
    .limit(10)
)

# COMMAND ----------

CHUNKS_TABLE = (
    "workspace.viktoriia_kalenichenko_lab12.document_chunks"
)

(
    chunks_df.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable(CHUNKS_TABLE)
)

saved_count = spark.table(CHUNKS_TABLE).count()
assert saved_count == len(chunk_rows), \
    "Saved chunk count does not match the expected count"

print(f"Successfully saved {saved_count} chunks to {CHUNKS_TABLE}")

# COMMAND ----------
