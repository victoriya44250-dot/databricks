"""Reject plans that create/delete resources or target different deployed jobs."""
import argparse
import json
from pathlib import Path

EXPECTED_JOBS = {
    "resources.jobs.rag_qa": 708337744279402,
    "resources.jobs.rag_smoke": 333515008590836,
}


def check_plan(document):
    if document.get("plan_version") != 2:
        raise ValueError("Unsupported plan format; review the CLI version and plan manually")
    changes = document.get("plan", {})
    if set(changes) != set(EXPECTED_JOBS):
        raise ValueError("Plan must contain exactly the two existing Lab 12 jobs")
    summary = []
    for key, expected_id in EXPECTED_JOBS.items():
        resource = changes[key]
        action = resource.get("action")
        if action not in {"update", "skip"}:
            raise ValueError(f"Unexpected resource action for {key}: {action}")
        actual_id = resource.get("remote_state", {}).get("job_id")
        if actual_id != expected_id:
            raise ValueError(f"Existing job ID does not match for {key}: {actual_id}")
        summary.append({"resource": key, "job_id": expected_id, "action": action})
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    summary = json.dumps(check_plan(plan), indent=2)
    if args.summary:
        args.summary.write_text(summary + "\n", encoding="utf-8")
    print(summary)
    print("Plan accepted: existing jobs only; no resource creation or deletion")
