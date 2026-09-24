#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3L) stop("usage: read_sketch_region.R PREFIX INDEX_TSV RAW_OUT")
suppressPackageStartupMessages(library(pecotmr))
prefix <- args[[1]]
idx <- as.integer(read.delim(args[[2]], header = FALSE)[[1]])
p <- pecotmr:::open_pgen(paste0(prefix, ".pgen"))
on.exit(pgenlibr::ClosePgen(p), add = TRUE)
x <- pecotmr:::read_pgen(p, idx, meanimpute = FALSE)
if (!is.matrix(x) || ncol(x) != length(idx)) stop("reader returned an unexpected shape")
writeBin(as.double(x), args[[3]], size = 8L, endian = "little")
cat(sprintf("rows=%d variants=%d bytes=%d\n", nrow(x), ncol(x), file.info(args[[3]])$size))
