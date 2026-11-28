"""Exercise notebook logic with mocked remote boundaries; never call Databricks."""
import ast
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from src.rag_helpers import ABSTENTION, ALLOWED_PAGES, citation_check, make_prompt, parse_results

ROOT = Path(__file__).resolve().parents[1]


class NotebookIntegrationTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / "notebooks/06_evaluation.py").read_text(encoding="utf-8"))
        ask_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "ask")
        self.index = Mock()
        self.spark = Mock()
        self.spark.createDataFrame.return_value.selectExpr.return_value.first.return_value = {"answer": "Fact【p. 59】"}
        namespace = {"time": time, "index": self.index, "spark": self.spark,
                     "ABSTENTION": ABSTENTION, "ALLOWED_PAGES": ALLOWED_PAGES,
                     "citation_check": citation_check, "make_prompt": make_prompt,
                     "parse_results": parse_results}
        exec(compile(ast.Module(body=[ask_node], type_ignores=[]), "06_evaluation.py", "exec"), namespace)
        self.ask = namespace["ask"]

    def test_empty_retrieval_abstains_without_inference(self):
        self.index.similarity_search.return_value = {"manifest": {"columns": []}}
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.ask("Question?")
        self.assertEqual(result["answer"], ABSTENTION)
        self.assertEqual(result["pages"], [])
        self.spark.createDataFrame.assert_not_called()

    def test_baseline_does_not_retrieve_or_receive_evidence(self):
        result = self.ask("Question?", use_retrieval=False)
        self.index.similarity_search.assert_not_called()
        self.assertNotIn("EVIDENCE", result["prompt"])
        self.assertEqual(result["pages"], [])
        self.spark.createDataFrame.assert_called_once()

    def test_hybrid_preserves_filter_and_raw_answer_for_logging(self):
        self.index.similarity_search.return_value = {
            "manifest": {"columns": [{"name": name} for name in ["chunk_text", "page_number", "chunk_id"]]},
            "result": {"data_array": [["Evidence", 59.0, "chunk1"]]},
        }
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.ask("Question?", query_type="HYBRID")
        self.assertEqual(result["answer"], "Fact【p. 59】")
        self.assertEqual(result["pages"], [59])
        self.assertEqual(result["chunk_ids"], ["chunk1"])
        self.assertEqual(self.index.similarity_search.call_args.kwargs["filters"], {"page_number": ALLOWED_PAGES})
        self.assertEqual(self.index.similarity_search.call_args.kwargs["query_type"], "HYBRID")
        self.assertEqual(self.index.similarity_search.call_args.kwargs["num_results"], 5)
        self.spark.createDataFrame.assert_called_once()

    def test_imports_work_with_an_unrelated_working_directory(self):
        original_cwd = os.getcwd()
        original_path = sys.path[:]
        try:
            with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
                for filename in ("04_retrieval_test.py", "05_rag_answer.py", "06_evaluation.py", "07_smoke_test.py"):
                    with self.subTest(notebook=filename):
                        tree = ast.parse((ROOT / "notebooks" / filename).read_text(encoding="utf-8"))
                        start = next(i for i, node in enumerate(tree.body)
                                     if isinstance(node, ast.Import) and node.names[0].name == "sys")
                        end = next(i for i, node in enumerate(tree.body)
                                   if isinstance(node, ast.ImportFrom) and node.module == "src.rag_helpers")
                        widgets = SimpleNamespace(text=Mock(), get=Mock(return_value=str(ROOT)))
                        namespace = {"dbutils": SimpleNamespace(widgets=widgets)}
                        module = ast.Module(body=tree.body[start:end + 1], type_ignores=[])
                        exec(compile(module, filename, "exec"), namespace)
                        self.assertIs(namespace["parse_results"], parse_results)
                        self.assertEqual(namespace["project_root"], ROOT)
        finally:
            os.chdir(original_cwd)
            sys.path[:] = original_path

    def test_logging_schemas_remain_compatible(self):
        expected = {
            "05_rag_answer.py": "run_id STRING, mode STRING, question STRING, prompt STRING, answer STRING, retrieved_pages ARRAY<INT>, retrieved_chunk_ids ARRAY<STRING>",
            "06_evaluation.py": "question_id STRING, question STRING, answerable BOOLEAN, mode STRING, prompt STRING, answer STRING, retrieved_pages ARRAY<INT>, retrieved_chunk_ids ARRAY<STRING>, elapsed_seconds DOUBLE",
        }
        for filename, schema in expected.items():
            tree = ast.parse((ROOT / "notebooks" / filename).read_text(encoding="utf-8"))
            schemas = [" ".join(node.value.value.split()) for node in ast.walk(tree)
                       if isinstance(node, ast.keyword) and node.arg == "schema"
                       and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
            self.assertIn(schema, schemas)


if __name__ == "__main__":
    unittest.main()
