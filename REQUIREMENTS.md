# REQUIREMENTS.md — hr-demo-env

Fictitious HR demo: Snowflake DWH + 2 Tableau dashboards + Claude chat agent over the metrics.

## Functional

- R1 — Snowflake DDL for a normalized HR schema: employees, departments, roles, manager hierarchy, attendance logs, leaves, lifecycle events.
- R2 — Fictitious data generator spanning ≥ 2 years with enough volume for trend analysis (hundreds of employees, daily attendance).
- R3 — Documented Snowflake load path (SQL + COPY pattern, secrets via env, never in repo).
- R4 — Tableau extract guide + exactly 2 dashboards: Attendance Anomaly, Retention & Turnover Risk (metric specs included).
- R5 — MCP HR-metrics server: `get_headcount`, `turnover_by_dept`, `attendance_anomalies` with JSON input/output schemas.
- R6 — Chat agent answers NL questions grounded in MCP metric results; cites the source dashboard/metric; refuses out-of-scope questions.
- R7 — Local dev parity: same model + metrics runnable on SQLite with zero cloud credentials.

## Non-functional

- N1 — Fictitious data only; no real PII anywhere (names, emails, phones all generated).
- N2 — Reproducible: seeded RNG, same seed → same dataset.
- N3 — `pytest` suite green; README commands copy-paste runnable.
- N4 — No secrets in repo (Snowflake/Tableau creds via env only).
- N5 — Node.js 18+ with `npx` required for Tableau MCP server (`npx -y @tableau/mcp-server@latest` per `.mcp.json`); Tableau creds via `TABLEAU_SERVER`, `TABLEAU_SITE`, `TABLEAU_PAT_NAME`, `TABLEAU_PAT_SECRET` env only.

## Out of scope

- Actual Snowflake/Tableau provisioning and clicking (documented, not executed here).
- More than 2 dashboards; production deployment; SSO/auth integration.
- Model fine-tuning (adaptation: `none` — prompt + metric grounding only).
