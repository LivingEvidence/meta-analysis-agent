#!/usr/bin/env Rscript
#
# SNIPPET: Read the Outcomes index sheet from an Excel file.
#
# Usage example:
#   Rscript read_outcomes.R /data/input/study.xlsx
#
# Output: JSON with outcome metadata printed to stdout.
#

library(readxl)
library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)
excel_file <- args[1]

all_sheets <- excel_sheets(excel_file)

# Find "Outcomes" sheet (case-insensitive)
outcomes_idx <- which(tolower(all_sheets) == "outcomes")

if (length(outcomes_idx) == 0) {
  cat(toJSON(list(
    error = "No 'Outcomes' sheet found",
    available_sheets = all_sheets,
    outcomes = list()
  ), auto_unbox = TRUE, pretty = TRUE))
  quit(status = 1)
}

dat <- as.data.frame(read_excel(excel_file, sheet = all_sheets[outcomes_idx[1]]))
names(dat) <- trimws(tolower(names(dat)))

outcomes <- lapply(seq_len(nrow(dat)), function(i) list(
  name      = as.character(dat$name[i]),
  full_name = as.character(dat$full_name[i]),
  measure   = as.character(dat$measure[i]),
  data_type = as.character(dat$data_type[i])
))

cat(toJSON(list(outcomes = outcomes, all_sheets = all_sheets),
           auto_unbox = TRUE, pretty = TRUE))
