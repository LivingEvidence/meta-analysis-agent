# final.json Schema

This file defines the exact structure the frontend expects.
The Agent **must** produce `final.json` in this format in the run output directory.

---

## Top-level Structure

```json
{
  "session_id": "string",
  "request_id": "string",
  "created_at": "2024-01-01T00:00:00Z",
  "outcomes": [ /* array of OutcomeAnalysis objects */ ],
  "metadata": {}
}
```

---

## OutcomeAnalysis Object

```json
{
  "outcome_name": "OS",
  "full_name": "Overall Survival",
  "measure": "HR",
  "data_type": "pre",
  "is_ratio": true,
  "n_studies": 8,
  "studies": [ /* StudyResult[] */ ],
  "pooled_random": { /* PooledEstimate */ },
  "pooled_fixed": { /* PooledEstimate, optional */ },
  "heterogeneity": { /* Heterogeneity */ },
  "publication_bias": { /* PublicationBias, optional */ },
  "leave_one_out": [ /* LeaveOneOut[] */ ],
  "interpretation": "string (optional)"
}
```

### Field notes

| Field | Required | Description |
|---|---|---|
| `outcome_name` | ✅ | Short name, used as the tab label in the UI |
| `full_name` | ✅ | Full descriptive name, shown in summaries |
| `measure` | ✅ | One of: `HR`, `RR`, `OR`, `RD`, `MD`, `SMD` |
| `data_type` | ✅ | `"pre"` (pre-calculated) or `"raw"` (event counts) |
| `is_ratio` | ✅ | `true` for HR/RR/OR — controls log-scale x-axis in forest plot |
| `n_studies` | ✅ | Integer count of studies included |
| `studies` | ✅ | Array; may be empty if analysis was skipped |
| `pooled_random` | ✅ | Random-effects pooled estimate |
| `pooled_fixed` | ❌ | Fixed-effect estimate, include if available |
| `heterogeneity` | ✅ | Heterogeneity statistics |
| `publication_bias` | ❌ | Egger's test result; omit if < 3 studies |
| `leave_one_out` | ✅ | Leave-one-out array; use `[]` if unavailable |
| `interpretation` | ❌ | Agent's plain-language interpretation |

---

## StudyResult

```json
{
  "study": "Smith 2020",
  "year": 2020,
  "effect": 0.72,
  "ci_lower": 0.55,
  "ci_upper": 0.94,
  "weight": 18.5,
  "se": 0.136
}
```

**Scale convention:** `effect`, `ci_lower`, `ci_upper` must be on the **natural scale**
(i.e., NOT log-transformed), even for ratio measures.
- HR = 0.72, not log(0.72) = -0.329
- The frontend renders these directly on a log x-axis via D3

`se` is the standard error on the log scale for ratio measures (used for funnel plot).

---

## PooledEstimate

```json
{
  "model": "random",
  "effect": 0.68,
  "ci_lower": 0.54,
  "ci_upper": 0.85,
  "z_value": -3.72,
  "p_value": 0.0002
}
```

Same natural-scale convention as StudyResult.
`z_value` is optional. `p_value` is required.

---

## Heterogeneity

```json
{
  "tau2": 0.0123,
  "i2": 34.5,
  "q_statistic": 10.7,
  "q_df": 7,
  "q_pvalue": 0.153,
  "prediction_lower": 0.41,
  "prediction_upper": 1.12
}
```

`prediction_lower` / `prediction_upper`: prediction interval on natural scale.
Set to `null` if not computed.

---

## PublicationBias

```json
{
  "method": "Egger",
  "statistic": 1.84,
  "p_value": 0.089,
  "note": "Only 8 studies — Egger's test may be unreliable with < 10 studies."
}
```

`statistic` and `p_value` may be `null` if the test could not be run.

---

## LeaveOneOut

```json
{
  "excluded_study": "Smith 2020",
  "effect": 0.71,
  "ci_lower": 0.56,
  "ci_upper": 0.90
}
```

Natural scale. One entry per study omitted.

---

## Skipped Outcome

If an outcome cannot be analysed (e.g., fewer than 2 studies), include it in
`outcomes` with a minimal object and `n_studies: 0` / empty `studies`:

```json
{
  "outcome_name": "AE",
  "full_name": "Adverse Events",
  "measure": "RR",
  "data_type": "raw",
  "is_ratio": true,
  "n_studies": 1,
  "studies": [],
  "pooled_random": null,
  "heterogeneity": null,
  "leave_one_out": [],
  "interpretation": "Skipped: only 1 study found — meta-analysis requires at least 2."
}
```

The frontend gracefully handles `null` pooled estimates by showing a message.

---

## Complete Example

```json
{
  "session_id": "abc123",
  "request_id": "def456",
  "created_at": "2024-03-01T12:00:00Z",
  "outcomes": [
    {
      "outcome_name": "OS",
      "full_name": "Overall Survival",
      "measure": "HR",
      "data_type": "pre",
      "is_ratio": true,
      "n_studies": 8,
      "studies": [
        { "study": "Smith 2018", "year": 2018, "effect": 0.82, "ci_lower": 0.65, "ci_upper": 1.03, "weight": 14.2, "se": 0.118 },
        { "study": "Jones 2020", "year": 2020, "effect": 0.61, "ci_lower": 0.48, "ci_upper": 0.78, "weight": 19.8, "se": 0.124 }
      ],
      "pooled_random": { "model": "random", "effect": 0.71, "ci_lower": 0.58, "ci_upper": 0.87, "z_value": -3.4, "p_value": 0.0007 },
      "pooled_fixed":  { "model": "fixed",  "effect": 0.69, "ci_lower": 0.58, "ci_upper": 0.82, "z_value": -4.1, "p_value": 0.00004 },
      "heterogeneity": { "tau2": 0.018, "i2": 28.3, "q_statistic": 9.76, "q_df": 7, "q_pvalue": 0.202, "prediction_lower": 0.44, "prediction_upper": 1.14 },
      "publication_bias": { "method": "Egger", "statistic": 1.23, "p_value": 0.245, "note": null },
      "leave_one_out": [
        { "excluded_study": "Smith 2018", "effect": 0.68, "ci_lower": 0.55, "ci_upper": 0.84 },
        { "excluded_study": "Jones 2020", "effect": 0.74, "ci_lower": 0.60, "ci_upper": 0.91 }
      ],
      "interpretation": "The pooled HR of 0.71 (95% CI 0.58–0.87) indicates a statistically significant survival benefit. Heterogeneity is low (I²=28%), and the result is robust across all leave-one-out analyses."
    }
  ],
  "metadata": {}
}
```
