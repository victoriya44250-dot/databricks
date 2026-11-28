# Databricks notebook source
# MAGIC %md
# MAGIC # RAG evaluation
# MAGIC
# MAGIC Compare answers with and without retrieval using the same model and questions.
# MAGIC
# MAGIC Review:
# MAGIC - relevance to the question;
# MAGIC - support for factual claims in the retrieved passages;
# MAGIC - missing information;
# MAGIC - handling of questions that the document cannot answer.
# MAGIC
# MAGIC This small development set is not a general accuracy benchmark.

# COMMAND ----------

# MAGIC %pip install databricks-ai-search==0.83

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

evaluation_questions = [
    {
        "id": "Q1",
        "question": "Which climatic risks are classified as catastrophic for Italian agriculture?",
        "answerable": True,
    },
    {
        "id": "Q2",
        "question": "According to the report, what percentage of Italian crop production value was insured in 2023?",
        "answerable": True,
    },
    {
        "id": "Q3",
        "question": "Which clustering method does the report use to group EU agricultural sectors?",
        "answerable": True,
    },
    {
        "id": "Q4",
        "question": "What is the insurance policy number of my private farm?",
        "answerable": False,
    },
    {
        "id": "Q5",
        "question": "What will the exact wheat yield of my farm be in 2027?",
        "answerable": False,
    },
]

display(spark.createDataFrame(evaluation_questions))

# COMMAND ----------

import time
import sys
from pathlib import Path

# Bundle passes its absolute Workspace Files directory. Set this widget for manual runs.
dbutils.widgets.text("project_root", "")
project_root = Path(dbutils.widgets.get("project_root"))
if not project_root.is_absolute() or not (project_root / "src/rag_helpers.py").is_file():
    raise ValueError("Set project_root to the absolute /Workspace directory containing src/rag_helpers.py")
sys.path.insert(0, str(project_root))

from src.rag_helpers import ABSTENTION, ALLOWED_PAGES, citation_check, make_prompt, parse_results

from databricks.ai_search.client import AISearchClient

index = AISearchClient().get_index(
    index_name="workspace.viktoriia_kalenichenko_lab12.document_chunks_index"
)


# COMMAND ----------

def ask(question, use_retrieval=True, query_type="ANN"):
    started = time.perf_counter()
    chunks = []

    if use_retrieval:
        response = index.similarity_search(
            query_text=question,
            query_type=query_type,
            num_results=5,
            columns=["chunk_id", "page_number", "chunk_text"],
            filters={"page_number": ALLOWED_PAGES},
        )

        chunks = parse_results(response)

    # Revised prompt wording; historical results below were collected before this refactor.
    prompt = make_prompt(question, chunks if use_retrieval else None, max_words=150)

    if use_retrieval and not chunks:
        answer = ABSTENTION
    else:
        answer = (
            spark.createDataFrame([(prompt,)], ["prompt"])
            .selectExpr("ai_query('databricks-gpt-oss-120b', prompt) AS answer")
            .first()["answer"]
        )

    elapsed_seconds = round(time.perf_counter() - started, 2)
    if use_retrieval:
        print("Citation diagnostics (not factual verification):", citation_check(answer, chunks))

    return {
        "context": chunks,
        "prompt": prompt,
        "answer": answer,
        "pages": sorted({int(chunk["page_number"]) for chunk in chunks}),
        "chunk_ids": [str(chunk["chunk_id"]) for chunk in chunks],
        "elapsed_seconds": elapsed_seconds,
    }

# COMMAND ----------

evaluation_rows = []

for case in evaluation_questions:
    for mode in ["rag", "baseline"]:
        result = ask(
            question=case["question"],
            use_retrieval=(mode == "rag"),
        )

        evaluation_rows.append((
            case["id"],
            case["question"],
            case["answerable"],
            mode,
            result["prompt"],
            result["answer"],
            result["pages"],
            result["chunk_ids"],
            result["elapsed_seconds"],
        ))

        print(f"{case['id']} / {mode}: completed")

print(f"Collected {len(evaluation_rows)} answers")

# COMMAND ----------

evaluation_df = spark.createDataFrame(
    evaluation_rows,
    schema="""
        question_id STRING,
        question STRING,
        answerable BOOLEAN,
        mode STRING,
        prompt STRING,
        answer STRING,
        retrieved_pages ARRAY<INT>,
        retrieved_chunk_ids ARRAY<STRING>,
        elapsed_seconds DOUBLE
    """,
)

display(
    evaluation_df
    .select("question_id", "mode", "answerable", "answer", "retrieved_pages")
    .orderBy("question_id", "mode")
)

# COMMAND ----------

import uuid
from pyspark.sql import functions as F

EVALUATION_TABLE = "workspace.viktoriia_kalenichenko_lab12.qa_evaluation"
evaluation_id = str(uuid.uuid4())

(
    evaluation_df
    .withColumn("evaluation_id", F.lit(evaluation_id))
    .withColumn("logged_at", F.current_timestamp())
    .write.format("delta")
    .mode("append")
    .saveAsTable(EVALUATION_TABLE)
)

