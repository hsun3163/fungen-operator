#!/usr/bin/env python3
"""Source-sketch tie census and selected-subset content fingerprints."""
import hashlib,json,pathlib
import numpy as np,pandas as pd
import sketch_mwe as m
OUT=m.OUT; rows=[]
regions=pd.read_csv(OUT/"prepared/regions.tsv",sep="\t")
for _,r in regions.iterrows():
    x,secs,_=m.read_sketch(str(r.chromosome),pd.read_csv(r.metadata_path,sep="\t").pidx.to_numpy(),OUT/"scratch")
    sha=hashlib.sha256(np.asarray(x,dtype="<f8").tobytes(order="F")).hexdigest()
    per=[]
    for j in range(x.shape[1]):
        c=np.unique(x[:,j],return_counts=True)[1]
        per.append((B:=len(x),len(c),int(np.sum(c>1)),int(np.max(c)),int(np.sum(c[c>1])) if np.any(c>1) else 0))
    a=np.asarray(per,dtype=np.int64)
    rows.append({"region_id":r.region_id,"chromosome":str(r.chromosome),"variants":x.shape[1],
        "source_read_seconds":secs,"source_subset_content_sha256":sha,
        "fraction_variants_with_ties":float(np.mean(a[:,2]>0)),"mean_distinct_values_per_variant":float(a[:,1].mean()),
        "mean_excess_tied_rows_fraction":float(np.mean((a[:,0]-a[:,1])/a[:,0])),
        "mean_largest_tie_group_fraction":float(np.mean(a[:,3]/a[:,0])),
        "max_largest_tie_group_fraction":float(np.max(a[:,3]/a[:,0])),
        "mean_rows_in_tie_groups_fraction":float(np.mean(a[:,4]/a[:,0]))})
    del x
pd.DataFrame(rows).to_csv(OUT/"results/tie_and_source_subset_audit.tsv",sep="\t",index=False)
print(pd.DataFrame(rows)[["region_id","fraction_variants_with_ties","mean_excess_tied_rows_fraction","mean_largest_tie_group_fraction","max_largest_tie_group_fraction"]].to_string(index=False))
