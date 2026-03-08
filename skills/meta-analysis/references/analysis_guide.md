# Statistical Analysis Guide

## Overview

This guide describes the statistical methods used in the meta-analysis pipeline.
The analysis uses R packages `meta` (primary) and `metafor` (supplementary),
which implement standard pairwise meta-analysis methods.

## Model Selection

### Default: Random-Effects Model

All analyses use the **random-effects model** by default, because clinical
trials in a meta-analysis typically differ in patient populations, interventions,
and settings, making the assumption of a single true effect (fixed-effect)
unrealistic.

- **Estimator**: Restricted maximum-likelihood (REML) for tau²
- **Confidence intervals**: Knapp-Hartung adjustment when k >= 5 studies
- **Prediction interval**: Always reported (shows expected range for a future study)

### Fixed-Effect Model

The fixed-effect model (Mantel-Haenszel for binary data, inverse-variance
otherwise) is also computed and reported alongside, but the random-effects
result is primary.

## Analysis by Data Type

### Pre-calculated effect sizes (`pre`)

Uses `meta::metagen()`:

```r
metagen(
  TE = sm,           # Treatment effect (log-scale for ratio measures)
  lower = lower,     # Lower CI bound
  upper = upper,     # Upper CI bound
  studlab = paste(study, year),
  sm = measure,      # "HR", "RR", "OR", "MD", "SMD"
  method.tau = "REML"
)
```

The standard error is back-calculated from the confidence interval:
`se = (upper - lower) / (2 * qnorm(0.975))`

For ratio measures (HR, RR, OR), if values appear to be on the natural scale
(all positive), they are log-transformed before analysis.

### Raw binary data (`raw`)

Uses `meta::metabin()`:

```r
metabin(
  event.e = Et,      # Events in treatment
  n.e = Nt,          # Total in treatment
  event.c = Ec,      # Events in control
  n.c = Nc,          # Total in control
  studlab = paste(study, year),
  sm = measure,      # "RR", "OR", "RD"
  method = "MH",     # Mantel-Haenszel for fixed-effect
  method.tau = "REML"
)
```

**Zero-event handling**: When a study has zero events in one arm, a continuity
correction of 0.5 is added (default in `meta` package). Studies with zero
events in both arms are excluded by default.

## Heterogeneity Assessment

Reported statistics:
- **Q statistic**: Cochran's Q test for heterogeneity (chi-squared test)
- **I²**: Proportion of total variability due to between-study heterogeneity
  - 0–25%: Low
  - 25–50%: Moderate
  - 50–75%: Substantial
  - 75–100%: Considerable
- **tau²**: Between-study variance estimate (REML)
- **Prediction interval**: 95% prediction interval for the true effect in a
  new study setting

## Sensitivity Analysis

### Leave-One-Out

Each study is removed one at a time, and the meta-analysis is re-run. This
identifies:
- **Influential studies**: Studies whose removal substantially changes the
  pooled estimate
- **Robustness**: Whether statistical significance is maintained regardless
  of which study is removed

The output includes a table and plot showing the pooled estimate when each
study is excluded.

## Publication Bias

### Visual Assessment: Funnel Plot

A funnel plot displays each study's effect size against its standard error.
Asymmetry suggests potential publication bias or small-study effects.

### Statistical Tests

**Egger's test** (`meta::metabias()`):
- Tests for funnel plot asymmetry using a linear regression approach
- p < 0.10 conventionally suggests significant asymmetry
- **Caveat**: Unreliable with fewer than 10 studies — this is noted in the output

**For binary outcomes (raw data)**, the Harbord test or Peters test may be
used instead of Egger's, as Egger's can be biased for binary outcomes.

## Interpretation Notes

### Ratio Measures (HR, RR, OR)

- Results < 1 favor the treatment group
- Results > 1 favor the control group
- The pooled estimate and CI are reported on the natural scale in the summary,
  though computation is done on the log scale

### HR (Hazard Ratio) Specifics

- HR < 1 means lower hazard (better survival) in the treatment group
- The log(HR) and its SE are used internally for the meta-analysis
- Forest plots show HR on a log scale with a vertical reference line at HR = 1

### Absolute Measures (RD, MD, SMD)

- Results are reported on their original scale
- Negative or positive direction depends on the outcome definition
- Reference line in forest plots is at 0
