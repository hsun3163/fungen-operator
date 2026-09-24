#!/usr/bin/env python3
"""Versioned two-global-theta follow-up, triggered by the frozen MAF-stratified failure."""
import argparse,hashlib,json,math,os,pathlib,resource,subprocess,time
import numpy as np
import pandas as pd
import sketch_mwe as m

ROOT=m.ROOT; OUT=m.OUT/"two_stratum_v1"; PREP=OUT/"prepared"; RESULTS=OUT/"results"
HERE=pathlib.Path(__file__).resolve().parent
LOW=.05; B=m.B; SEED=m.SEED

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for x in iter(lambda:f.read(8*1024*1024),b""):h.update(x)
    return h.hexdigest()

def candidate_thetas():
    # Screening uses the existing chr22 full-grid `pair_maf_strata` RMSE summaries.
    # The final 3x3 choices are then compared on the original primary objective.
    vals=[]
    for p in (m.OUT/"results").glob("22_*_t*.json"):
        z=json.loads(p.read_text())
        if z.get("split")!="development":continue
        d={x["maf_pair_type"]:x for x in z.get("pair_maf_strata",[])}
        lowtypes=["0-0","0-1","1-1"]; hit=[d[x] for x in lowtypes if x in d]
        if hit:
            n=sum(x["n_pairs"] for x in hit); low=math.sqrt(sum(x["n_pairs"]*x["rmse"]**2 for x in hit)/n)
        else:low=np.nan
        high=d.get("2-2",{}).get("rmse",np.nan)
        vals.append({"theta":z["theta"],"region_id":z["region_id"],"low_maf_pair_rmse_unweighted":low,"high_maf_pair_rmse_unweighted":high})
    d=pd.DataFrame(vals)
    agg=d.groupby("theta").mean(numeric_only=True).reset_index()
    lo=agg.sort_values(["low_maf_pair_rmse_unweighted","theta"]).theta.head(3).to_list()
    hi=agg.sort_values(["high_maf_pair_rmse_unweighted","theta"]).theta.head(3).to_list()
    # Stable screen file and selected theta grids are retained with their documented role.
    RESULTS.mkdir(parents=True,exist_ok=True)
    d.to_csv(RESULTS/"chr22_stratum_candidate_screen.tsv",sep="\t",index=False)
    (RESULTS/"candidate_thetas.json").write_text(json.dumps({"low_maf_cutoff":LOW,"low_candidates":[float(x) for x in lo],"high_candidates":[float(x) for x in hi],
       "screen":"mean over development regions of pair-count-weighted within-stratum unweighted RMSE from already completed global-theta jobs",
       "selection":"promising-value screen only; 3x3 choices use the frozen primary objective on all fixed chr22 pairs"},indent=2)+"\n")
    return lo,hi

