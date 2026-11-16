"""HR-metrics MCP server (R5). stdio JSON-RPC: one request per line.

Request:  {"tool": "<name>", "args": {...}}
Response: {"ok": true, "result": ...} | {"ok": false, "error": "..."}
Backends: sqlite (default; path via --db or HR_DB) or snowflake
(--backend or HR_BACKEND=snowflake; credentials from env only, see .env.example).
The MCP host passes env through; this file never carries secret values.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hr_demo_env import db, metrics  # noqa: E402

TOOLS = {
    "get_headcount": lambda conn, a: metrics.get_headcount(conn, a["as_of"]),
    "list_databases": lambda conn, a: db.show_databases(conn),
    "turnover_by_dept": lambda conn, a: metrics.turnover_by_dept(conn, a["start"], a["end"]),
    "attendance_anomalies": lambda conn, a: metrics.attendance_anomalies(
        conn, a["start"], a["end"], int(a.get("limit", 50))),
}


def dispatch(tool: str, args: dict, conn):
    if tool not in TOOLS:
        raise KeyError(f"unknown tool: {tool} (see tools.json)")
    return TOOLS[tool](conn, args or {})


def _mcp_tool_list():
    spec = os.path.join(os.path.dirname(__file__), "tools.json")
    try:
        with open(spec) as f:
            tools = json.load(f).get("tools", [])
        return [{"name": t["name"], "description": t.get("description", ""),
                 "inputSchema": t.get("input_schema", {"type": "object"})}
                for t in tools]
    except Exception:
        return [{"name": k, "description": k, "inputSchema": {"type": "object"}}
                for k in TOOLS]


def _handle_mcp(req, conn, ctx):
    method = req.get("method", "")
    rid = req.get("id")
    params = req.get("params", {}) or {}

    def reply(result):
        if rid is None:  # notification — no response
            return
        print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}), flush=True)

    def fail(msg):
        if rid is None:
            print(json.dumps({"ok": False, "error": msg}), file=sys.stderr, flush=True)
            return
        print(json.dumps({"jsonrpc": "2.0", "id": rid,
                           "error": {"code": -32000, "message": msg}}), flush=True)

    try:
        if method == "initialize":
            reply({"protocolVersion": "2024-11-05",
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "hr-demo-env", "version": "1.0.0"}})
        elif method in ("notifications/initialized",):
            return
        elif method == "ping":
            reply({})
        elif method == "tools/list":
            reply({"tools": _mcp_tool_list()})
        elif method == "tools/call":
            name = params.get("name", "")
            args = dict(params.get("arguments", {}) or {})
            extra = {k: args.pop(k) for k in ("warehouse", "database") if args.get(k)}
            use = (db.get_connection(backend=ctx["backend"], sqlite_path=ctx["db"], **extra)
                   if extra else conn)
            try:
                result = dispatch(name, args, use)
            finally:
                if use is not conn:
                    use.close()
            reply({"content": [{"type": "text", "text": json.dumps(result, default=str)}]})
        else:
            fail(f"unknown method: {method}")
    except Exception as exc:
        fail(str(exc))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("HR_DB", "data/dev.db"))
    ap.add_argument("--backend", default=os.environ.get("HR_BACKEND", "sqlite"))
    ap.add_argument("--warehouse", default=None,
                    help="Snowflake warehouse override (must be in SNOWFLAKE_WAREHOUSES)")
    ap.add_argument("--database", default=None,
                    help="Snowflake database override (empty = all databases)")
    a = ap.parse_args()
    conn = db.get_connection(backend=a.backend, sqlite_path=a.db,
                               warehouse=a.warehouse, database=a.database)
    ctx = {"backend": a.backend, "db": a.db}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": f"bad JSON: {exc}"}), flush=True)
            continue
        if "method" in req:  # MCP JSON-RPC from the host
            _handle_mcp(req, conn, ctx)
            continue
        try:
            args = req.get("args", {})
            extra = {k: args.pop(k) for k in ("warehouse", "database") if args.get(k)}
            use = db.get_connection(backend=a.backend, sqlite_path=a.db, **extra) if extra else conn
            try:
                result = dispatch(req["tool"], args, use)
            finally:
                if use is not conn:
                    use.close()
            print(json.dumps({"ok": True, "result": result}), flush=True)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}), flush=True)


if __name__ == "__main__":
    main()
