#!/usr/bin/env python3
"""Method checks, dense-LD audit, and final tables/figures for the frozen MWE."""
import hashlib, importlib.util, json, pathlib, subprocess, sys, math
import numpy as np
import pandas as pd

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/"output/sketch_to_plink1"
CORE=HERE/"sketch_mwe.py"
PY="/sc/arion/work/sunh14/conda/envs/py3.11/bin/python"
R="/sc/arion/work/sunh14/conda/envs/py3.11/bin/Rscript"
SEED=20260923; B=10000
sp=importlib.util.spec_from_file_location("sketch_mwe",CORE); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m)

def hfile(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()

def method_audit():
    rng=np.random.default_rng(SEED)
    X=rng.normal(size=(B,7)); pairs=np.array([[0,1],[0,3],[2,4],[4,6],[1,5]],np.int32)
    r1=m.pair_corr(X,pairs); r2=np.array([np.corrcoef(X[:,i],X[:,j])[0,1] for i,j in pairs])
    art_error=float(np.max(np.abs(r1-r2)))
    if art_error>1e-12: raise RuntimeError(f"artificial pair correlation mismatch {art_error}")
    # Opposite ALT-allele example with untied continuous ranks: minor-oriented ranks match,
    # while final ALT counts complement exactly under p and 1-p.
    u=np.linspace(-2.0,2.0,B); u_alt=np.column_stack([u,-u]); p=np.array([.2,.8])
    tie=rng.random(B); ranks=np.empty((2,B),np.uint16)
    for j in range(2):
        z=u_alt[:,j] if p[j]<=.5 else -u_alt[:,j]
        key=tie if p[j]<=.5 else -tie
        order=np.lexsort((key,z)); ranks[j,order]=np.arange(1,B+1,dtype=np.uint16)
    g,*_=m.transform(ranks,p,1.0)
    if not np.array_equal(g[0],2-g[1]): raise RuntimeError("opposite-allele count complement failed")
    # Verify the exact installed reader and native helper on a bounded real sketch subset.
    region=pd.read_csv(OUT/"prepared/regions.tsv",sep="\t").query("chromosome == 22").iloc[0]
    v=pd.read_csv(region.metadata_path,sep="\t").iloc[:8]
    scratch=OUT/"scratch"; scratch.mkdir(exist_ok=True)
    idx=scratch/"native_indices.txt"; mat=scratch/"native_ld.tsv"
    np.savetxt(idx,v.pidx.to_numpy(np.int64),fmt="%d")
    cmd=[R,"--vanilla",str(HERE/"native_ld_check.R"),str(m.source_prefix("22")),str(idx),str(mat)]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    native=pd.read_csv(mat,sep="\t",index_col=0).to_numpy()
    x,_,_=m.read_sketch("22",v.pidx.to_numpy(),scratch)
    np_r=np.corrcoef(x,rowvar=False)
    native_error=float(np.max(np.abs(native-np_r)))
    if native_error>1e-10: raise RuntimeError(f"installed compute_LD mismatch {native_error}")
    result={"status":"pass","B":B,"seed":SEED,"artificial_selected_pair_max_abs_error":art_error,
            "opposite_alt_allele_complement":"pass","native_pecotmr_compute_LD_variants":len(v),
            "native_vs_numpy_max_abs_error":native_error,"native_runtime":"py3.11 R 4.3.3 pecotmr 0.3.4 pgenlibr 0.3.2",
            "tutorial_documented_path":"missing at its documented COSI_paper location; generator and installed helper inspected"}
    (OUT/"results/method_audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

def q_alt(p,theta):
    n0,n1,n2,M,clip=m.count_formula(np.asarray([p]),theta)
    q=np.array([n0[0],n1[0],n2[0]],float)/B
    if p>.5: q=q[::-1]
    return q

def coupling_corr(q1,q2,opposite=False):
    # Integrate quantile products exactly over the union of categorical CDF breakpoints.
    if opposite: q2=q2[::-1]
    c1=np.cumsum(q1); c2=np.cumsum(q2)
    breaks=np.unique(np.r_[0.,c1,1.,c2]); breaks=np.clip(breaks,0,1)
    a=0.; eprod=0.
    for lo,hi in zip(breaks[:-1],breaks[1:]):
        if hi<=lo: continue
        u=(lo+hi)/2
        x=int(np.searchsorted(c1,u,side="right")); y=int(np.searchsorted(c2,u,side="right"))
        if opposite: y=2-y
        eprod+=(hi-lo)*x*y
    mean1=float(np.dot(np.arange(3),q1)); mean2=float(np.dot(np.arange(3),q2[::-1] if opposite else q2))
    var1=float(np.dot(np.arange(3)**2,q1)-mean1**2); var2=float(np.dot(np.arange(3)**2,q2[::-1] if opposite else q2)-mean2**2)
    cov=eprod-mean1*mean2
    return cov/math.sqrt(var1*var2) if var1>0 and var2>0 else np.nan

def dense_audit(theta):
    regions=pd.read_csv(OUT/"prepared/regions.tsv",sep="\t")
    chosen=[regions.query("split == 'development'").sort_values("region_id").iloc[0],
            regions.query("split == 'validation' and chromosome == 1").sort_values("region_id").iloc[0]]
    rows=[]
    for rg in chosen:
        meta=pd.read_csv(rg.metadata_path,sep="\t").iloc[:500].copy()
        x,secs,_=m.read_sketch(str(rg.chromosome),meta.pidx.to_numpy(),OUT/"scratch")
        target=np.corrcoef(x,rowvar=False)
        ranks=np.fromfile(rg.rank_cache,dtype=np.uint16).reshape((int(rg.n_variants),B))[:500]
        g,*_=m.transform(ranks,meta.p_freq.to_numpy(float),theta)
        # g is variants × synthetic rows, so rows are variables here.
        recon=np.corrcoef(g.astype(float),rowvar=True)
        iu=np.triu_indices(len(meta),1); a=target[iu]; b=recon[iu]
        rows.append({"region_id":rg.region_id,"split":rg.split,"chromosome":str(rg.chromosome),"variants":len(meta),
             "pairs":len(a),"dense_signed_rmse":float(np.sqrt(np.mean((b-a)**2))),
             "dense_signed_r_correlation":float(np.corrcoef(a,b)[0,1]),"target_mean_abs_r":float(np.mean(np.abs(a))),
             "reconstructed_mean_abs_r":float(np.mean(np.abs(b))),"target_decode_seconds":secs})
        pd.DataFrame({"target_r":a,"synthetic_r":b,"residual":b-a}).to_csv(OUT/f"results/dense_{rg.region_id}_pairs.tsv.gz",sep="\t",index=False,compression="gzip")
    pd.DataFrame(rows).to_csv(OUT/"results/dense_ld_audit.tsv",sep="\t",index=False)
    return rows

def export_roundtrip(theta):
    # Native PLINK 1.9 import and rewrite, plus exact selected calls through --recode A.
    exp=OUT/"pilot"; base=exp/"pilot"; plink=str(m.PLINK)
    out=exp/"plink_native"; log=exp/"plink_native.log"
    cp=subprocess.run([plink,"--bfile",str(base),"--keep-allele-order","--make-bed","--out",str(out)],capture_output=True,text=True)
    log.write_text(cp.stdout+"\n--- STDERR ---\n"+cp.stderr)
    if cp.returncode: raise RuntimeError(cp.stderr[-2000:])
    raw=exp/"plink_selected_calls"; selected=exp/"roundtrip_variant_ids.txt"
    bim=pd.read_csv(str(base)+".bim",sep=r"\s+",header=None,dtype=str)
    sel=bim.iloc[np.linspace(0,len(bim)-1,min(32,len(bim)),dtype=int),1].drop_duplicates()
    selected.write_text("\n".join(sel)+"\n")
    cp=subprocess.run([plink,"--bfile",str(base),"--extract",str(selected),"--recode","A","--out",str(raw)],capture_output=True,text=True)
    if cp.returncode: raise RuntimeError(cp.stderr[-2000:])
    rec=pd.read_csv(str(raw)+".raw",sep=r"\s+",dtype=str)
    expected=[]; checks=[]
    variants=pd.read_csv(OUT/"prepared/regions.tsv",sep="\t")
    theta_by=theta
    # Match each selected BIM variant to its source region and compare every synthetic row.
    for vid in sel:
        found=False
        for _,rg in variants.iterrows():
            vm=pd.read_csv(rg.metadata_path,sep="\t")
            where=np.flatnonzero(vm.ID.astype(str).to_numpy()==str(vid))
            if not len(where): continue
            j=int(where[0]); p=vm.p_freq.to_numpy(float)
            rank=np.fromfile(rg.rank_cache,dtype=np.uint16).reshape((int(rg.n_variants),B))[j:j+1]
            geno,*_=m.transform(rank,p[j:j+1],theta_by)
            # PLINK 1.9 --recode A labels/counts the allele shown in the raw header;
            # resolve that allele against BIM rather than assuming it is A1 or ALT.
            brow=bim.loc[bim[1]==str(vid)]
            if len(brow)!=1: raise RuntimeError(f"BIM has nonunique/missing variant {vid}")
            a1,a2=str(brow.iloc[0,4]),str(brow.iloc[0,5])
            candidates=[c for c in rec.columns[6:] if c.startswith(str(vid)+"_")]
            if len(candidates)!=1: raise RuntimeError(f"cannot identify recoded allele column for {vid}: {candidates}")
            col=candidates[0]; counted=col[len(str(vid))+1:]
            got=pd.to_numeric(rec[col],errors="coerce").to_numpy()
            ref=str(vm.REF.iloc[j]); alt=str(vm.ALT.iloc[j])
            expected=geno[0] if counted==alt else (2-geno[0] if counted==ref else None)
            if expected is None: raise RuntimeError(f"PLINK raw allele {counted} does not match source REF/ALT for {vid}")
            if not np.array_equal(got,expected.astype(float)):
                bad=np.flatnonzero(got!=expected); raise RuntimeError(f"genotype mismatch for {vid}, first row {int(bad[0])}")
            checks.append({"variant_id":str(vid),"rows_checked":B,"exact_call_match":True,"raw_counted_allele":counted,"BIM_A1":a1,"BIM_A2":a2,"ALT_genotype_recovered":True})
            found=True; break
        if not found: raise RuntimeError(f"selected variant absent from source metadata: {vid}")
    b1=pathlib.Path(str(base)+".bed").read_bytes(); b2=pathlib.Path(str(out)+".bed").read_bytes()
    # Byte identity confirms PLINK parsed and rewrote all SNP-major calls, including ordering.
    if b1!=b2: raise RuntimeError("PLINK native BED read/write byte roundtrip differed")
    fam=pd.read_csv(str(base)+".fam",sep=r"\s+",header=None,dtype=str); bim0=pd.read_csv(str(base)+".bim",sep=r"\s+",header=None,dtype=str)
    result={"status":"pass","plink":"1.9","samples":len(fam),"variants":len(bim0),"selected_variants_exactly_checked":len(checks),
        "genotypes_per_selected_variant":B,"allele_counted":"BIM A1 is ALT","native_bed_byte_roundtrip":"identical",
        "selected_call_checks":checks,"source_bed_sha256":hfile(str(base)+".bed"),"rewritten_bed_sha256":hfile(str(out)+".bed"),
        "log":str(log)}
    (exp/"roundtrip_verified.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def postprocess():
    frozen=json.loads((OUT/"frozen_parameters.json").read_text()); theta=float(frozen["theta_star"])
    dev=pd.read_csv(OUT/"results/development_results.tsv",sep="\t"); val=pd.read_csv(OUT/"results/validation_results.tsv",sep="\t")
    dev=dev[(dev.theta==theta)&(dev.status=="ok")].copy()
    if len(dev)!=8 or len(val)!=12: raise RuntimeError("expected complete development and validation result sets")
    vjobs=pd.read_csv(OUT/"prepared/validation_jobs.tsv",sep="\t")
    baseline=[]
    for _,job in vjobs[vjobs.theta==1.0].iterrows():
        z=json.loads(pathlib.Path(job.result_path).read_text()); z["job_id"]=job.job_id; baseline.append(z)
    base=pd.DataFrame(baseline)
    if len(base)!=12 or not (base.status=="ok").all(): raise RuntimeError("prespecified held-out theta=1 baseline is incomplete")
    comp=val.merge(base,on="region_id",suffixes=("_star","_baseline"))
    comp[["region_id","chromosome_star","theta_star","primary_rmse_star","primary_rmse_baseline","unweighted_rmse_star","unweighted_rmse_baseline","signed_ld_correlation_star","signed_ld_correlation_baseline"]].to_csv(OUT/"results/heldout_baseline_comparison.tsv",sep="\t",index=False)
    regions=pd.read_csv(OUT/"prepared/regions.tsv",sep="\t")
    pair_rows=[]; variant_rows=[]; bounds=[]
    for _,rg in regions.iterrows():
        phase=rg.split; use=theta if phase=="development" else theta
        meta=pd.read_csv(rg.metadata_path,sep="\t"); p=meta.p_freq.to_numpy(float); maf=np.minimum(p,1-p)
        ranks=np.fromfile(rg.rank_cache,dtype=np.uint16).reshape((int(rg.n_variants),B))
        g,n0,n1,n2,M,clip=m.transform(ranks,p,use)
        cache=np.load(rg.pair_cache); pairs=cache["pairs"]; target=cache["r"]; bins=cache["ld_bin"]
        rr=m.pair_corr(g.T.astype(float),pairs); pairmaf=cache["maf_pair"]
        cls=np.where(pairmaf<.01,0,np.where(pairmaf<.05,1,2)); typ=np.sort(cls,axis=1)
        for j,(a,b) in enumerate(pairs):
            pair_rows.append({"region_id":rg.region_id,"split":phase,"chromosome":str(rg.chromosome),"target_r":target[j],"synthetic_r":rr[j],
                "i":int(a),"j":int(b),
                "residual":rr[j]-target[j],"target_abs_r_bin":["[0,.1)","[.1,.5)","[.5,1]"][int(bins[j])],
                "maf_pair_type":f"{int(typ[j,0])}-{int(typ[j,1])}","maf_i":pairmaf[j,0],"maf_j":pairmaf[j,1]})
        af=g.mean(axis=1)/2; het=(g==1).mean(axis=1); hwe=2*maf*(1-maf)
        for j,row in meta.iterrows():
            variant_rows.append({"region_id":rg.region_id,"split":phase,"chromosome":str(rg.chromosome),"variant_id":row.ID,
                "pos":row.POS,"is_snp":bool(row.is_snp),"supplied_alt_af":p[j],"synthetic_alt_af":af[j],"alt_af_error":af[j]-p[j],
                "maf":maf[j],"het_observed":het[j],"het_hwe":hwe[j],"relative_hwe_het_error":abs(het[j]-hwe[j])/max(hwe[j],1e-15),
                "n0":int(n0[j]),"n1":int(n1[j]),"n2":int(n2[j]),"finite_count_clipped":bool(clip[j]),"genotype_proportions":str(np.bincount(g[j],minlength=3)/B)})
    pp=pd.DataFrame(pair_rows); vv=pd.DataFrame(variant_rows)
    pp.to_csv(OUT/"results/pair_metrics.tsv.gz",sep="\t",index=False,compression="gzip")
    vv.to_csv(OUT/"results/variant_metrics.tsv.gz",sep="\t",index=False,compression="gzip")
    # Region-level bootstrap; regions, not correlated pairs, are the resampling units.
    rng=np.random.default_rng(SEED); nboot=20000
    d=dev.primary_rmse.to_numpy(); v=val.primary_rmse.to_numpy()
    bd=np.sqrt(np.mean(rng.choice(d,(nboot,len(d)),replace=True)**2,axis=1)); bv=np.sqrt(np.mean(rng.choice(v,(nboot,len(v)),replace=True)**2,axis=1))
    boot={"seed":SEED,"resampling_unit":"region","replicates":nboot,
        "development_weighted_rmse_ci95":[float(x) for x in np.quantile(bd,[.025,.975])],
        "validation_weighted_rmse_ci95":[float(x) for x in np.quantile(bv,[.025,.975])],
        "validation_minus_development_ci95":[float(x) for x in np.quantile(bv-bd,[.025,.975])],
        "ratio_ci95":[float(x) for x in np.quantile(bv/np.maximum(bd,.02),[.025,.975])]}
    (OUT/"results/region_bootstrap.json").write_text(json.dumps(boot,indent=2)+"\n")
    # All six unordered pair classes and target-|r| strata, with explicit support counts.
    strata=pp.groupby(["split","target_abs_r_bin","maf_pair_type"]).agg(n_pairs=("residual","size"),rmse=("residual",lambda x:float(np.sqrt(np.mean(x*x)))),bias=("residual","mean"),n_regions=("region_id","nunique")).reset_index()
    strata.to_csv(OUT/"results/ld_maf_pair_strata.tsv",sep="\t",index=False)
    case=pp.groupby(["split","target_abs_r_bin","maf_pair_type"]).agg(pair_count=("residual","size"),region_count=("region_id","nunique"),mean_target_abs_r=("target_r",lambda x:float(np.mean(np.abs(x))))).reset_index()
    case.to_csv(OUT/"results/heldout_case_mix.tsv",sep="\t",index=False)
    # Pairwise attainable signed-correlation bounds from frozen finite genotype marginals.
    rng=np.random.default_rng(SEED+91)
    for (split,ld,typ),grp in pp.groupby(["split","target_abs_r_bin","maf_pair_type"]):
        if len(grp)==0: continue
        take=grp.iloc[np.sort(rng.choice(len(grp),min(20,len(grp)),replace=False))]
        for _,pr in take.iterrows():
            rg=regions[regions.region_id==pr.region_id].iloc[0]; vm=pd.read_csv(rg.metadata_path,sep="\t")
            pmap=dict(zip(vm.ID.astype(str),vm.p_freq.astype(float)))
            i=int(pr.i); j=int(pr.j); q1=q_alt(float(vm.p_freq.iloc[i]),theta); q2=q_alt(float(vm.p_freq.iloc[j]),theta)
            bounds.append({"split":split,"region_id":pr.region_id,"ld_bin":ld,"maf_pair_type":typ,"target_r":float(pr.target_r),
                "attainable_min_r":coupling_corr(q1,q2,True),"attainable_max_r":coupling_corr(q1,q2,False),"simultaneous_feasibility":"not implied"})
    pd.DataFrame(bounds).to_csv(OUT/"results/pairwise_feasibility_sample.tsv",sep="\t",index=False)
    dense=dense_audit(theta)
    # Pooled held-out vector summaries use each fixed pair once.
    hval=pp[pp.split=="validation"]
    pooled={"signed_r_correlation":float(np.corrcoef(hval.target_r,hval.synthetic_r)[0,1]),
       "signed_rmse":float(np.sqrt(np.mean(hval.residual**2))),"signed_bias":float(hval.residual.mean()),
       "r2_rmse":float(np.sqrt(np.mean((hval.synthetic_r**2-hval.target_r**2)**2))),
       "strong_abs_r_bias":float(np.mean(np.abs(hval.loc[np.abs(hval.target_r)>=.5,"synthetic_r"])-np.abs(hval.loc[np.abs(hval.target_r)>=.5,"target_r"]))),
       "max_alt_af_error":float(vv[vv.split=="validation"].alt_af_error.abs().max()),
       "hwe_95pct_variants":float(np.mean(vv[(vv.split=="validation")&(vv.maf>=.05)].relative_hwe_het_error<=.10)),
       "conversion_rate":float(np.mean(val.conversion_rate)),"pair_count":len(hval)}
    valrmse=float(np.sqrt(np.mean(val.primary_rmse**2))); devrmse=float(np.sqrt(np.mean(dev.primary_rmse**2)))
    basermse=float(np.sqrt(np.mean(base.primary_rmse**2)))
    chromosome=val.groupby("chromosome").apply(lambda x:float(np.sqrt(np.mean(x.primary_rmse**2)))).to_dict()
    eligible=strata[strata.split=="validation"].copy(); covered=eligible[(eligible.n_pairs>=1000)&(eligible.n_regions>=3)]
    gates={"development_weighted_rmse_le_0.10":devrmse<=.10,"heldout_weighted_rmse_le_0.10":valrmse<=.10,
       "heldout_minus_dev_le_0.03":valrmse-devrmse<=.03,"heldout_ratio_le_1.25":valrmse/max(devrmse,.02)<=1.25,
       "heldout_signed_r_corr_ge_0.90":pooled["signed_r_correlation"]>=.90,"heldout_r2_rmse_le_0.10":pooled["r2_rmse"]<=.10,
       "heldout_strong_abs_bias_le_0.10":abs(pooled["strong_abs_r_bias"])<=.10,"alt_frequency_bound":pooled["max_alt_af_error"]<=1/(4*B)+1e-10,
       "hwe_95pct_for_maf_ge_0.05":pooled["hwe_95pct_variants"]>=.95,"all_validation_chrom_rmse_le_0.15":all(x<=.15 for x in chromosome.values()),
       "covered_ld_maf_strata_rmse_le_0.15":bool((covered.rmse<=.15).all()),"coverage_strata_n":len(covered),"conversion_all":bool((val.conversion_rate==1).all())}
    (OUT/"results/acceptance.json").write_text(json.dumps({"theta_star":theta,"development_weighted_rmse":devrmse,
       "heldout_weighted_rmse":valrmse,"heldout_development_difference":valrmse-devrmse,
       "heldout_development_ratio":valrmse/max(devrmse,.02),"heldout_chromosome_weighted_rmse":chromosome,
       "heldout_baseline_theta1_weighted_rmse":basermse,"heldout_baseline_delta_star_minus_baseline":valrmse-basermse,
       "pooled_heldout_metrics":pooled,"adequately_covered_heldout_strata":covered.to_dict(orient="records"),
       "region_bootstrap":boot,"gates":gates,"single_theta_accepted":all(v is True for v in gates.values() if isinstance(v,bool)),
       "interpretation":"support only within sampled regions and adequately covered strata"},indent=2,allow_nan=True)+"\n")
    # Figures with full numeric tables saved above.
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    results=OUT/"results"; grid=pd.read_csv(results/"development_grid.tsv",sep="\t")
    fig,ax=plt.subplots(figsize=(6,4)); ax.plot(grid.theta,grid.primary_loss,"o-"); ax.axvline(theta,color="black",ls="--",label=f"frozen theta={theta:.4f}"); ax.axhline(.10,color="red",ls=":",label="acceptance 0.10"); ax.set(xlabel="Global theta",ylabel="Chr22 weighted LD RMSE"); ax.legend(); fig.tight_layout(); fig.savefig(results/"loss_vs_theta.png",dpi=180); plt.close(fig)
    samp=hval.sample(min(50000,len(hval)),random_state=SEED)
    fig,ax=plt.subplots(figsize=(5,5)); ax.scatter(samp.target_r,samp.synthetic_r,s=2,alpha=.15); ax.plot([-1,1],[-1,1],"k--"); ax.set(xlabel="Target sketch r",ylabel="Synthetic genotype r"); fig.tight_layout(); fig.savefig(results/"heldout_target_vs_synthetic_r.png",dpi=180); plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4));
    ldgroups=list(hval.groupby("target_abs_r_bin")); groups=[g.residual.to_numpy() for _,g in ldgroups]; axs[0].boxplot(groups,labels=[k for k,_ in ldgroups],showfliers=False); axs[0].set(ylabel="Signed-r residual",xlabel="Target |r| bin")
    mafgroups=list(hval.groupby("maf_pair_type")); groups2=[g.residual.to_numpy() for _,g in mafgroups]; axs[1].boxplot(groups2,labels=[k for k,_ in mafgroups],showfliers=False); axs[1].set(ylabel="Signed-r residual",xlabel="MAF pair class"); fig.tight_layout(); fig.savefig(results/"heldout_residual_strata.png",dpi=180); plt.close(fig)
    h=vv[vv.split=="validation"]
    fig,axs=plt.subplots(1,2,figsize=(10,4)); axs[0].hist(h.alt_af_error,bins=40); axs[0].set(xlabel="Synthetic ALT AF - supplied ALT AF",ylabel="Variants"); axs[1].hist(h.loc[h.maf>=.05,"relative_hwe_het_error"],bins=40); axs[1].axvline(.1,color="red",ls=":"); axs[1].set(xlabel="Relative HWE heterozygosity error (MAF ≥ 0.05)",ylabel="Variants"); fig.tight_layout(); fig.savefig(results/"frequency_heterozygosity_qc.png",dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,4)); ax.scatter(val.runtime_s,val.peak_rss_mb,c=val.primary_rmse); ax.set(xlabel="Worker runtime (s)",ylabel="Peak RSS (MB)"); fig.tight_layout(); fig.savefig(results/"runtime_memory.png",dpi=180); plt.close(fig)
    summary={"status":"complete","theta_star":theta,"interpretation":"supported" if all(v is True for v in gates.values() if isinstance(v,bool)) else "unsupported",
       "pilot_export_required":True,"genomewide_export_authorized_by_contract":bool(all(v is True for v in gates.values() if isinstance(v,bool))),
       "dev_weighted_rmse":devrmse,"validation_weighted_rmse":valrmse,"figures":5,"pair_rows":len(pp),"variant_rows":len(vv),"dense_audit":dense,
       "acceptance_path":str(OUT/"results/acceptance.json"),"supporting_code_sha256":hfile(HERE/"supporting_audits.py")}
    (OUT/"results/final_report_data.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))

def main():
    cmd=sys.argv[1]
    if cmd=="method-audit": method_audit()
    elif cmd=="postprocess": postprocess()
    else: raise SystemExit("use method-audit or postprocess")
if __name__=="__main__": main()