def prepare_reserved():
    PREP.mkdir(parents=True,exist_ok=True); work=m.OUT/"scratch"; work.mkdir(exist_ok=True)
    allregs=[]; profiles=[]; sources=[]; exclusion=[]
    main_order=json.loads((m.OUT/"prepared/sample_order_audit.json").read_text())["row_order_sha256"]
    for chrom in ["2","20"]:
        df,ex=m.load_metadata(chrom); exclusion.append({"chromosome":chrom,**ex})
        cands=m.candidate_rows(df,chrom,4)
        prof=m.profile_candidates(cands,chrom,work); profiles.extend(prof)
        chosen,g,notes=m.select_quadrants(prof,chrom,3)
        pre=m.source_prefix(chrom)
        src={"chromosome":chrom}
        for ext in ["pgen","pvar","psam","afreq"]:
            f=pathlib.Path(str(pre)+"."+ext); st=f.stat()
            src[ext]={"path":str(f),"size":st.st_size,"mtime_ns":st.st_mtime_ns,"full_sha256":sha(f) if ext!="pgen" else None}
        sources.append(src)
        ps=pathlib.Path(str(pre)+".psam"); ids=pd.read_csv(ps,sep="\t",comment="#",header=None,dtype=str).iloc[:,1].astype(str).tolist()
        if len(ids)!=B or hashlib.sha256("\n".join(ids).encode()).hexdigest()!=main_order: raise RuntimeError(f"reserved chromosome {chrom} sample-row order mismatch")
        for d in cands:
            cid=str(d.region_candidate.iloc[0])
            if cid not in chosen:continue
            region=d.sort_values(["P","pidx"],kind="stable").copy(); rid=f"{chrom}_{cid}"
            x,secs,_=m.read_sketch(chrom,region.pidx.to_numpy(),work)
            good=np.isfinite(x).all(axis=0)&(x.min(axis=0)>=-1e-8)&(x.max(axis=0)<=2+1e-8)&(x.std(axis=0)>0)
            bad=int((~good).sum());region=region.loc[good].reset_index(drop=True);x=x[:,good]
            pairs=m.make_pairs(region.P.to_numpy(),"reserve_"+rid); r=m.pair_corr(x,pairs)
            p=region.p_freq.to_numpy(float); maf=np.minimum(p,1-p); tie=np.random.default_rng(m.stable_seed("tie-key")).random(B)
            ranks=np.empty((len(region),B),np.uint16)
            for j in range(len(region)):
                xx=x[:,j] if p[j]<=.5 else -x[:,j]; key=tie if p[j]<=.5 else -tie
                order=np.lexsort((key,xx));ranks[j,order]=np.arange(1,B+1,dtype=np.uint16)
            rp=PREP/f"{rid}.ranks.u16";ranks.tofile(rp)
            ldbin=np.digitize(np.abs(r),[.1,.5],right=False).astype(np.uint8);w=np.zeros(len(r));H=max(1,len(np.unique(ldbin)))
            for k in np.unique(ldbin):w[ldbin==k]=1/(H*np.sum(ldbin==k))
            pp=PREP/f"{rid}.pairs.npz";np.savez_compressed(pp,pairs=pairs,r=r,ld_bin=ldbin,weights=w,
                maf_pair=np.column_stack([maf[pairs[:,0]],maf[pairs[:,1]]]).astype(np.float32))
            mp=PREP/f"{rid}.variants.tsv";region[["CHROM","POS","ID","REF","ALT","p_freq","pidx","P","is_snp"]].to_csv(mp,sep="\t",index=False)
            profile=next(x for x in prof if x["candidate"]==cid)
            allregs.append({"region_id":rid,"candidate":cid,"chromosome":chrom,"split":"reserved_validation","region_start":int(region.P.min()),"region_end":int(region.P.max()),
                "n_variants":len(region),"n_snps":int(region.is_snp.sum()),"n_indels":int((~region.is_snp).sum()),"n_invalid_source":bad,
                "rare_fraction":float((region.p_freq<.05).mean()),"pilot_mean_abs_r":profile["mean_abs_r"],
                "rank_cache":str(rp),"pair_cache":str(pp),"metadata_path":str(mp),"pair_count":len(pairs),"decode_seconds":secs,
                "input_hash":hashlib.sha256((sha(rp)+sha(pp)+sha(mp)).encode()).hexdigest(),"sample_order_sha256":main_order,
                "notes":"reserved untouched follow-up region; "+"; ".join(notes)})
            print(f"RESERVED_INPUT {rid} variants={len(region)} pairs={len(pairs)} seconds={secs:.1f}",flush=True)
    if len(allregs)!=6:raise RuntimeError(f"expected six reserved regions, got {len(allregs)}")
    pd.DataFrame(allregs).to_csv(PREP/"reserved_regions.tsv",sep="\t",index=False)
    pd.DataFrame(profiles).to_csv(PREP/"reserved_candidate_target_profiles.tsv",sep="\t",index=False)
    pd.DataFrame(exclusion).to_csv(PREP/"reserved_exclusions.tsv",sep="\t",index=False)
    (PREP/"reserved_sources.json").write_text(json.dumps(sources,indent=2)+"\n")

