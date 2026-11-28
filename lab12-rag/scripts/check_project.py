"""Check Python syntax, notebook paths, shared imports and CI configuration offline."""
import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = [p for directory in ("src", "tests", "scripts", "notebooks")
             for p in (ROOT / directory).rglob("*.py")]
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    config = yaml.safe_load((ROOT / "databricks.yml").read_text(encoding="utf-8"))
    jobs = config["resources"]["jobs"]
    assert set(jobs) == {"rag_qa", "rag_smoke"}, "Unexpected Bundle resources"
    expected_paths = {
        "rag_qa": ["05_rag_answer.py", "06_evaluation.py"],
        "rag_smoke": ["07_smoke_test.py"],
    }
    for key, job in jobs.items():
        actual_paths = []
        for task in job["tasks"]:
            notebook = task["notebook_task"]
            path = (ROOT / notebook["notebook_path"]).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), f"Invalid notebook path: {path}"
            assert path.read_text(encoding="utf-8").startswith("# Databricks notebook source")
            assert notebook["base_parameters"]["project_root"] == "${workspace.file_path}"
            actual_paths.append(path.name)
        assert actual_paths == expected_paths[key], f"Unexpected task order: {key}"
        assert job["environments"][0]["spec"]["dependencies"] == ["databricks-ai-search==0.83"]
    assert (ROOT / "src/__init__.py").is_file()
    assert "src/*.py" in config["sync"]["include"]
    assert "screenshots/**" in config["sync"]["exclude"]
    for path in (ROOT / "notebooks").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "entry_point" not in text, f"Unsupported notebook-context import: {path}"
        assert "rag_runs" not in text, f"Obsolete logging table: {path}"
        if path.name[:2] in {"04", "05", "06", "07"}:
            assert "from src.rag_helpers import" in text, f"Missing shared helper import: {path}"
            assert 'dbutils.widgets.get("project_root")' in text
        if "%pip install databricks-ai-search" in text:
            assert "%pip install databricks-ai-search==0.83" in text
    workflow_text = (ROOT.parent / ".github/workflows/lab12.yml").read_text(encoding="utf-8")
    # BaseLoader retains GitHub's 'on' key, unlike YAML 1.1 boolean resolution.
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"pull_request", "push", "workflow_dispatch"}
    assert set(workflow["jobs"]) == {"tests", "bundle-check", "deploy"}
    assert workflow["jobs"]["deploy"]["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    assert "build_notebook" not in workflow_text
    assert "bundle run -t dev rag_qa" not in workflow_text, "CI must not run QA inference"
    assert "bundle run -t dev rag_smoke" in workflow_text
    assert "scripts/check_plan.py" in workflow_text
    print(f"PASS: syntax for {len(files)} Python files; Bundle paths, imports, SDK pins and workflow structure")


if __name__ == "__main__":
    main()
