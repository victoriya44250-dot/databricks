"""Build a self-contained Databricks notebook; standard library only."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build():
    cells = []
    def md(text):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)})
    def code(text):
        cells.append({"cell_type": "code", "metadata": {}, "source": text.splitlines(True), "outputs": [], "execution_count": None})

    md("""# Lab 12 — RAG answers, evaluation and logging
Run on **Serverless**, top to bottom. Uses the existing 550-chunk index.
Only `rag_runs` is written (append); source pages, chunks and index are preserved.
The evaluation calls the LLM 16 times. Keep the evaluation switch false for the first demo.
""")
    code("%pip install databricks-ai-search")
    code("dbutils.library.restartPython()")
    md("## 1. Configuration and functions\nThis cell is self-contained after the restart.")
    code((ROOT / "src/rag_helpers.py").read_text(encoding="utf-8") + "\n\n" + (ROOT / "notebooks/runtime.py").read_text(encoding="utf-8"))
    md("## 2. First grounded answer\nRead the answer and check its cited passages. A valid page number alone does not prove the claim.")
    code('demo = run_question("What are the three levels of agricultural risk management interventions in Italy?", expected_pages=[59])\nfor passage in demo["context"]:\n    print(f"\\n--- PDF page {passage[\'page_number\']} ---\\n{passage[\'chunk_text\']}")')
    md("## 3. Compare with no retrieval\nSame model and question, without the report context.")
    code('baseline = run_question("What are the three levels of agricultural risk management interventions in Italy?", mode="baseline")')
    md("## 4. Small development evaluation\nSet the `run_evaluation` widget to `true` after the demo works; the Bundle job supplies this parameter automatically. Eight cases, two answers per case. Reference answers are used only for review; they are never sent to the model. These are development examples, not an independent benchmark.")
    cases = json.loads((ROOT / "evaluation_cases.json").read_text(encoding="utf-8"))
    code("dbutils.widgets.text('run_evaluation', 'false')\nRUN_EVALUATION = dbutils.widgets.get('run_evaluation').lower() == 'true'\nEVAL_CASES = " + repr(cases) + '''
if RUN_EVALUATION:
    failures = []
    for case in EVAL_CASES:
        for mode in ["rag", "baseline"]:
            result = run_question(case["question"], mode=mode, question_id=case["id"], expected_pages=case["pages"])
            if result["status"] != "ok":
                failures.append(case["id"] + "/" + mode)
        print("REFERENCE FOR HUMAN REVIEW:", case["expected"])
    assert not failures, f"Some calls failed; inspect rag_runs: {failures}"
else:
    print("Evaluation skipped. Set the run_evaluation widget to true to run the 8 paired cases.")
''')
    md("## 5. Monitoring and review\nMetrics are diagnostic: expected-page hit means at least one expected page was retrieved. Citation format checks page membership, not factual support. Manually assess relevance, completeness and unsupported claims against the PDF.")
    code('''logs = spark.table(LOG_TABLE).filter(F.col("session_id") == SESSION_ID)
display(logs.select("question_id", "mode", "question", "answer", "retrieved_pages", "cited_pages", "citation_format_ok", "expected_page_hit", "elapsed_seconds", "status", "error").orderBy("created_at"))
display(logs.groupBy("mode").agg(
    F.count("*").alias("requests"),
    F.sum(F.when(F.col("status") == "error", 1).otherwise(0)).alias("errors"),
    F.round(F.avg("elapsed_seconds"), 2).alias("avg_seconds"),
    F.avg(F.col("expected_page_hit").cast("double")).alias("expected_page_hit_rate"),
    F.avg(F.col("citation_format_ok").cast("double")).alias("citation_format_pass_rate"),
))
print("Save the output or export the notebook with results as evidence. No quality score has been assumed.")
''')
    md("## 6. Access review (read-only)\nInspect actual grants. Do not grant access to all users. Full prompts are logged, so use public report questions only in this lab.")
    code('''for object_type, object_name in [
    ("CATALOG", "workspace"),
    ("SCHEMA", TARGET),
    ("VOLUME", f"{TARGET}.raw_docs"),
    ("TABLE", f"{TARGET}.document_chunks"),
    ("TABLE", LOG_TABLE),
]:
    print(object_type, object_name)
    try:
        display(spark.sql(f"SHOW GRANTS ON {object_type} {object_name}"))
    except Exception as exc:
        print("Grant inspection needs the appropriate privileges:", str(exc)[:300])
''')
    code('assert demo["status"] == "ok" and baseline["status"] == "ok", "Demo failed; inspect rag_runs.error"')
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 4}
    path = ROOT / "notebooks/05_rag_complete.ipynb"
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    build()
