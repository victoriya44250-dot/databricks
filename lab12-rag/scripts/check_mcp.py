"""Exercise the installed AI Dev Kit via its real MCP stdio transport."""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kit", required=True)
    parser.add_argument("--profile", default="lab12_free")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "evidence"
    output.mkdir(exist_ok=True)
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "profile": args.profile, "calls": []}
    env = dict(os.environ)
    env["DATABRICKS_CONFIG_PROFILE"] = args.profile
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(args.kit) / "databricks-mcp-server" / "run_server.py")],
        env=env,
    )
    name = "mcp_offline.json" if args.offline else "mcp_workspace.json"

    def save():
        (output / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            report["tools"] = [t.name for t in listing.tools]
            report["tool_count"] = len(listing.tools)
            print(f"MCP connected: {len(listing.tools)} tools", flush=True)
            save()
            if args.offline:
                return
            calls = [
                ("warehouse", "manage_warehouse", {"action": "list"}),
                ("counts", "execute_sql", {"sql_query": "SELECT 'pages' AS object_name, count(*) AS n FROM workspace.viktoriia_kalenichenko_lab12.document_pages UNION ALL SELECT 'chunks', count(*) FROM workspace.viktoriia_kalenichenko_lab12.document_chunks", "output_format": "json"}),
                ("chunks_grants", "execute_sql", {"sql_query": "SHOW GRANTS ON TABLE workspace.viktoriia_kalenichenko_lab12.document_chunks", "output_format": "json"}),
                ("rag_logs", "execute_sql", {"sql_query": "SELECT * FROM workspace.viktoriia_kalenichenko_lab12.rag_runs ORDER BY created_at DESC LIMIT 40", "output_format": "json"}),
            ]
            for label, tool, arguments in calls:
                print(f"Calling {label} ...", flush=True)
                try:
                    result = await asyncio.wait_for(session.call_tool(tool, arguments), timeout=180)
                    entry = {"label": label, "tool": tool, "result": result.model_dump(mode="json")}
                    print(f"{label}: {'ERROR' if result.isError else 'OK'}", flush=True)
                except Exception as exc:
                    entry = {"label": label, "tool": tool, "error": str(exc)}
                    print(f"{label}: ERROR: {exc}", flush=True)
                report["calls"].append(entry)
                save()
    print(output / name)


if __name__ == "__main__":
    asyncio.run(main())
