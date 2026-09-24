#!/usr/bin/env python3
"""Pair-level diagnostics and frozen-gate review for two_stratum_v1."""
import json,pathlib,hashlib
import numpy as np,pandas as pd
import sketch_mwe as m
import two_stratum_followup as f

OUT=m.OUT/"two_stratum_v1"; PREP=OUT/"prepared"; RES=OUT/"results"; B=m.B; SEED=m.SEED
frozen=json.loads((OUT/"frozen_parameters.json").read_text());tl=frozen["theta_low"];th=frozen["theta_high"]
regions=pd.read_csv(PREP/"reserved_regions.tsv",sep="\t");pairrows=[];variants=[]
for _,rg in regions.iterrows():
    meta=pd.read_csv(rg.metadata_path,sep="\t");p=meta.p_freq.to_numpy(float);maf=np.minimum(p,1-p)
    rank=np.fromfile(rg.rank_cache,dtype=np.uint16).reshape((int(rg.n_variants),B));g,n0,n1,n2,M,clip,ths=f.transform_mixed(rank,p,tl,th)
    pc=np.load(rg.pair_cache);pairs=pc["pairs"];target=pc["r"];r=m.pair_corr(g.T.astype(float),pairs);pairmaf=pc["maf_pair"]
    cls=np.where(pairmaf<.01,0,np.where(pairmaf<.05,1,2));typ=np.sort(cls,axis=1)
    for k,(i,j) in enumerate(pairs):
        pairrows.append({"region_id":rg.region_id,"chromosome":str(rg.chromosome),"target_r":target[k],"synthetic_r":r[k],"residual":r[k]-target[k],
            "ld_bin":["[0,.1)","[.1,.5)","[.5,1]"][int(pc["ld_bin"][k])],"maf_pair_type":f"{typ[k,0]}-{typ[k,1]}",
            "maf_i":pairmaf[k,0],"maf_j":pairmaf[k,1]})
    af=g.mean(axis=1)/2;het=(g==1).mean(axis=1);hwe=2*maf*(1-maf)
    for j,row in meta.iterrows():
        variants.append({"region_id":rg.region_id,"chromosome":str(rg.chromosome),"variant_id":row.ID,"maf":maf[j],"supplied_alt_af":p[j],
            "synthetic_alt_af":af[j],"alt_af_error":af[j]-p[j],"het_observed":het[j],"het_hwe":hwe[j],
            "relative_hwe_het_error":abs(het[j]-hwe[j])/max(hwe[j],1e-15),"finite_count_clipped":bool(clip[j]),"maf_stratum_theta":tl if maf[j]<.05 else th})
    del g,rank
pp=pd.DataFrame(pairrows);vv=pd.DataFrame(variants)
pp.to_csv(RES/"pair_metrics.tsv.gz",sep="\t",index=False,compression="gzip");vv.to_csv(RES/"variant_metrics.tsv.gz",sep="\t",index=False,compression="gzip")
strata=pp.groupby(["ld_bin","maf_pair_type"]).agg(n_pairs=("residual","size"),n_regions=("region_id","nunique"),
    rmse=("residual",lambda x:float(np.sqrt(np.mean(x*x)))),bias=("residual","mean")).reset_index()
