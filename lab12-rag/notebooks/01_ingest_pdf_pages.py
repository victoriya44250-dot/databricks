# Databricks notebook source
# MAGIC %pip install pypdf==7.1.1

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from pathlib import Path
from pypdf import PdfReader
from pyspark.sql import functions as F
import hashlib

RAW_DIR = Path("/Volumes/workspace/viktoriia_kalenichenko_lab12/raw_docs")
TABLE = "workspace.viktoriia_kalenichenko_lab12.document_pages"
FILES = ["P510294-1b00a8b1-c76f-419d-953a-46bd5805c044.pdf"]

for filename in FILES:
    path = RAW_DIR / filename

    if not path.is_file():
        raise FileNotFoundError(f"Not found: {path}")

    with path.open("rb") as stream:
        header = stream.read(1024)

    if b"%PDF-" not in header:
        raise ValueError(f"The file does not have the expected PDF header: {filename}")

    print(f"OK | {filename} | {path.stat().st_size:,} bytes")

# COMMAND ----------

rows = []

for filename in FILES:
    path = RAW_DIR / filename
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    with path.open("rb") as stream:
        reader = PdfReader(stream)

        if reader.is_encrypted:
            raise ValueError(f"PDF is encrypted: {filename}")

        page_count = len(reader.pages)
        if page_count == 0:
            raise ValueError(f"PDF contains no pages: {filename}")

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                raise RuntimeError(
                    f"Error: {filename}, page {page_number}"
                ) from exc

            rows.append((
                filename,
                str(path),
                file_hash,
                page_number,
                text,
                len(text.strip()),
            ))

    print(f"{filename}: {page_count} pages")

pages_df = spark.createDataFrame(
    rows,
    schema="""
        file_name STRING,
        file_path STRING,
        source_sha256 STRING,
        page_number INT,
        text STRING,
        char_count INT
    """,
)

print(f"Total pages retrieved: {len(rows)}")

# COMMAND ----------

from pyspark.sql import functions as F

display(
    pages_df.groupBy("file_name").agg(
        F.count("*").alias("total_pages"),
        F.sum(
            F.when(F.col("char_count") == 0, 1).otherwise(0)
        ).alias("empty_pages"),
        F.sum(
            F.when(F.col("char_count") < 300, 1).otherwise(0)
        ).alias("pages_under_300_chars"),
        F.round(F.avg("char_count"), 0).alias("avg_chars_per_page"),
    )
)

# COMMAND ----------

print("SHORT PAGES")

display(
    pages_df
    .filter(F.col("char_count") < 300)
    .select("page_number", "char_count", "text")
    .orderBy("page_number")
)

print("MAIN TEXT SAMPLES")

samples = (
    pages_df
    .filter(F.col("page_number").isin(20, 60, 100))
    .select("page_number", "text")
    .orderBy("page_number")
    .collect()
)

for row in samples:
    print(f"\n===== PDF page {row['page_number']} =====\n")
    print(row["text"][:2500])

# COMMAND ----------

TABLE = "workspace.viktoriia_kalenichenko_lab12.document_pages"

# Validate the results before saving.
assert pages_df.count() == 147, "Expected 147 pages"

assert pages_df.select("file_name").distinct().count() == 1, \
    "Expected one document"

assert (
    pages_df.groupBy("file_name", "page_number")
    .count()
    .filter(F.col("count") > 1)
    .count() == 0
), "Duplicate pages detected"

# Save the extracted text to a Delta table.
pages_df.write.format("delta").mode("overwrite").saveAsTable(TABLE)

# Read and validate the saved table.
saved_df = spark.table(TABLE)
saved_count = saved_df.count()

assert saved_count == 147, "Saved page count does not match the expected count"

print(f"Successfully saved {saved_count} pages to {TABLE}")
