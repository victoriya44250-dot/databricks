# This file is embedded into the generated notebook by build_notebook.py.
import json
import time
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from databricks.ai_search.client import AISearchClient
from pyspark.sql import functions as F

TARGET = "workspace.viktoriia_kalenichenko_lab12"
INDEX_NAME = f"{TARGET}.document_chunks_index"
LOG_TABLE = f"{TARGET}.rag_runs"
MODEL = "databricks-gpt-oss-120b"
TOP_K = 5
SOURCE_URL = "https://documents1.worldbank.org/curated/en/099032326044016306/pdf/P510294-1b00a8b1-c76f-419d-953a-46bd5805c044.pdf"
EXCLUDED_PAGES = {1, 2, 3, 4, 5, 6, 96, 97, 147}
ALLOWED_PAGES = [p for p in range(1, 148) if p not in EXCLUDED_PAGES]
SDK_VERSION = version("databricks-ai-search")
SESSION_ID = str(uuid.uuid4())
index = AISearchClient().get_index(index_name=INDEX_NAME)

LOG_SCHEMA = """
    run_id STRING, session_id STRING, created_at TIMESTAMP,
    question_id STRING, mode STRING, question STRING, prompt STRING,
    answer STRING, retrieved_pages STRING, retrieved_chunk_ids STRING,
    cited_pages STRING, invalid_citations STRING, citation_format_ok BOOLEAN,
    abstained BOOLEAN, expected_page_hit BOOLEAN, elapsed_seconds DOUBLE,
    model STRING, index_name STRING, sdk_version STRING,
    status STRING, error STRING
"""


def retrieve(question):
    response = index.similarity_search(
        query_text=question, query_type="ANN", num_results=TOP_K,
        columns=["chunk_id", "page_number", "chunk_text"],
        filters={"page_number": ALLOWED_PAGES},
    )
    return parse_results(response)


def generate(prompt):
    # Pass the prompt as data, never interpolate user text into SQL.
    result = spark.createDataFrame([(prompt,)], "prompt STRING").selectExpr(
        "ai_query('databricks-gpt-oss-120b', prompt) AS answer"
    ).first()
    answer = result["answer"]
    if not answer or not isinstance(answer, str):
        raise RuntimeError("Модель не повернула текстової відповіді")
    return answer


def run_question(question, mode="rag", question_id="demo", expected_pages=None):
    if mode not in {"rag", "baseline"}:
        raise ValueError("mode must be rag or baseline")
    start = time.perf_counter()
    context, answer, prompt, error = [], "", "", None
    checks = {"cited_pages": [], "invalid_pages": [],
              "citation_format_ok": None, "abstained": False}
    try:
        if mode == "rag":
            context = retrieve(question)
            prompt = make_prompt(question, context)
            answer = generate(prompt) if context else ABSTENTION
            checks = citation_check(answer, context)
        else:
            prompt = make_prompt(question)
            answer = generate(prompt)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:2000]
    pages = sorted({r["page_number"] for r in context})
    hit = bool(set(pages) & set(expected_pages)) if mode == "rag" and expected_pages else None
    record = (
        str(uuid.uuid4()), SESSION_ID, datetime.now(timezone.utc),
        question_id, mode, question, prompt, answer,
        json.dumps(pages), json.dumps([r["chunk_id"] for r in context]),
        json.dumps(checks["cited_pages"]), json.dumps(checks["invalid_pages"]),
        checks["citation_format_ok"], checks["abstained"], hit,
        round(time.perf_counter() - start, 3), MODEL, INDEX_NAME, SDK_VERSION,
        "error" if error else "ok", error,
    )
    # The model output was materialized above: logging does not re-run inference.
    spark.createDataFrame([record], LOG_SCHEMA).write.format("delta").mode("append").saveAsTable(LOG_TABLE)
    if error:
        print(f"{question_id} / {mode}: ERROR: {error}")
        return {"status": "error", "answer": "", "context": context}
    print(f"\n{question_id} / {mode} | {time.perf_counter() - start:.1f}s | pages: {pages}\n")
    print(normalize_citations(answer) if mode == "rag" else answer)
    if mode == "rag":
        if not checks["citation_format_ok"]:
            print("УВАГА: формат або номери посилань потребують перевірки.")
        for page in checks["cited_pages"]:
            if page in pages:
                print(f"PDF page {page}: {SOURCE_URL}#page={page}")
    return {"status": "ok", "answer": answer, "context": context, "checks": checks}


print(f"Ready. Index: {INDEX_NAME}; model: {MODEL}; SDK: {SDK_VERSION}")
print(f"Session: {SESSION_ID}; log table: {LOG_TABLE}")
