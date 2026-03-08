#!/usr/bin/env Rscript
#
# SNIPPET: Fit a pairwise meta-analysis for pre-calculated effect sizes.
#
# Requires: dat$studlab + columns for effect size and CI bounds.
# Common column names: sm/effect, lower/lowerci, upper/upperci.
# Inspect the actual sheet first — column names may differ.
#
# This is a REFERENCE snippet. Adapt to the actual data.
#

library(meta)

# --- Detect effect size columns ---
# Check which column names are actually present; adapt as needed
sm_col    <- intersect(c("sm", "effect", "te", "logrr", "logor", "loghr"), names(dat))[1]
lower_col <- intersect(c("lower", "lowerci", "lower_ci", "ci_lower"), names(dat))[1]
upper_col <- intersect(c("upper", "upperci", "upper_ci", "ci_upper"), names(dat))[1]

if (is.na(sm_col) || is.na(lower_col) || is.na(upper_col)) {
  stop("Cannot find effect size columns. Available: ", paste(names(dat), collapse = ", "))
}

te    <- as.numeric(dat[[sm_col]])
lower <- as.numeric(dat[[lower_col]])
upper <- as.numeric(dat[[upper_col]])

# --- Scale detection for ratio measures ---
# If all values are positive, assume natural scale and log-transform
is_ratio <- measure %in% c("HR", "RR", "OR")
if (is_ratio && all(te > 0, na.rm = TRUE) && all(lower > 0, na.rm = TRUE)) {
  cat("Detected natural scale — applying log-transform.\n")
  te    <- log(te)
  lower <- log(lower)
  upper <- log(upper)
}

# Back-calculate standard error from CI
se <- (upper - lower) / (2 * qnorm(0.975))

m <- metagen(
  TE       = te,
  seTE     = se,
  studlab  = dat$studlab,
  sm       = measure,           # e.g. "HR", "MD", "SMD"
  method.tau = "REML",
  method.random.ci = if (nrow(dat) >= 5) "HK" else "classic",
  prediction = TRUE
)

cat("Model fitted:", m$k, "studies\n")
if (is_ratio) {
  cat("Pooled RE:", round(exp(m$TE.random), 4),
      "[", round(exp(m$lower.random), 4), ",", round(exp(m$upper.random), 4), "]\n")
} else {
  cat("Pooled RE:", round(m$TE.random, 4),
      "[", round(m$lower.random, 4), ",", round(m$upper.random, 4), "]\n")
}