saved_evaluation = (
    spark.table(EVALUATION_TABLE)
    .filter(F.col("evaluation_id") == evaluation_id)
)

print(f"Saved {saved_evaluation.count()} answers")
print(f"Evaluation ID: {evaluation_id}")

# COMMAND ----------

for row in saved_evaluation.orderBy("question_id", "mode").collect():
    print(f"\n===== {row['question_id']} / {row['mode']} =====")
    print("Question:", row["question"])
    print("Retrieved pages:", row["retrieved_pages"])
    print(row["answer"])

# COMMAND ----------

q3_result = (
    saved_evaluation
    .filter(
        (F.col("question_id") == "Q3") &
        (F.col("mode") == "rag")
    )
    .select("prompt")
    .first()
)

print(q3_result["prompt"])

# COMMAND ----------

q3_question = next(
    case["question"]
    for case in evaluation_questions
    if case["id"] == "Q3"
)

# Inspect the exact passages used for the HYBRID answer; retrieve only once.
hybrid_q3 = ask(question=q3_question, use_retrieval=True, query_type="HYBRID")
hybrid_chunks = hybrid_q3["context"]

for number, chunk in enumerate(hybrid_chunks, start=1):
    print(f"\n--- Result {number}: PDF page {int(chunk['page_number'])} ---")
    print(chunk["chunk_text"])

# COMMAND ----------

print("Retrieved pages:", hybrid_q3["pages"])
print(hybrid_q3["answer"])

# COMMAND ----------

hybrid_evaluation_id = str(uuid.uuid4())

hybrid_row = [(
    "Q3",
    q3_question,
    True,
    "rag_hybrid",
    hybrid_q3["prompt"],
    hybrid_q3["answer"],
    hybrid_q3["pages"],
    hybrid_q3["chunk_ids"],
    hybrid_q3["elapsed_seconds"],
)]

(
    spark.createDataFrame(hybrid_row, schema=evaluation_df.schema)
    .withColumn("evaluation_id", F.lit(hybrid_evaluation_id))
    .withColumn("logged_at", F.current_timestamp())
    .write.format("delta")
    .mode("append")
    .saveAsTable(EVALUATION_TABLE)
)

print(f"Saved HYBRID experiment: {hybrid_evaluation_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Historical evaluation conclusions
# MAGIC
# MAGIC These observations belong to the original manual experiment, before shared-prompt integration.
# MAGIC They are not results of the refactored code. New runs append new evaluation IDs and full prompts.
# MAGIC No new experiment was executed during this refactor.
# MAGIC
# MAGIC Five questions were tested with and without retrieval using the same model.
# MAGIC
# MAGIC | Question | RAG with ANN | Without retrieval |
# MAGIC |---|---|---|
# MAGIC | Q1: catastrophic agricultural risks | Correct: flood, drought and frost | Added hazards outside the report's catastrophic-risk category |
# MAGIC | Q2: insured crop production value in 2023 | Correct: 19.2% | Acknowledged missing information |
# MAGIC | Q3: clustering method | Abstained because the retrieved passages did not name the method | Acknowledged missing information |
# MAGIC | Q4: private insurance policy number | Correctly abstained | Correctly abstained |
# MAGIC | Q5: exact future farm yield | Correctly abstained | Correctly abstained |
# MAGIC
# MAGIC ANN-based RAG answered two of the three answerable questions correctly. Both modes abstained on the two unanswerable questions.
# MAGIC
# MAGIC For Q3, ANN retrieved a chunk from page 20 but missed the passage naming the method. HYBRID search, with the same question, top-k and page filter, retrieved the relevant passage. The model then correctly answered **K-means clustering [p. 20]**.
# MAGIC
# MAGIC This demonstrates a retrieval improvement for Q3, not a general superiority of HYBRID search. The original results were retained, and the follow-up experiment was saved separately.
# MAGIC
# MAGIC This small development set was reviewed manually. It is not an independent benchmark, and citation presence alone does not prove factual correctness.

# COMMAND ----------

objects = [
    ("SCHEMA", "workspace.viktoriia_kalenichenko_lab12"),
    ("TABLE", "workspace.viktoriia_kalenichenko_lab12.qa_log"),
    ("TABLE", "workspace.viktoriia_kalenichenko_lab12.qa_evaluation"),
]

for object_type, object_name in objects:
    print(f"\nPermissions: {object_name}")
    display(spark.sql(f"SHOW GRANTS ON {object_type} {object_name}"))

# COMMAND ----------

print("Current user and table owners:")
display(spark.sql("""
    SELECT
        current_user() AS current_user,
        table_name,
        table_owner
    FROM workspace.information_schema.tables
    WHERE table_schema = 'viktoriia_kalenichenko_lab12'
      AND table_name IN ('qa_log', 'qa_evaluation')
"""))

print("Catalog permissions:")
display(spark.sql("SHOW GRANTS ON CATALOG workspace"))

# COMMAND ----------
