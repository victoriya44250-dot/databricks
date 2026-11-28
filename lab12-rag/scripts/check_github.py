"""Read GitHub environment secret names and workflow status; never print credentials."""
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPOSITORY = "victoriya44250-dot/databricks"
ROOT = Path(__file__).resolve().parents[1]


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        credentials = subprocess.run(
            ["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, check=False,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"},
        )
        fields = dict(line.split("=", 1) for line in credentials.stdout.splitlines() if "=" in line)
        token = fields.get("password")
    if not token:
        raise SystemExit("No non-interactive GitHub credential is available; no secret values were printed")

    def get(path):
        request = Request(f"https://api.github.com/repos/{REPOSITORY}/{path}", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "lab12-read-only-check",
        })
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            return {"http_status": exc.code}

    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "repository": REPOSITORY,
              "transport": "GitHub REST using existing Git credential; read-only"}
    for label, path in [
        ("environment_secrets", "environments/lab12-dev/secrets"),
        ("repository_secrets", "actions/secrets"),
    ]:
        data = get(path)
        report[label] = {"names": sorted(item["name"] for item in data.get("secrets", [])),
                         "http_status": data.get("http_status", 200)}
    environment = get("environments/lab12-dev")
    report["environment"] = {key: environment.get(key) for key in
                             ["name", "protection_rules", "deployment_branch_policy", "http_status"]}
    runs = get("actions/workflows/lab12.yml/runs?per_page=5")
    report["recent_runs"] = [{key: run.get(key) for key in
                              ["id", "event", "head_sha", "head_branch", "status", "conclusion", "html_url"]}
                             for run in runs.get("workflow_runs", [])]
    expected = {"LAB12_DATABRICKS_HOST", "LAB12_DATABRICKS_TOKEN"}
    available = set(report["environment_secrets"]["names"] + report["repository_secrets"]["names"])
    report["required_secret_names_present"] = sorted(expected & available)
    report["missing_or_unreadable_secret_names"] = sorted(expected - available)
    destination = ROOT / "evidence/github_preflight.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if expected - available:
        raise SystemExit("Required secret names are missing or metadata access is unavailable")


if __name__ == "__main__":
    main()
