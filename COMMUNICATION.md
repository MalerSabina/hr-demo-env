# COMMUNICATION.md — hr-demo-env

## Interfaces

- CLI: `python -m hr_demo_env.generator [--seed 42] [--out data] [--db data/dev.db] [--n 300]`.
- MCP tools (`mcp/tools.json`): `get_headcount(as_of) → int`,
  `turnover_by_dept(start, end) → [{dept, started, left, rate}]`,
  `attendance_anomalies(start, end, limit?) → [{emp_id, day, type, detail}]`.
- Agent: `answer_question(question, conn, llm_client?) → {answer, sources[], refused}`.
- Error format: metrics raise `ValueError` on bad ranges; MCP server returns
  `{"ok": false, "error": "<message>"}`; agent degrades with metrics intact.

## Events

None — batch-seeded demo, no webhooks. (Row reserved if Tableau alerts are added later.)

## Hooks (harness)

| Matcher | Command | Purpose |
|---------|---------|---------|
| `Bash(rm -rf:*)` (PreToolUse) | echo + `exit 2` | Block destructive deletes (H1) |
| `Write\|Edit` (PostToolUse) | `py_compile` | Syntax check on save |

## HITL table

| # | Breakpoint | Trigger | Approver | On deny |
|---|------------|---------|----------|---------|
| H1 | Destructive ops | `rm -rf`, delete repo/branch, drop tables | user | Do the safe alternative, log it |
| H2 | Snowflake load | COPY into real account (FLOWS.md B.1) | user | Stay on SQLite (R7) |
| H3 | Tableau publish | Publishing extract/dashboards (FLOWS.md B.4) | user | Keep local `.twbx`, log plan |

No harness agents (assessed Step 0–1: none needed). No fine-tuning (adaptation `none`).
## Secrets / env contract (names only — values never in repo, chat, or logs)

`HR_BACKEND`, `HR_DB`, `SNOWFLAKE_ACCOUNT/USER/ROLE/WAREHOUSE/DATABASE/SCHEMA`,
`SNOWFLAKE_PRIVATE_KEY_PATH` (preferred) or `SNOWFLAKE_PASSWORD` (fallback).
The MCP server inherits these from the host process env; `.mcp.json` carries
no secrets. Missing vars fail with the var name, never a value. On startup `db.get_connection()`
also loads `<project>/.env` (stdlib parser; real env wins; `HR_ENV_FILE` overrides
path for tests) — so the MCP server picks up `SNOWFLAKE_PAT` with no host plumbing.

Local-only project: no repo touchpoints.
