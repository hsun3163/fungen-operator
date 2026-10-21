# Run with the pinned scientific R against the retained patched upstream worker.
worker <- commandArgs(TRUE)[1]
for (expr in parse(worker)) {
  if (is.call(expr) && identical(expr[[1]], as.name("<-")) &&
      as.character(expr[[2]]) %in% c("read_pheno_metadata", "projection_with_ids")) eval(expr)
}
folder <- tempfile("pca-identity-"); dir.create(folder)
check_ids <- function(fid, iid, expected) {
  prefix <- file.path(folder, paste0("case", length(list.files(folder))))
  fam <- paste0(prefix,".fam")
  write.table(data.frame(fid,iid,0,0,0,-9),fam,quote=FALSE,row.names=FALSE,col.names=FALSE)
  scores <- projection_with_ids(matrix(seq_len(6),nrow=2),paste0(prefix,".bed"))
  stopifnot(identical(scores$ID,expected),identical(scores$PC1,1:2))
  stopifnot(inherits(try(projection_with_ids(matrix(1,nrow=1),paste0(prefix,".bed")),silent=TRUE),"try-error"))
}
check_ids(c("a","b"),c("a","b"),c("0:a","0:b"))
check_ids(c("0","0"),c("a","b"),c("0:a","0:b"))
check_ids(c("family1","family2"),c("a","b"),c("family1:a","family2:b"))
cat("PASS: three native FAM identity conventions and three sample-count mismatch guards\n")
