"""Export only notebooks inside a clearly named Lab 12 folder in the user's workspace."""
import base64
import json
import re
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ExportFormat, ObjectType

root = Path(__file__).resolve().parents[1]
destination = root / "notebooks/original"
evidence = root / "evidence"
destination.mkdir(exist_ok=True)
evidence.mkdir(exist_ok=True)
w = WorkspaceClient(profile="lab12_free")
user = w.current_user.me().user_name
manifest = []


def visit(path, depth=0, in_lab=False):
    for item in w.workspace.list(path):
        name = item.path.rsplit("/", 1)[-1]
        if name.startswith("."):
            continue
        lab = in_lab or bool(re.search(r"lab[ _-]*12|л[ар][б _-]*12", name, re.I))
        if item.object_type == ObjectType.DIRECTORY and depth < 3:
            visit(item.path, depth + 1, lab)
        elif item.object_type == ObjectType.NOTEBOOK:
            entry = {"workspace_path": item.path, "exported": False}
            is_known_lab12 = depth == 0 and name in {
                "01_ingest_pdf_pages", "02_prepare_chunks", "03_create_search_index", "04_retrieval_test"
            }
            if lab or is_known_lab12:
                response = w.workspace.export(item.path, format=ExportFormat.JUPYTER)
                data = base64.b64decode(response.content)
                notebook = json.loads(data)
                notebook["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}
                # Preserve original code, but omit outputs (may include private prompts).
                for cell in notebook.get("cells", []):
                    cell["metadata"] = {}
                    if cell.get("cell_type") == "code":
                        cell["outputs"] = []
                        cell["execution_count"] = None
                filename = re.sub(r"[^\w. -]", "_", name) + f"_{item.object_id}.ipynb"
                (destination / filename).write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
                entry.update(exported=True, local_file=filename)
            manifest.append(entry)


visit(f"/Users/{user}")
(evidence / "original_notebooks_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Exported {sum(x['exported'] for x in manifest)} Lab 12 notebooks. Code requires review before committing.")