def transform_mixed(rank,p,theta_low,theta_high):
    maf=np.minimum(p,1-p);th=np.where(maf<LOW,theta_low,theta_high);M=np.floor(2*B*maf+.5).astype(np.int32)
    raw=np.floor(B*th*maf*maf+.5).astype(np.int32);n2=np.clip(raw,np.maximum(0,M-B),M//2);n1=M-2*n2;n0=B-n1-n2
    g=(rank>n0[:,None]).astype(np.uint8)+(rank>(n0+n1)[:,None]).astype(np.uint8);flip=p>.5
    g[flip]=2-g[flip]
    return g,n0,n1,n2,M,(raw!=n2),th

def loss_metrics(g,p,pairs,target,bins,maf_pair,theta_low,theta_high,clip):
    rr=m.pair_corr(g.T.astype(float),pairs);err=rr-target
    ms=[np.mean(err[bins==b]**2) for b in range(3) if np.any(bins==b)]
    af=g.mean(axis=1)/2;maf=np.minimum(af,1-af);m0=np.minimum(p,1-p);het=(g==1).mean(axis=1);hwe=2*m0*(1-m0)
    r2corr=np.corrcoef(rr*rr,target*target)[0,1] if np.std(rr*rr)>0 and np.std(target*target)>0 else np.nan
    cls=np.where(maf_pair<.01,0,np.where(maf_pair<.05,1,2));typ=np.sort(cls,axis=1);strata=[]
    for a in range(3):
      for b in range(a,3):
        ix=((typ[:,0]==a)&(typ[:,1]==b));
        if ix.any():strata.append({"type":f"{a}-{b}","n":int(ix.sum()),"rmse":float(np.sqrt(np.mean(err[ix]**2)))})
    return {"primary_rmse":float(np.sqrt(np.mean(ms))),"unweighted_rmse":float(np.sqrt(np.mean(err*err)),),
      "signed_r_correlation":float(np.corrcoef(rr,target)[0,1]) if np.std(rr)>0 and np.std(target)>0 else np.nan,
      "r2_rmse":float(np.sqrt(np.mean((rr*rr-target*target)**2))),"r2_correlation":float(r2corr),"strong_abs_r_bias":float(np.mean(np.abs(rr[np.abs(target)>=.5])-np.abs(target[np.abs(target)>=.5]))) if np.any(np.abs(target)>=.5) else np.nan,
      "max_alt_af_error":float(np.max(np.abs(af-p))),"mean_alt_af_mae":float(np.mean(np.abs(af-p))),
      "hwe_95pct":float(np.mean((np.abs(het-hwe)/np.maximum(hwe,1e-15))[m0>=.05]<=.1)) if np.any(m0>=.05) else np.nan,
      "conversion_rate":float(np.mean(g.max(axis=1)>g.min(axis=1))),"finite_count_clipped":int(clip.sum()),
      "pair_maf_strata":strata,"runtime_s":0.0,"peak_rss_mb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}

def make_dev_jobs():
    lo,hi=candidate_thetas();grid=[(float(a),float(b)) for a in lo for b in hi]
    regions=pd.read_csv(m.OUT/"prepared/regions.tsv",sep="\t").query("split == 'development'")
    rows=[]
    for _,r in regions.iterrows():
      for tl,th in grid:
        jid=f"{r.region_id}_low{tl:.6f}_high{th:.6f}"
        rows.append({"job_id":jid,"phase":"two_stratum_development","region_id":r.region_id,"chromosome":str(r.chromosome),
          "theta_low":tl,"theta_high":th,"rank_cache":r.rank_cache,"pair_cache":r.pair_cache,"metadata_path":r.metadata_path,
          "input_hash":r.input_hash,"seed":SEED,"B":B,"result_path":str(RESULTS/(jid+".json"))})
    pd.DataFrame(rows).to_csv(PREP/"development_jobs.tsv",sep="\t",index=False)
    print(f"development jobs={len(rows)} theta_low={lo} theta_high={hi}")

def worker(index=None,manifest=None):
    jobs=pd.read_csv(manifest or PREP/"development_jobs.tsv",sep="\t");i=index or int(os.environ["LSB_JOBINDEX"]);j=jobs.iloc[i-1]
    t0=time.time();pmeta=pd.read_csv(j.metadata_path,sep="\t");p=pmeta.p_freq.to_numpy(float);rank=np.fromfile(j.rank_cache,dtype=np.uint16).reshape((len(p),B))
    pc=np.load(j.pair_cache);g,n0,n1,n2,M,clip,ths=transform_mixed(rank,p,float(j.theta_low),float(j.theta_high))
    status="ok" if np.all(g.max(axis=1)>g.min(axis=1)) else "invalid_candidate"
    z=loss_metrics(g,p,pc["pairs"],pc["r"],pc["ld_bin"],pc["maf_pair"],j.theta_low,j.theta_high,clip)
    z.update({"status":status,"error_reason":"" if status=="ok" else "candidate-induced constant column",
      "job_id":j.job_id,"phase":j.phase,"region_id":j.region_id,"chromosome":str(j.chromosome),"theta_low":float(j.theta_low),"theta_high":float(j.theta_high),
      "B":B,"seed":SEED,"input_hash":j.input_hash,"code_hash":sha(HERE/"two_stratum_followup.py"),"runtime_s":time.time()-t0,"n_variants":len(p),"n_pairs":len(pc["pairs"]),
      "low_maf_variant_count":int((np.minimum(p,1-p)<LOW).sum()),"high_maf_variant_count":int((np.minimum(p,1-p)>=LOW).sum())})
    q=pathlib.Path(j.result_path);q.parent.mkdir(parents=True,exist_ok=True);tmp=q.with_suffix(".tmp");tmp.write_text(json.dumps(z,allow_nan=True));os.replace(tmp,q)

def reduce_dev():
    jobs=pd.read_csv(PREP/"development_jobs.tsv",sep="\t");arr=[]
    for _,j in jobs.iterrows():
      p=pathlib.Path(j.result_path)
      if not p.exists():raise RuntimeError(f"missing follow-up dev result: {j.job_id}")
      z=json.loads(p.read_text())
      if z.get("input_hash")!=j.input_hash or z.get("code_hash")!=sha(HERE/"two_stratum_followup.py"):raise RuntimeError(f"identity mismatch: {j.job_id}")
      arr.append(z)
    d=pd.DataFrame(arr);d.to_csv(RESULTS/"development_results.tsv",sep="\t",index=False)
    rows=[]
    for (lo,hi),g in d.groupby(["theta_low","theta_high"]):
      valid=(len(g)==8 and (g.status=="ok").all())
      rows.append({"theta_low":lo,"theta_high":hi,"n_regions":len(g),"primary_loss":float(np.sqrt(np.mean(g.primary_rmse**2))) if valid else np.nan,
          "unweighted_rmse":float(g.unweighted_rmse.mean()),"valid":bool(valid)})
    tab=pd.DataFrame(rows).sort_values(["theta_low","theta_high"]);tab.to_csv(RESULTS/"development_grid.tsv",sep="\t",index=False)
    valid=tab[tab.valid];minloss=valid.primary_loss.min();tied=valid[np.abs(valid.primary_loss-minloss)<=1e-6].copy();tied["distance_to_hwe"]=(tied.theta_low-1).abs()+(tied.theta_high-1).abs()
    best=tied.sort_values(["distance_to_hwe","theta_low","theta_high"]).iloc[0]
    sources=json.loads((PREP/"reserved_sources.json").read_text())
    frozen={"status":"frozen_before_reserved_validation","experiment":"two_stratum_v1","theta_low":float(best.theta_low),"theta_high":float(best.theta_high),
      "maf_cutoff":LOW,"low_stratum":"MAF < 0.05","high_stratum":"MAF >= 0.05","B":B,"seed":SEED,
      "formula_version":"global_homozygosity_multiplier_rank_quantile_v1_two_fixed_maf_strata",
      "primary_loss":"same equal-region/equal-nonempty-target-LD-bin RMSE on all original chr22 pairs; cross-stratum edges use the actual mixed transformation",
      "selected_development_loss":float(best.primary_loss),"selected_development_unweighted_rmse":float(best.unweighted_rmse),
      "candidate_screen":json.loads((RESULTS/"candidate_thetas.json").read_text()),"all_nine_joint_results":rows,
      "reserved_regions_sha256":sha(PREP/"reserved_regions.tsv"),"reserved_inputs":sources,
      "acceptance_contract":"same provisional numeric gates as the single-theta experiment; heldout scope limited to six reserved regions",
      "tie_rule":"within 1E-6, theta pair closest to (1,1), then lower theta_low and theta_high",
      "code_sha256":sha(HERE/"two_stratum_followup.py"),"development_jobs_sha256":sha(PREP/"development_jobs.tsv")}
    (OUT/"frozen_parameters.json").write_text(json.dumps(frozen,indent=2,allow_nan=True)+"\n")
    # Held-out transformation outcomes are materialized only after this freeze.
    regs=pd.read_csv(PREP/"reserved_regions.tsv",sep="\t");vr=[]
    for _,r in regs.iterrows():
      for label,lo,hi in [("two_theta",best.theta_low,best.theta_high),("hwe_baseline",1.,1.)]:
        jid=f"{r.region_id}_{label}"
        vr.append({"job_id":jid,"phase":"reserved_validation","region_id":r.region_id,"chromosome":str(r.chromosome),
          "theta_low":float(lo),"theta_high":float(hi),"rank_cache":r.rank_cache,"pair_cache":r.pair_cache,"metadata_path":r.metadata_path,
          "input_hash":r.input_hash,"seed":SEED,"B":B,"result_path":str(RESULTS/(jid+".json"))})
    pd.DataFrame(vr).to_csv(PREP/"validation_jobs.tsv",sep="\t",index=False)
    print(json.dumps({"status":"frozen_reserved_validation_ready","theta_low":best.theta_low,"theta_high":best.theta_high,"dev_primary_loss":best.primary_loss,"validation_jobs":len(vr)},indent=2))

def finalize():
    frozen=json.loads((OUT/"frozen_parameters.json").read_text()); frozen_worker_hash=frozen["code_sha256"]
    jobs=pd.read_csv(PREP/"validation_jobs.tsv",sep="\t");arr=[]
    for _,j in jobs.iterrows():
      p=pathlib.Path(j.result_path)
      if not p.exists():raise RuntimeError(f"missing heldout follow-up job {j.job_id}")
      z=json.loads(p.read_text())
      if z.get("input_hash")!=j.input_hash or z.get("code_hash")!=frozen_worker_hash:raise RuntimeError(f"identity mismatch {j.job_id}")
      arr.append(z)
    d=pd.DataFrame(arr);d.to_csv(RESULTS/"validation_results.tsv",sep="\t",index=False)
    best=d[d.phase=="reserved_validation"]
    best=best[best.job_id.str.endswith("two_theta")];base=d[d.job_id.str.endswith("hwe_baseline")]
    dev=pd.read_csv(RESULTS/"development_results.tsv",sep="\t");f=frozen
    devsel=dev[(dev.theta_low==f["theta_low"])&(dev.theta_high==f["theta_high"])]
    dr=float(np.sqrt(np.mean(devsel.primary_rmse**2)));vr=float(np.sqrt(np.mean(best.primary_rmse**2)));br=float(np.sqrt(np.mean(base.primary_rmse**2)))
    # Pair-weighted diagnostics pool regions only after reporting each region's objective value.
    res={"status":"complete","experiment":"two_stratum_v1","theta_low":f["theta_low"],"theta_high":f["theta_high"],"dev_regions":len(devsel),"validation_regions":len(best),
      "development_primary_loss":dr,"reserved_validation_primary_rmse":vr,"reserved_hwe_baseline_rmse":br,
      "validation_minus_development":vr-dr,"validation_over_development":vr/max(dr,.02),
      "validation_chromosome_rmse":best.groupby("chromosome").apply(lambda g:float(np.sqrt(np.mean(g.primary_rmse**2)))).to_dict(),
      "validation_max_alt_af_error":float(best.max_alt_af_error.max()),"validation_conversion_rate_min":float(best.conversion_rate.min()),
      "validation_hwe_95pct_min":float(best.hwe_95pct.min()),"validation_strong_abs_r_bias":float(best.strong_abs_r_bias.mean()),
      "validation_r2_rmse_mean":float(best.r2_rmse.mean()),"validation_signed_r_corr_mean":float(best.signed_r_correlation.mean()),
      "reserved_region_results":best[["region_id","chromosome","theta_low","theta_high","primary_rmse","unweighted_rmse","conversion_rate","max_alt_af_error","hwe_95pct","strong_abs_r_bias"]].to_dict(orient="records"),
      "acceptance":{"development_rmse_le_0.10":bool(dr<=.1),"validation_rmse_le_0.10":bool(vr<=.1),"transfer_delta_le_0.03":bool(vr-dr<=.03),
        "transfer_ratio_le_1.25":bool(vr/max(dr,.02)<=1.25),"max_af_error_bound":bool(best.max_alt_af_error.max()<=1/(4*B)+1e-10),
        "all_convert":bool((best.conversion_rate==1).all()),"limited_holdout":"six regions on chr2/chr20; adequate regime coverage must be reviewed"},
      "conclusion":"two-stratum follow-up requires scoped review of its six-region coverage and all frozen gates"}
    def clean(x):
      if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
      if isinstance(x,(list,tuple)):return [clean(v) for v in x]
      if isinstance(x,np.generic):return x.item()
      return x
    res=clean(res)
    (RESULTS/"summary.json").write_text(json.dumps(res,indent=2,allow_nan=True)+"\n");print(json.dumps(res,indent=2,allow_nan=True))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("command",choices=["prepare-reserved","dev-jobs","worker","reduce-dev","finalize"]);ap.add_argument("--index",type=int);ap.add_argument("--manifest")
    a=ap.parse_args()
    if a.command=="prepare-reserved":prepare_reserved()
    elif a.command=="dev-jobs":make_dev_jobs()
    elif a.command=="worker":worker(a.index,a.manifest)
    elif a.command=="reduce-dev":reduce_dev()
    elif a.command=="finalize":finalize()
if __name__=="__main__":main()
