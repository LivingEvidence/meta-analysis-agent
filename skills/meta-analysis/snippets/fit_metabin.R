#!/usr/bin/env Rscript
#
# SNIPPET: Fit a pairwise meta-analysis for raw binary event-count data.
#
# Requires: dat$studlab, dat$et, dat$nt, dat$ec, dat$nc
# Columns may be named differently in the actual data — inspect first.
#
# This is a REFERENCE snippet. Adapt column names and measure to actual data.
#

library(meta)

# Assumes `dat` and `measure` ("RR", "OR", "RD") are already set
# Adapt column names if the sheet uses different names (e.g. "events_t" vs "et")

m <- metabin(
  event.e  = as.integer(dat$et),   # events in treatment arm
  n.e      = as.integer(dat$nt),   # total in treatment arm
  event.c  = as.integer(dat$ec),   # events in control arm
  n.c      = as.integer(dat$nc),   # total in control arm
  studlab  = dat$studlab,
  sm       = measure,               # e.g. "RR", "OR", "RD"
  method   = "MH",                  # Mantel-Haenszel for fixed-effect
  method.tau = "REML",
  method.random.ci = if (nrow(dat) >= 5) "HK" else "classic",
  prediction = TRUE
)

# Quick sanity check
cat("Model fitted:", m$k, "studies\n")
cat("Pooled RE:", round(exp(m$TE.random), 4),
    "[", round(exp(m$lower.random), 4), ",", round(exp(m$upper.random), 4), "]\n")

# Study-level TE and SE (on log scale for ratio measures)
te <- m$TE
se <- m$seTE
