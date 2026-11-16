-- hr-demo-env Snowflake DDL (canonical schema, V1)
-- Secrets via env/connection context only; nothing credentialed in this file.

CREATE SCHEMA IF NOT EXISTS HR_DEMO;

CREATE TABLE IF NOT EXISTS HR_DEMO.departments (
  dept_id   NUMBER AUTOINCREMENT PRIMARY KEY,
  name      VARCHAR NOT NULL UNIQUE,
  budget    NUMBER
);

CREATE TABLE IF NOT EXISTS HR_DEMO.roles (
  role_id     NUMBER AUTOINCREMENT PRIMARY KEY,
  dept_id     NUMBER NOT NULL REFERENCES HR_DEMO.departments(dept_id),
  title       VARCHAR NOT NULL,
  level       VARCHAR NOT NULL,
  base_salary NUMBER NOT NULL
);

CREATE TABLE IF NOT EXISTS HR_DEMO.employees (
  emp_id      NUMBER AUTOINCREMENT PRIMARY KEY,
  first_name  VARCHAR NOT NULL,
  last_name   VARCHAR NOT NULL,
  email       VARCHAR NOT NULL UNIQUE,
  dept_id     NUMBER NOT NULL REFERENCES HR_DEMO.departments(dept_id),
  role_id     NUMBER NOT NULL REFERENCES HR_DEMO.roles(role_id),
  manager_id  NUMBER REFERENCES HR_DEMO.employees(emp_id),
  hire_date   DATE NOT NULL,
  term_date   DATE,
  salary      NUMBER NOT NULL
);

CREATE TABLE IF NOT EXISTS HR_DEMO.attendance (
  att_id       NUMBER AUTOINCREMENT PRIMARY KEY,
  emp_id       NUMBER NOT NULL REFERENCES HR_DEMO.employees(emp_id),
  day          DATE NOT NULL,
  clock_in     TIME,
  clock_out    TIME,
  overtime_min NUMBER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS HR_DEMO.leaves (
  leave_id  NUMBER AUTOINCREMENT PRIMARY KEY,
  emp_id    NUMBER NOT NULL REFERENCES HR_DEMO.employees(emp_id),
  start_day DATE NOT NULL,
  end_day   DATE NOT NULL,
  kind      VARCHAR NOT NULL  -- vacation|sick|unpaid
);

CREATE TABLE IF NOT EXISTS HR_DEMO.lifecycle_events (
  ev_id    NUMBER AUTOINCREMENT PRIMARY KEY,
  emp_id   NUMBER NOT NULL REFERENCES HR_DEMO.employees(emp_id),
  ev_day   DATE NOT NULL,
  kind     VARCHAR NOT NULL,  -- promotion|raise|transfer
  details  VARIANT
);