strata.to_csv(RES/"heldout_ld_maf_strata.tsv",sep="\t",index=False)
region_tab=pp.groupby(["region_id","chromosome","ld_bin","maf_pair_type"]).agg(n_pairs=("residual","size"),rmse=("residual",lambda x:float(np.sqrt(np.mean(x*x))))).reset_index()
region_tab.to_csv(RES/"region_ld_maf_strata.tsv",sep="\t",index=False)
vals=pd.read_csv(RES/"validation_results.tsv",sep="\t");best=vals[vals.job_id.str.endswith("two_theta")];base=vals[vals.job_id.str.endswith("hwe_baseline")]
dev=pd.read_csv(RES/"development_results.tsv",sep="\t");ds=dev[(dev.theta_low==tl)&(dev.theta_high==th)]
dr=float(np.sqrt(np.mean(ds.primary_rmse**2)));vr=float(np.sqrt(np.mean(best.primary_rmse**2)));br=float(np.sqrt(np.mean(base.primary_rmse**2)))
pool={"signed_r_correlation":float(np.corrcoef(pp.target_r,pp.synthetic_r)[0,1]),"signed_rmse":float(np.sqrt(np.mean(pp.residual**2))),
  "signed_bias":float(pp.residual.mean()),"r2_rmse":float(np.sqrt(np.mean((pp.synthetic_r**2-pp.target_r**2)**2))),
  "strong_abs_r_bias":float(np.mean(np.abs(pp.loc[np.abs(pp.target_r)>=.5,"synthetic_r"])-np.abs(pp.loc[np.abs(pp.target_r)>=.5,"target_r"]))),
  "max_alt_af_error":float(vv.alt_af_error.abs().max()),"hwe_variant_fraction_within_10pct":float(np.mean(vv[vv.maf>=.05].relative_hwe_het_error<=.10)),
  "conversion_rate":float(best.conversion_rate.min()),"n_pairs":len(pp)}
chrom=best.groupby("chromosome").apply(lambda g:float(np.sqrt(np.mean(g.primary_rmse**2)))).to_dict()
covered=strata[(strata.n_pairs>=1000)&(strata.n_regions>=3)]
gates={"development_weighted_rmse_le_0.10":bool(dr<=.1),"heldout_weighted_rmse_le_0.10":bool(vr<=.1),
 "transfer_delta_le_0.03":bool(vr-dr<=.03),"transfer_ratio_le_1.25":bool(vr/max(dr,.02)<=1.25),
 "each_chromosome_weighted_rmse_le_0.15":bool(all(x<=.15 for x in chrom.values())),
 "covered_ld_maf_strata_rmse_le_0.15":bool((covered.rmse<=.15).all()),"adequately_covered_strata_count":int(len(covered)),
 "pooled_signed_r_correlation_ge_0.90":bool(pool["signed_r_correlation"]>=.90),"pooled_r2_rmse_le_0.10":bool(pool["r2_rmse"]<=.10),
 "strong_pair_abs_bias_le_0.10":bool(abs(pool["strong_abs_r_bias"])<=.10),"max_frequency_error_bound":bool(pool["max_alt_af_error"]<=1/(4*B)+1e-10),
 "hwe_95pct_for_maf_ge_0.05":bool(pool["hwe_variant_fraction_within_10pct"]>=.95),"all_columns_nonconstant":bool((best.conversion_rate==1).all())}
rng=np.random.default_rng(SEED);d=ds.primary_rmse.to_numpy();v=best.primary_rmse.to_numpy();nb=20000
bd=np.sqrt(np.mean(rng.choice(d,(nb,len(d)),replace=True)**2,axis=1));bv=np.sqrt(np.mean(rng.choice(v,(nb,len(v)),replace=True)**2,axis=1))
boot={"seed":SEED,"resampling_unit":"region","replicates":nb,"development_ci95":[float(x) for x in np.quantile(bd,[.025,.975])],
 "reserved_validation_ci95":[float(x) for x in np.quantile(bv,[.025,.975])],"difference_ci95":[float(x) for x in np.quantile(bv-bd,[.025,.975])]}
out={"experiment":"two_stratum_v1","status":"complete","conclusion":"supported in limited reserved scope" if all(gates[k] for k in gates if isinstance(gates[k],bool)) else "unsupported",
 "theta_low":tl,"theta_high":th,"maf_cutoff":.05,"development_weighted_rmse":dr,"reserved_validation_weighted_rmse":vr,
 "hwe_baseline_reserved_validation_weighted_rmse":br,"selected_vs_baseline_delta":vr-br,"reserved_chromosome_rmse":chrom,
 "pooled_pair_metrics":pool,"gates":gates,"covered_ld_maf_strata":covered.to_dict(orient="records"),"region_bootstrap":boot,
 "scope":"eight chr22 development regions and six chr2/chr20 reserved validation regions; no genome-wide validation"}
(RES/"acceptance.json").write_text(json.dumps(out,indent=2,allow_nan=True)+"\n")
print(json.dumps(out,indent=2,allow_nan=True))
