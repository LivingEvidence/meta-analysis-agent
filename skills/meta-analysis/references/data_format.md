# Excel Data Format Specification

## Overview

The input Excel file (.xlsx) contains clinical trial outcome data organized
across multiple sheets. One special sheet ("Outcomes") serves as an index;
the remaining sheets each contain data for one clinical outcome.

## Outcomes Sheet

The "Outcomes" sheet is the index. Each row describes one outcome.

### Required Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `name` | string | Sheet name for this outcome | "OS" |
| `full_name` | string | Full descriptive name | "Overall Survival" |
| `measure` | string | Effect measure code | "HR" |
| `data_type` | string | Data format: "pre" or "raw" | "pre" |

### Supported Effect Measures

| Code | Full Name | Scale | Typical Data Type |
|------|-----------|-------|-------------------|
| HR | Hazard Ratio | Ratio (log) | pre |
| RR | Risk Ratio / Relative Risk | Ratio (log) | raw or pre |
| OR | Odds Ratio | Ratio (log) | raw or pre |
| RD | Risk Difference | Absolute | raw or pre |
| MD | Mean Difference | Absolute | pre |
| SMD | Standardised Mean Difference | Absolute | pre |

## Outcome Data Sheets

### Pre-calculated data (`data_type = "pre"`)

Used when studies report effect sizes directly (common for time-to-event
outcomes like HR).

| Column | Type | Description |
|--------|------|-------------|
| `study` | string | Study identifier (e.g., "Smith 2020") |
| `year` | integer | Publication year |
| `sm` | numeric | Summary measure (effect size) |
| `lower` | numeric | Lower bound of 95% CI |
| `upper` | numeric | Upper bound of 95% CI |
| `treatment` | string | Treatment arm name |
| `control` | string | Control arm name |

**Scale convention for ratio measures (HR, RR, OR)**:
- If all `sm`, `lower`, `upper` values are positive, they are assumed to be on
  the natural scale (e.g., HR = 0.75) and will be log-transformed automatically.
- If any values are negative or zero, they are assumed to already be on the
  log scale.

### Raw event count data (`data_type = "raw"`)

Used when studies report binary outcomes (events/totals in each arm).

| Column | Type | Description |
|--------|------|-------------|
| `study` | string | Study identifier |
| `year` | integer | Publication year |
| `Et` | integer | Number of events in treatment group |
| `Nt` | integer | Total participants in treatment group |
| `Ec` | integer | Number of events in control group |
| `Nc` | integer | Total participants in control group |
| `treatment` | string | Treatment arm name |
| `control` | string | Control arm name |

## Optional Columns

Both data types may include additional columns. The `treatment` and `control`
columns can be used to filter studies for specific comparisons, but the
default analysis pools all studies in the sheet.

## Naming Convention

Sheet names are typically abbreviations of clinical outcomes:
- OS = Overall Survival
- PFS = Progression-Free Survival
- ORR = Overall Response Rate
- DFS = Disease-Free Survival
- TTP = Time to Progression
- AE = Adverse Events
