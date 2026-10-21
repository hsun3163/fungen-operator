#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(pecotmr))
a <- commandArgs(TRUE)
truth <- read.delim(a[1], check.names=FALSE)
variant_key <- function(x) {
  pieces <- strsplit(gsub('_', ':', sub('^chr', '', x)), ':', fixed=TRUE)
  vapply(pieces, function(p) {
    if (length(p) != 4 || is.na(as.integer(p[2]))) stop('Unsupported synthetic variant identifier: ',paste(p,collapse=':'))
    paste(p[1], as.integer(p[2]), paste(sort(p[3:4]),collapse=':'), sep=':')
  }, character(1))
}
out <- list()
for (i in seq_len(nrow(truth))) {
  t <- truth[i, ]
  folder <- file.path(a[2], 'finemapping', t$context, 'susie_twas')
  prefix <- paste0(t$context, '.', t$trait)
  fm <- file.path(folder, 'fine_mapping', paste0(prefix, '.univariate_bvsr.rds'))
  tw <- file.path(folder, 'twas_weights', paste0(prefix, '.univariate_twas_weights.rds'))
  stopifnot(file.exists(fm), file.info(fm)$size > 0, file.exists(tw), file.info(tw)$size > 0)
  obj <- readRDS(fm)
  stopifnot(is(obj, 'FineMappingResultBase'))
  if (t$planted == 0) next
  cs <- as.data.frame(credibleSets(obj))
  if (!'variant_id' %in% names(cs)) stop('Native credibleSets schema lacks variant_id: ', paste(names(cs),collapse=', '))
  if ('coverage' %in% names(cs)) cs <- cs[cs$coverage >= 0.95, ,drop=FALSE]
  found <- variant_key(t$variant) %in% variant_key(cs$variant_id)
  out[[length(out)+1]] <- data.frame(context=t$context,trait=t$trait,causal_in_95cs=as.integer(found))
}
write.table(do.call(rbind,out), a[3],sep='\t',quote=FALSE,row.names=FALSE)
