# FLOWS.md — hr-demo-env

## A. Seed → query (local)

1. `python -m hr_demo_env.generator --seed 42` → CSVs + `data/dev.db`.
2. `python -m hr_demo_env.agent "turnover in Engineering last quarter?"` → grounded answer.
3. `pytest` → green; results logged in EVIDENCE.md.

## B. Seed → Snowflake → Tableau (guided, manual)

1. **[HITL]** Approve target account/warehouse + confirm fictitious-data-only. Deny → stay on SQLite (R7).
2. Run `sql/snowflake_ddl.sql`, load CSVs via documented COPY pattern.
3. Build Tableau extract; implement the 2 dashboard specs.
4. **[HITL]** Approve publish of dashboards/extract. Deny → keep local `.twbx`, log plan.

## C. Chat with your data (R6)

1. User asks NL question → agent routes to 1+ MCP metric tools.
2. Tools return rows → agent composes answer with `sources[]` (dashboard/metric names).
3. No matching metric → `refused: True`, suggests answerable questions.

## Error paths

- Bad dates → `ValueError` naming expected format.
- Missing `SNOWFLAKE_*` env → error names the var, no stack-trace leak of values.
- LLM unreachable → error + already-gathered metric rows returned for transparency.
