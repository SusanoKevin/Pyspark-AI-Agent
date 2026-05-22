# Excelsis360 Data Policy

## Overview

This document defines how the Excelsis360 Data Agent accesses, evaluates, and reports on platform data. All data domains (attendance, enrollment, HR, academics) share a common configuration model; domain-specific thresholds and rules are set via environment variables.

## Configurable Data Domain

The agent's primary data domain is configured through environment variables:

| Variable | Description | Example |
|---|---|---|
| `PRIMARY_TABLE` | Main table the agent queries | `attendance_records` |
| `METRIC_COLUMN` | Column that holds the status/metric value | `status` |
| `POSITIVE_VALUE` | Value that counts as a positive outcome | `present` |
| `ENTITY_COLUMN` | Row-level entity identifier | `student_id` |
| `ENTITY_NAME_COLUMN` | Human-readable entity name | `student_name` |
| `GROUP_COLUMNS` | Comma-separated grouping dimensions | `class,grade` |

## Threshold Alerting

Entities whose positive-outcome rate falls below `AT_RISK_THRESHOLD` (default `75.0`) are flagged as at-risk. This threshold applies across all configured data domains.

| Rate | Status | Action |
|---|---|---|
| ≥ 90% | Good Standing | No action required |
| 75%–89% | Acceptable | Advisory notice |
| 60%–74% | At-Risk | Written warning; mandatory review |
| < 60% | Critical | Escalation; committee review |

## Attendance Domain Example

When `PRIMARY_TABLE=attendance_records`, `METRIC_COLUMN=status`, `POSITIVE_VALUE=present`:

- **Present** — Entity completed the full session.
- **Absent** — Entity did not attend without prior notification.
- **Late** — Entity arrived more than 10 minutes after session start.
- **Excused** — Absence approved in advance (documentation required within 3 school days).

Late-arrival rules:
- Within 10 minutes → Present
- 10–30 minutes late → Late
- > 30 minutes late → Absent
- Three Late records in one month = one Absent for reporting purposes

## Reporting Periods

- Weekly reports: Monday through Sunday
- Monthly reports: calendar month
- Semester reports: end of each academic semester
- The at-risk threshold for all automated reports is `AT_RISK_THRESHOLD` (default 75%) unless overridden.

## SQL Access Rules

The agent enforces read-only SQL access:
- Only SELECT statements are permitted (enforced at AST level via sqlglot).
- Only databases listed in `SQL_DATABASES` can be queried.
- All user-supplied values are parameterized — never string-interpolated into SQL.
