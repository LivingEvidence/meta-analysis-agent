#!/usr/bin/env Rscript
#
# SNIPPET: Generate forest, funnel, and sensitivity (leave-one-out) plots.
#
# Assumes `m` (meta object) and `dat`, `is_ratio`, `full_name` are already set.
# `output_dir` is the directory where files will be written.
# Adapt dimensions and titles to the actual data.
#
# This is a REFERENCE snippet. Adapt to the actual data.
#

library(meta)

plot_height <- max(6, nrow(dat) + 3)

# --- Forest Plot ---
pdf(file.path(output_dir, "forest_plot.pdf"), width = 12, height = plot_height)
forest(m,
       sortvar   = if ("year_num" %in% names(dat)) dat$year_num else NULL,
       prediction  = TRUE,
       print.tau2  = TRUE,
       print.I2    = TRUE,
       leftcols    = "studlab",
       leftlabs    = "Study",
       main        = paste(full_name, "- Forest Plot"))
dev.off()

png(file.path(output_dir, "forest_plot.png"),
    width = 1200, height = plot_height * 100, res = 100)
forest(m,
       sortvar   = if ("year_num" %in% names(dat)) dat$year_num else NULL,
       prediction  = TRUE,
       print.tau2  = TRUE,
       print.I2    = TRUE,
       leftcols    = "studlab",
       leftlabs    = "Study",
       main        = paste(full_name, "- Forest Plot"))
dev.off()

# --- Funnel Plot ---
pdf(file.path(output_dir, "funnel_plot.pdf"), width = 8, height = 7)
funnel(m, main = paste(full_name, "- Funnel Plot"))
dev.off()

png(file.path(output_dir, "funnel_plot.png"), width = 800, height = 700, res = 100)
funnel(m, main = paste(full_name, "- Funnel Plot"))
dev.off()

# --- Sensitivity (Leave-One-Out) Plot ---
loo <- metainf(m, pooled = "random")

pdf(file.path(output_dir, "sensitivity_plot.pdf"), width = 10, height = plot_height)
forest(loo, main = paste(full_name, "- Leave-One-Out"))
dev.off()

png(file.path(output_dir, "sensitivity_plot.png"),
    width = 1000, height = plot_height * 100, res = 100)
forest(loo, main = paste(full_name, "- Leave-One-Out"))
dev.off()

cat("Plots written to:", output_dir, "\n")
