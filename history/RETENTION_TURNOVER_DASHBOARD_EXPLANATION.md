# Retention & Turnover Risk Dashboard — Visual & Metric Breakdown

**Date:** 2026-11-15  
**Environment:** Tableau Cloud Web Authoring (`malersabina25-37fd130b43`)  
**Data Source:** Snowflake (`TEST_SANDBOX.ASSIGNMENT_SABINA`) via Stored Extract  
**Dashboard Name:** `Retention & Turnover Risk Dashboard`

---

## Executive Overview
The Retention & Turnover Risk Dashboard equips HR leadership, Chief People Officers, and department heads with strategic talent retention analytics. By breaking down active workforce distribution, attrition volume by department, and historical onboarding trajectories across 300 employees and 8 departments, leadership can identify departments experiencing elevated turnover and proactively mitigate retention risk.

---

## Detailed Chart-by-Chart Explanation

### Chart 1: Active Headcount by Department (`Headcount by Dept`)
- **Visual Form:** Horizontal Bar Chart
- **Shelves & Fields:**
  - **Rows (Y-axis):** `DEPARTMENTS.NAME` (Data, Engineering, Finance, HR, Marketing, Operations, Sales, Support)
  - **Columns (X-axis):** `CNTD(EMPLOYEES.EMP_ID)` (Distinct count of employees)
  - **Filters:** `EMPLOYEES.TERM_DATE` is NULL (isolates currently active employees)
- **What this chart shows:**
  - The live operational workforce distribution across business units.
  - Benchmarks departmental scale (e.g., Engineering and Operations as largest delivery organizations versus specialized functions like HR and Data).
- **Key Insights for HR Analysts:**
  - Forms the denominator for accurate departmental turnover rate calculations.
  - Highlights organizational structure balance and departmental span of control.

---

### Chart 2: Exits by Department (`Exits by Dept`)
- **Visual Form:** Departmental Attrition Bar Chart
- **Shelves & Fields:**
  - **Rows (Y-axis):** `DEPARTMENTS.NAME`
  - **Columns (X-axis):** `CNTD(EMPLOYEES.EMP_ID)` (Distinct count of departed employees)
  - **Filters:** `EMPLOYEES.TERM_DATE` is NOT NULL (isolates departed staff)
- **What this chart shows:**
  - The absolute volume of employee departures across each business unit over the dataset's historical timeframe.
  - When paired side-by-side with Chart 1 (`Headcount by Dept`), it immediately surfaces department-specific attrition hot spots (e.g., higher turnover rates in high-churn functions like Support or Operations vs. low churn in Data).
- **Key Insights for HR Analysts:**
  - Flags retention risk hotspots that require exit interview audits, compensation benchmarking, or management effectiveness reviews.
  - Supplies the numerator for the AI Agent's `turnover_by_dept` metric tool.

---

### Chart 3: Hiring Cohorts Over Time (`Hires Over Time`)
- **Visual Form:** Time-Series Longitudinal Line / Area Chart
- **Shelves & Fields:**
  - **Columns (X-axis):** `EMPLOYEES.HIRE_DATE` (Continuous Month over 24+ months)
  - **Rows (Y-axis):** `CNTD(EMPLOYEES.EMP_ID)` (New hires onboarded per month)
- **What this chart shows:**
  - Historical recruitment velocity and cohort onboarding cycles.
  - Visualizes company expansion waves, hiring freezes, and onboarding cadence over the multi-year demo timeframe.
- **Key Insights for HR Analysts:**
  - Correlates hiring surges with subsequent turnover trends (e.g., testing whether rapid hiring cohorts suffer higher 90-day attrition).
  - Validates recruitment capacity and workforce planning forecast accuracy.

---

## Alignment with AI Agent & MCP Layer
- **Unified Logic:** The dimensions and metrics visualized here exactly match the MCP tool `turnover_by_dept(start, end)` and `get_headcount(as_of)`.
- **Grounded Citing:** When end-users ask the chat agent questions like *"Which department has the highest turnover?"* or *"What is our headcount?"*, the agent answers with the exact numbers reflected in these visual charts and cites the **Retention & Turnover Risk Dashboard** as the authoritative source.
