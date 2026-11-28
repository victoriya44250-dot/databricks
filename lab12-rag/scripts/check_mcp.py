"""Read-only checks through the Databricks MCP server registered for Codex.

Use the AI Dev Kit Python environment. No inference, job runs or mutations.
"""
import argparse
import asyncio
import json
import os
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "workspace.viktoriia_kalenichenko_lab12"


def clean(value):
    """Exclude identities, credentials and internal URLs from local evidence."""
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items() if not any(
            part in key.lower() for part in (
                "token", "secret", "credential", "password", "owner", "creator",
                "created_by", "updated_by", "run_as", "run_by", "email", "url",
                "storage_location", "principal", "user_name",
            ))}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"[\w.+-]+@[\w.-]+", "<redacted-user>", value)
        value = re.sub(r"dapi[a-zA-Z0-9]+", "<redacted-token>", value)
        return re.sub(r"(?i)(bearer\s+)\S+", r"\1<redacted>", value)
    return value


def payload(result):
    if result.structuredContent is not None:
        data = result.structuredContent
        return data.get("result", data)
    values = []
    for block in result.content:
        if block.type == "text":
            try:
                values.append(json.loads(block.text))
            except json.JSONDecodeError:
                values.append(block.text)
    return values[0] if len(values) == 1 else values


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT.parent / ".codex/config.toml")
    parser.add_argument("--profile", default="lab12_free")
    parser.add_argument("--offline", action="store_true", help="Only initialize and list MCP tools")
    args = parser.parse_args()
    registration = tomllib.loads(args.config.read_text(encoding="utf-8-sig"))["mcp_servers"]["databricks"]
    if registration.get("env", {}).get("DATABRICKS_CONFIG_PROFILE") != args.profile:
        raise ValueError("Registered MCP profile does not match the requested profile")
    if registration.get("enabled") is False:
        raise ValueError("Registered Databricks MCP server is disabled")
    output = ROOT / "evidence"
    output.mkdir(exist_ok=True)
    report = {"created_at": datetime.now(timezone.utc).isoformat(),
              "transport": "MCP stdio using project Codex registration",
              "profile": args.profile, "read_only": True, "calls": []}
    evidence_file = output / ("mcp_offline.json" if args.offline else "mcp_workspace.json")

    def save():
        evidence_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    server = StdioServerParameters(command=registration["command"], args=registration.get("args", []),
                                  env={**os.environ, **registration.get("env", {})})
    failed = False
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            report["tools"] = sorted(tool.name for tool in listing.tools)
            report["tool_count"] = len(listing.tools)
            save()
            print(f"MCP initialized: {len(listing.tools)} tools", flush=True)
            if args.offline:
                return

            async def call(label, tool, arguments):
                nonlocal failed
                if tool not in report["tools"]:
                    raise ValueError(f"Required MCP tool is unavailable: {tool}")
                print(f"MCP read: {label}", flush=True)
                try:
                    result = await asyncio.wait_for(session.call_tool(tool, arguments), timeout=180)
                    data = payload(result)
                    is_error = bool(result.isError or (isinstance(data, dict) and data.get("error")))
                    if label == "jobs" and isinstance(data, dict):
                        data = {"items": [job for job in data.get("items", [])
                                          if "lab12" in job.get("settings", {}).get("name", "").lower()
                                          or "lab12" in job.get("name", "").lower()]}
                    report["calls"].append({"label": label, "tool": tool, "arguments": arguments,
                                            "is_error": is_error, "result": clean(data)})
                    failed |= is_error
                    save()
                    print(f"{label}: {'ERROR' if is_error else 'OK'}", flush=True)
                    return data if not is_error else None
                except Exception as exc:
                    failed = True
                    report["calls"].append({"label": label, "tool": tool, "arguments": arguments,
                                            "is_error": True, "error_type": type(exc).__name__})
                    save()
                    print(f"{label}: ERROR ({type(exc).__name__})", flush=True)
                    return None

            calls = [
                ("schema", "manage_uc_objects", {"object_type": "schema", "action": "get", "full_name": SCHEMA}),
                ("volume", "manage_uc_objects", {"object_type": "volume", "action": "get", "full_name": f"{SCHEMA}.raw_docs"}),
                ("counts", "execute_sql", {"sql_query":
                    f"SELECT 'pages' AS object_name, COUNT(*) AS n FROM {SCHEMA}.document_pages "
                    f"UNION ALL SELECT 'chunks', COUNT(*) FROM {SCHEMA}.document_chunks", "output_format": "json"}),
                ("log_schemas", "execute_sql", {"sql_query":
                    "SELECT table_name, column_name, full_data_type FROM workspace.information_schema.columns "
                    "WHERE table_schema = 'viktoriia_kalenichenko_lab12' "
                    "AND table_name IN ('qa_log', 'qa_evaluation') ORDER BY table_name, ordinal_position", "output_format": "json"}),
                ("endpoint", "manage_vs_endpoint", {"action": "get", "name": "lab12_agri_search"}),
                ("index", "manage_vs_index", {"action": "get", "name": f"{SCHEMA}.document_chunks_index"}),
            ]
            for label, tool, arguments in calls:
                await call(label, tool, arguments)
            jobs = await call("jobs", "manage_jobs", {"action": "list", "limit": 100, "expand_tasks": False})
            for job in (jobs or {}).get("items", []):
                job_id = job["job_id"]
                await call(f"job_{job_id}", "manage_jobs", {"action": "get", "job_id": job_id})
                await call(f"runs_{job_id}", "manage_job_runs", {"action": "list", "job_id": job_id, "limit": 3})
    print(f"Sanitized evidence: {evidence_file}")
    if failed:
        raise SystemExit("One or more MCP checks failed; inspect evidence before claiming success")


if __name__ == "__main__":
    asyncio.run(main())
