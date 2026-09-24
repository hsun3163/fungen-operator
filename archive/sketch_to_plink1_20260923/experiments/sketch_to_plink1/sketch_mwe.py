#!/usr/bin/env python3
"""Frozen-contract sketch-to-synthetic-genotype experiment harness.

All source PGEN access is through the pinned pecotmr 0.3.4 reader.  Target
correlations and outputs describe 10,000 synthetic projection rows, never people.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, pathlib, platform, subprocess, sys, time, resource
from collections import Counter, defaultdict
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sketch_to_plink1"
CODE = ROOT / "experiments/sketch_to_plink1"
SRC = pathlib.Path("/sc/arion/projects/load/users/sunh14/myloid_paper/Myloid-paper/3_Production/cosi_archive/COSI/hg38/ADSP_reference_panel/ADSP_sketch_reference/EUR/rss_ld_sketch")
R = pathlib.Path("/sc/arion/work/sunh14/conda/envs/py3.11/bin/Rscript")
PY = pathlib.Path("/sc/arion/work/sunh14/conda/envs/py3.11/bin/python")
PLINK = pathlib.Path("/sc/arion/work/sunh14/conda/envs/py3.11/bin/plink")
B = 10000
SEED = 20260923
CHROMS = ["1", "6", "19", "21", "22"]
THETAS = [round(i / 8, 3) for i in range(17)]
MAC_MIN = 20

def sha(path, chunk=8*1024*1024):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            z=f.read(chunk)
            if not z: break
            h.update(z)
    return h.hexdigest()

def stable_seed(*parts):
    raw="|".join(map(str,(SEED,)+parts)).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:4],"big") & 0x7fffffff

def source_prefix(chrom):
    return SRC / f"chr{chrom}" / f"ADSP.R4.EUR.admixture85.chr{chrom}"

def chrom_norm(x):
    s=str(x)
    return s[3:] if s.lower().startswith("chr") else s

def load_metadata(chrom):
    """Join PVAR and AFREQ by normalized position and unordered allele set."""
    p=source_prefix(chrom)
    pv=pd.read_csv(str(p)+".pvar",sep="\t",comment="#",header=None,
                   names=["CHROM","POS","ID","REF","ALT"],dtype=str)
    af=pd.read_csv(str(p)+".afreq",sep="\t",comment="#",header=None,
                   names=["AF_CHROM","AF_ID","AF_REF","AF_ALT","ALT_FREQS","OBS_CT","U_MIN","U_MAX"],dtype=str)
    pv["pidx"]=np.arange(1,len(pv)+1,dtype=np.int64)
    for df,c,pcol,rcol,acol in [(pv,"CHROM","POS","REF","ALT"),(af,"AF_CHROM","AF_POS","AF_REF","AF_ALT")]:
        if df is af:
            m=df["AF_ID"].str.extract(r"^(?:chr)?([^:]+):(\d+):([^:]+):([^:]+)$")
            df["AF_CHROM"]=m[0]; df["AF_POS"]=m[1]
            df["AF_ID_REF"]=m[2]; df["AF_ID_ALT"]=m[3]
    pv["C"]=pv.CHROM.map(chrom_norm); pv["P"]=pd.to_numeric(pv.POS,errors="coerce")
    af["C"]=af.AF_CHROM.map(chrom_norm); af["P"]=pd.to_numeric(af.AF_POS,errors="coerce")
    pv["A0"]=pv[["REF","ALT"]].min(axis=1); pv["A1"]=pv[["REF","ALT"]].max(axis=1)
    af["A0"]=af[["AF_REF","AF_ALT"]].min(axis=1); af["A1"]=af[["AF_REF","AF_ALT"]].max(axis=1)
    pvkey=["C","P","A0","A1"]; afkey=pvkey
    pdup=pv.duplicated(pvkey,keep=False); adup=af.duplicated(afkey,keep=False)
    pv["_pdup"]=pdup; af["_adup"]=adup
    af=af.sort_values("AF_ID",kind="stable").drop_duplicates(afkey,keep="first")
    m=pv.merge(af,on=pvkey,how="left",validate="many_to_one",suffixes=("","_x"))
    m["p_match"]=m.AF_ID.notna()
    m["id_match"]=(m.ID==m.AF_ID) & (m.REF==m.AF_REF) & (m.ALT==m.AF_ALT)
    m["p_multi"]=m.ALT.str.contains(",",regex=False,na=True)
    m["p_freq"]=pd.to_numeric(m.ALT_FREQS,errors="coerce")
    m["p_freq_ok"]=m.p_freq.between(0,1,inclusive="both")
    m["p_mac"]=2*B*np.minimum(m.p_freq,1-m.p_freq)
    m["eligible_meta"]=(~m._pdup)&(~m._adup)&m.p_match&m.id_match&(~m.p_multi)&m.p_freq_ok&(m.p_mac>=MAC_MIN)
    m["is_snp"]=(m.REF.str.len()==1)&(m.ALT.str.len()==1)
    # One metadata row per original PVAR index; invalid/missing joins remain in exclusions.
    excl={"pvar_rows":len(m),"frequency_or_metadata_missing":int((~m.p_match).sum()),
          "id_or_allele_mismatch":int((m.p_match&(~m.id_match)).sum()),
          "ambiguous_duplicate_key":int((m._pdup|m._adup).sum()),
          "multiallelic":int(m.p_multi.sum()),"invalid_frequency":int((~m.p_freq_ok).sum()),
          "below_MAC20":int((m.p_freq_ok&(m.p_mac<MAC_MIN)).sum()),
          "eligible_metadata":int(m.eligible_meta.sum()),"eligible_snps":int((m.eligible_meta&m.is_snp).sum()),
          "eligible_indels":int((m.eligible_meta&(~m.is_snp)).sum())}
    return m,excl

def candidate_rows(df,chrom,ncand):
    e=df.loc[df.eligible_meta].sort_values(["P","pidx"],kind="stable")
    # Fixed-width in eligible-variant rank space; candidate ranges are disjoint.
    width=1000
    if len(e)<width*ncand*2: raise RuntimeError(f"chromosome {chrom} has too few eligible variants")
    starts=np.linspace(0,len(e)-width,ncand,dtype=int)
    # Reserve an explicit metadata-only candidate covering the chr6 MHC when available.
    if chrom=="6":
        mhc=np.flatnonzero((e.P.to_numpy()>=25_000_000)&(e.P.to_numpy()<=34_000_000))
        if len(mhc)>=width: starts[0]=int(mhc[len(mhc)//2]-width//2)
    starts=np.maximum.accumulate(starts)
    starts[-1]=min(starts[-1],len(e)-width)
    out=[]
    for ix,s in enumerate(starts):
        z=e.iloc[s:s+width].copy()
        # Avoid accidental overlap caused by integer spacing.
        if ix and int(z.pidx.min())<=int(out[-1].pidx.max()):
            s=int(np.searchsorted(e.pidx.to_numpy(),int(out[-1].pidx.max())+1))
            z=e.iloc[s:s+width].copy()
        z["region_candidate"]=f"chr{chrom}_cand{ix+1:02d}"
        z["region_start"]=int(z.P.min()); z["region_end"]=int(z.P.max())
        out.append(z)
    return out

def make_pairs(pos, region_id, pilot=False):
    pos=np.asarray(pos,dtype=np.int64); n=len(pos); pairs=[]
    for i in range(n):
        end=int(np.searchsorted(pos,pos[i]+1_000_000,side="right"))
        lo=i+1
        if lo>=end: continue
        cand=np.arange(lo,end,dtype=np.int32)
        near=cand[:16]
        rem=cand[16:]
        take=min(16,len(rem))
        if take:
            rng=np.random.default_rng(stable_seed("pair-sample",region_id,i))
            sampled=np.sort(rng.choice(rem,size=take,replace=False))
            pairs.extend((i,int(j)) for j in near)
            pairs.extend((i,int(j)) for j in sampled)
        else: pairs.extend((i,int(j)) for j in near)
    if not pairs: return np.empty((0,2),np.int32)
    return np.unique(np.asarray(pairs,dtype=np.int32),axis=0)

def read_sketch(chrom, pidx, scratch):
    p=source_prefix(chrom)
    ixfile=scratch/"pgen_indices.txt"; raw=scratch/"pgen_values.bin"
    np.savetxt(ixfile,np.asarray(pidx,dtype=np.int64),fmt="%d")
    cmd=[str(R),"--vanilla",str(CODE/"read_sketch_region.R"),str(p),str(ixfile),str(raw)]
    st=time.time(); cp=subprocess.run(cmd,text=True,capture_output=True)
    if cp.returncode: raise RuntimeError(cp.stderr[-3000:])
    x=np.fromfile(raw,dtype="<f8").reshape((B,len(pidx)),order="F")
    raw.unlink(missing_ok=True); ixfile.unlink(missing_ok=True)
    return x,time.time()-st,cp.stdout.strip()

def pair_corr(x,pairs):
    if not len(pairs): return np.empty(0)
    # Center/scale columns; chunk edges keep temporary arrays bounded.
    mu=x.mean(axis=0); sd=x.std(axis=0,ddof=1)
    z=(x-mu)/sd
    out=np.empty(len(pairs),dtype=np.float64)
    for a in range(0,len(pairs),2048):
        q=pairs[a:a+2048]
        out[a:a+len(q)]=np.einsum("ij,ij->j",z[:,q[:,0]],z[:,q[:,1]],optimize=True)/(B-1)
    return out

def profile_candidates(candidates,chrom,work):
    ans=[]
    for d in candidates:
        z=d.iloc[np.linspace(0,len(d)-1,min(96,len(d)),dtype=int)].copy()
        x,secs,_=read_sketch(chrom,z.pidx.to_numpy(),work)
        # fixed target-pair pilot, on pilot variants only
        pairs=make_pairs(z.P.to_numpy(),str(z.region_candidate.iloc[0])+"_pilot")
        if len(pairs)>2048:
            rng=np.random.default_rng(stable_seed("pilot",z.region_candidate.iloc[0]))
            pairs=pairs[np.sort(rng.choice(len(pairs),2048,replace=False))]
        r=pair_corr(x,pairs)
        ans.append({"candidate":str(z.region_candidate.iloc[0]),"chromosome":chrom,
                    "start":int(d.region_start.iloc[0]),"end":int(d.region_end.iloc[0]),
                    "n_variants":len(d),"rare_fraction":float((d.p_freq<.05).mean()),
                    "mean_abs_r":float(np.nanmean(np.abs(r))) if len(r) else np.nan,
                    "pilot_pairs":len(pairs),"decode_seconds":secs})
    return ans

def select_quadrants(profiles, chrom, nselect):
    g=pd.DataFrame(profiles)
    g["ld_hi"]=g.mean_abs_r>=g.mean_abs_r.median()
    g["rare_hi"]=g.rare_fraction>=g.rare_fraction.median()
    g["quadrant"]=(g.ld_hi.astype(str)+"_LD__"+g.rare_hi.astype(str)+"_rare")
    chosen=[]; notes=[]
    if chrom=="22":
        for q in sorted(g.quadrant.unique()):
            a=g[g.quadrant==q].copy(); a["dist"]=(a.mean_abs_r-a.mean_abs_r.median()).abs()+(a.rare_fraction-a.rare_fraction.median()).abs()
            for _,row in a.sort_values(["dist","candidate"]).head(2).iterrows(): chosen.append(row.candidate)
        # Fill missing quadrants deterministically to exactly eight disjoint regions.
        for cand in g.sort_values(["quadrant","candidate"]).candidate:
            if len(chosen)>=8: break
            if cand not in chosen: chosen.append(cand)
        chosen=chosen[:8]
    else:
        # Three regions/chromosome: one MHC region on chr6, then spread across target regimes.
        if chrom=="6":
            mhc=g[(g.start<=34_000_000)&(g.end>=25_000_000)]
            if len(mhc): chosen.append(str(mhc.iloc[(mhc.end-mhc.start).argmin()].candidate))
            else: notes.append("No candidate overlaps GRCh38 chr6 MHC interval 25-34 Mb")
        for q in sorted(g.quadrant.unique()):
            a=g[g.quadrant==q]
            if len(a) and len(chosen)<nselect:
                cand=str(a.sort_values(["candidate"]).iloc[0].candidate)
                if cand not in chosen: chosen.append(cand)
        for cand in g.candidate:
            if len(chosen)>=nselect: break
            if cand not in chosen: chosen.append(str(cand))
        chosen=chosen[:nselect]
    return chosen,g,notes

def write_npy(path,array): np.save(path,np.asarray(array),allow_pickle=False)

def prepare():
    OUT.mkdir(parents=True,exist_ok=True); work=OUT/"scratch"; work.mkdir(exist_ok=True)
    prep=OUT/"prepared"; prep.mkdir(exist_ok=True)
    runtime={"Rscript":str(R),"python":str(PY),"R_version":"4.3.3","pecotmr":"0.3.4","pgenlibr":"0.3.2",
             "libpaths":["/sc/arion/work/sunh14/conda/envs/py3.11/lib/R/library"],
             "reader":"pecotmr:::open_pgen/read_pgen, meanimpute=FALSE","source_root":str(SRC),"B":B,"seed":SEED}
    manifests=[]; sources=[]; excl_all=[]; profiles_all=[]; selected=[]; t0=time.time()
    for chrom in CHROMS:
        df,excl=load_metadata(chrom); excl_all.append({"chromosome":chrom,**excl})
        src={"chromosome":chrom}
        for ext in ["pgen","pvar","psam","afreq"]:
            f=pathlib.Path(str(source_prefix(chrom))+"."+ext); st=f.stat()
            src[ext]={"path":str(f),"size":st.st_size,"mtime_ns":st.st_mtime_ns,
                      "full_sha256":sha(f) if ext!="pgen" else None}
        sources.append(src)
        nc=24 if chrom=="22" else 4
        cands=candidate_rows(df,chrom,nc)
        prof=profile_candidates(cands,chrom,work); profiles_all.extend(prof)
        chosen,reg_profiles,notes=select_quadrants(prof,chrom,8 if chrom=="22" else 3)
        for d in cands:
            cid=str(d.region_candidate.iloc[0])
            if cid not in chosen: continue
            region_id=f"{chrom}_{cid}"
            rankpath=prep/f"{region_id}.ranks.u16"
            pairpath=prep/f"{region_id}.pairs.npz"
            metapath=prep/f"{region_id}.variants.tsv"
            if rankpath.exists() and pairpath.exists() and metapath.exists():
                # A bookkeeping retry reuses the exact completed caches from the prior preparation.
                region=pd.read_csv(metapath,sep="\t"); pairdata=np.load(pairpath); pairs=pairdata["pairs"]; r=pairdata["r"]
                decode_s=0.0; invalid_source=len(d)-len(region)
                rank_hash=sha(rankpath)
            else:
                region=d.sort_values(["P","pidx"],kind="stable").copy()
                x,decode_s,decode_log=read_sketch(chrom,region.pidx.to_numpy(),work)
                valid=np.isfinite(x).all(axis=0)&(x.min(axis=0)>=-1e-8)&(x.max(axis=0)<=2+1e-8)&(x.std(axis=0)>0)
                # The fixed universe is recorded before any theta comparison.
                invalid_source=int((~valid).sum())
                if not valid.all(): region=region.loc[valid].reset_index(drop=True); x=x[:,valid]
                if not len(region): raise RuntimeError(f"no valid columns in {region_id}")
                pairs=make_pairs(region.P.to_numpy(),region_id); r=pair_corr(x,pairs)
                tie_rng=np.random.default_rng(stable_seed("tie-key")); tie=tie_rng.random(B)
                p=region.p_freq.to_numpy(float); maf=np.minimum(p,1-p)
                ranks=np.empty((len(region),B),dtype=np.uint16)
                for j in range(len(region)):
                    oriented=x[:,j] if p[j]<=.5 else -x[:,j]
                    ordj=np.lexsort((tie if p[j]<=.5 else -tie,oriented))
                    ranks[j,ordj]=np.arange(1,B+1,dtype=np.uint16)
                ranks.tofile(rankpath)
                ldbin=np.digitize(np.abs(r),[.1,.5],right=False).astype(np.uint8)
                weights=np.zeros(len(r),dtype=np.float64); H=max(1,len(np.unique(ldbin)))
                for k in np.unique(ldbin): weights[ldbin==k]=1.0/(H*np.sum(ldbin==k))
                np.savez_compressed(pairpath,pairs=pairs,r=r,ld_bin=ldbin,weights=weights,
                                    maf_pair=np.column_stack([maf[pairs[:,0]],maf[pairs[:,1]]]).astype(np.float32))
                region[["CHROM","POS","ID","REF","ALT","p_freq","pidx","P","is_snp"]].to_csv(metapath,sep="\t",index=False)
                rank_hash=sha(rankpath)
                del x,ranks
            if not len(region): raise RuntimeError(f"no valid columns in {region_id}")
            input_hash=hashlib.sha256((rank_hash+sha(metapath)+sha(pairpath)).encode()).hexdigest()
            profile=next(z for z in prof if z["candidate"]==cid)
            manifests.append({"region_id":region_id,"candidate":cid,"chromosome":chrom,
                "split":"development" if chrom=="22" else "validation","region_start":int(region.P.min()),"region_end":int(region.P.max()),
                "n_variants":len(region),"n_snps":int(region.is_snp.sum()),"n_indels":int((~region.is_snp).sum()),"n_invalid_source":invalid_source,
                "rare_fraction":float((region.p_freq<.05).mean()),"pilot_mean_abs_r":profile["mean_abs_r"],"quadrant":str(reg_profiles.loc[reg_profiles.candidate==cid,"quadrant"].iloc[0]),
                "rank_cache":str(rankpath),"pair_cache":str(pairpath),"metadata_path":str(metapath),
                "B":B,"seed":SEED,"input_hash":input_hash,"rank_cache_sha256":rank_hash,
                "decode_seconds":decode_s,"pair_count":len(pairs),"pair_mean_abs_r":float(np.mean(np.abs(r))),"notes":"; ".join(notes)})
            print(f"PREP {region_id}: variants={len(region)} pairs={len(pairs)} decode_s={decode_s:.1f} rank_s/cache_mb={rankpath.stat().st_size/1e6:.1f}",flush=True)
            del r
    # stable chromosome row order verification without retaining identifiers in output
    row_hashes={}
    for chrom in CHROMS:
        ps=pathlib.Path(str(source_prefix(chrom))+".psam")
        ids=pd.read_csv(ps,sep="\t",comment="#",header=None,dtype=str).iloc[:,1].astype(str).tolist()
        if len(ids)!=B: raise RuntimeError(f"PSAM row count mismatch on chr{chrom}")
        row_hashes[chrom]=hashlib.sha256("\n".join(ids).encode()).hexdigest()
    if len(set(row_hashes.values()))!=1: raise RuntimeError("projection row order differs between chromosomes")
    sample_audit={"psam_row_count":B,"cross_chrom_order":"identical PSAM IID-order hashes across all five experiment chromosomes",
                  "row_order_sha256":next(iter(row_hashes.values())),
                  "row_ids_not_exported":True}
    pd.DataFrame(excl_all).to_csv(prep/"metadata_exclusion_census.tsv",sep="\t",index=False)
    pd.DataFrame(profiles_all).to_csv(prep/"candidate_target_profiles.tsv",sep="\t",index=False)
    pd.DataFrame(manifests).to_csv(prep/"regions.tsv",sep="\t",index=False)
    (prep/"runtime.json").write_text(json.dumps(runtime,indent=2)+"\n")
    (prep/"sources.json").write_text(json.dumps(sources,indent=2)+"\n")
    (prep/"sample_order_audit.json").write_text(json.dumps(sample_audit,indent=2)+"\n")
    (prep/"prepare_summary.json").write_text(json.dumps({"status":"prepared","elapsed_seconds":time.time()-t0,"regions":len(manifests),"profiles":len(profiles_all),"regions_table":str(prep/"regions.tsv")},indent=2)+"\n")

def count_formula(p,theta):
    m=np.minimum(p,1-p); M=np.floor(2*B*m+.5).astype(np.int32)
    raw=np.floor(B*theta*m*m+.5).astype(np.int32)
    n2=np.clip(raw,np.maximum(0,M-B),M//2)
    n1=M-2*n2; n0=B-n1-n2
    return n0,n1,n2,M,(raw!=n2)

def transform(ranks,p,theta):
    n0,n1,n2,M,clip=count_formula(p,theta)
    g=(ranks>n0[:,None]).astype(np.uint8)+(ranks>(n0+n1)[:,None]).astype(np.uint8)
    flip=p>.5
    if flip.any(): g[flip]=2-g[flip]
    return g,n0,n1,n2,M,clip

def metrics(g,p,pairs,target,ldbin,maf_pair,theta,clip):
    af=g.mean(axis=1)/2; maf=np.minimum(af,1-af); m=np.minimum(p,1-p)
    r=pair_corr(g.T.astype(np.float64),pairs)
    err=r-target; r2=g[np.newaxis,:] if False else r*r; t2=target*target
    def corr(a,b):
        return float(np.corrcoef(a,b)[0,1]) if len(a)>1 and np.std(a)>0 and np.std(b)>0 else np.nan
    bybin=[]
    for k,label in enumerate(["0-.1",".1-.5",".5-1"]):
        mask=ldbin==k
        if mask.any(): bybin.append({"bin":label,"n_pairs":int(mask.sum()),"rmse":float(np.sqrt(np.mean(err[mask]**2))),"bias":float(np.mean(err[mask]))})
    pair_maf_class=np.where(maf_pair<.01,0,np.where(maf_pair<.05,1,2))
    strat=[]
    for a in range(3):
        for b in range(a,3):
            mask=((pair_maf_class[:,0]==a)&(pair_maf_class[:,1]==b))|((pair_maf_class[:,0]==b)&(pair_maf_class[:,1]==a))
            if mask.any(): strat.append({"maf_pair_type":f"{a}-{b}","n_pairs":int(mask.sum()),"rmse":float(np.sqrt(np.mean(err[mask]**2)))})
    nonempty=[np.mean(err[ldbin==k]**2) for k in range(3) if np.any(ldbin==k)]
    q=np.column_stack([np.mean(g==0,axis=1),np.mean(g==1,axis=1),np.mean(g==2,axis=1)])
    qexp=np.column_stack([1-2*m+theta*m*m,2*m-2*theta*m*m,theta*m*m])
    het_hwe=2*m*(1-m); het=q[:,1]
    rel=np.abs(het-het_hwe)/np.maximum(het_hwe,1e-15)
    strong=np.abs(target)>=.5
    return {"primary_rmse":float(np.sqrt(np.mean(nonempty))),"unweighted_rmse":float(np.sqrt(np.mean(err**2))),
        "signed_ld_correlation":corr(r,target),"signed_bias":float(np.mean(err)),"r2_rmse":float(np.sqrt(np.mean((r2-t2)**2))),
        "r2_correlation":corr(r2,t2),"strong_abs_r_bias":float(np.mean(np.abs(r[strong])-np.abs(target[strong]))) if strong.any() else np.nan,
        "alt_af_mae":float(np.mean(np.abs(af-p))),"maf_mae":float(np.mean(np.abs(maf-m))),"max_af_error":float(np.max(np.abs(af-p))),
        "conversion_rate":float(np.mean(g.max(axis=1)>g.min(axis=1))),"genotype_frequency_error":float(np.mean(np.abs(q-qexp))),
        "heterozygosity_error":float(np.mean(het-het_hwe)),"hwe_rel_het_with_maf05_pct":float(np.mean(rel[m>=.05]<=.10)) if np.any(m>=.05) else np.nan,
        "mean_finite_count_clipped":float(np.mean(clip)),"pairs":len(pairs),"pair_ld_strata":bybin,"pair_maf_strata":strat,
        "genotype_proportions_mean":q.mean(axis=0).tolist(),"variant_het_hwe_rel_error_median":float(np.median(rel[m>=.05])) if np.any(m>=.05) else np.nan,
        "pair_correlations":r}

def worker(job_index=None,manifest=None):
    prep=OUT/"prepared"; jobs=pd.read_csv(manifest or prep/"jobs.tsv",sep="\t",dtype={"theta":float})
    ix=job_index if job_index is not None else int(os.environ["LSB_JOBINDEX"])
    row=jobs.iloc[ix-1]
    # Resume identity includes the run-time executable and current code digest.
    code_hash=sha(CODE/"sketch_mwe.py")
    result=OUT/"results"/f"{row.job_id}.json"; result.parent.mkdir(parents=True,exist_ok=True)
    start=time.time(); status="ok"; reason=""
    try:
        meta=pd.read_csv(row.metadata_path,sep="\t"); p=meta.p_freq.to_numpy(float)
        ranks=np.fromfile(row.rank_cache,dtype=np.uint16).reshape((len(p),B))
        cache=np.load(row.pair_cache); pairs=cache["pairs"]; target=cache["r"]; bins=cache["ld_bin"]; maf_pair=cache["maf_pair"]
        g,n0,n1,n2,M,clip=transform(ranks,p,float(row.theta))
        conv=g.max(axis=1)>g.min(axis=1)
        if not conv.all(): status="invalid_candidate"; reason=f"candidate-induced constant columns={int((~conv).sum())}"
        z=metrics(g,p,pairs,target,bins,maf_pair,float(row.theta),clip)
        z.pop("pair_correlations")
        result_obj={"phase":row.phase,"split":row.split,"region_id":row.region_id,"chromosome":str(row.chromosome),"theta":float(row.theta),"B":B,
           "number_of_snps":int(row.n_variants),"number_of_pairs":len(pairs),"status":status,"error_reason":reason,
            "input_hash":row.input_hash,"code_hash":code_hash,"seed":int(row.seed),"runtime_s":time.time()-start,
            "assignment_signature":hashlib.sha256(g.tobytes(order="C")).hexdigest(),
           "peak_rss_mb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,**z}
        # Keep required top-level fields and full QC companion fields in atomic JSON.
        tmp=result.with_suffix(".json.tmp"); tmp.write_text(json.dumps(result_obj,allow_nan=True)); os.replace(tmp,result)
        if status=="ok":
            pd.DataFrame([{**{k:v for k,v in result_obj.items() if not isinstance(v,(list,dict))},"ld_bin_details":json.dumps(z["pair_ld_strata"]),"maf_pair_details":json.dumps(z["pair_maf_strata"])}]).to_csv(OUT/"results"/f"{row.job_id}.tsv",sep="\t",index=False)
    except Exception as e:
        tmp=result.with_suffix(".json.tmp"); tmp.write_text(json.dumps({"status":"execution_error","error_reason":repr(e),"input_hash":row.input_hash,"code_hash":code_hash,"job_id":row.job_id})); os.replace(tmp,result)
        raise

def make_jobs():
    prep=OUT/"prepared"; regions=pd.read_csv(prep/"regions.tsv",sep="\t")
    rows=[]
    for _,r in regions.iterrows():
        theta_list=THETAS if r.split=="development" else []
        for theta in theta_list:
            jid=f"{r.region_id}_t{theta:.3f}"
            rows.append({"job_id":jid,"phase":"coarse_grid" if r.split=="development" else "validation_baseline","split":r.split,
                "region_id":r.region_id,"chromosome":r.chromosome,"theta":theta,"sketch_prefix":str(source_prefix(r.chromosome)),
                "metadata_path":r.metadata_path,"rank_cache":r.rank_cache,"pair_cache":r.pair_cache,"B":B,"seed":SEED,
                "input_hash":r.input_hash,"code_hash":sha(CODE/"sketch_mwe.py"),"result_path":str(OUT/"results"/(jid+".json")),"n_variants":r.n_variants})
    cols=["job_id","phase","split","region_id","chromosome","theta","sketch_prefix","metadata_path","rank_cache","pair_cache","B","seed","input_hash","code_hash","result_path","n_variants"]
    pd.DataFrame(rows,columns=cols).to_csv(prep/"jobs.tsv",sep="\t",index=False)

def reduce():
    prep=OUT/"prepared"; alljobs=pd.read_csv(prep/"jobs.tsv",sep="\t")
    jobs=alljobs[alljobs.split=="development"].copy()
    def collect(jobs):
        results=[]; missing=[]
        for _,j in jobs.iterrows():
            p=pathlib.Path(j.result_path)
            if not p.exists(): missing.append(j.job_id); continue
            z=json.loads(p.read_text())
            if z.get("input_hash")!=j.input_hash or z.get("code_hash")!=sha(CODE/"sketch_mwe.py") or z.get("seed")!=SEED:
                raise RuntimeError(f"identity mismatch in {j.job_id}")
            z["job_id"]=j.job_id; results.append(z)
        if missing: raise RuntimeError(f"incomplete expected development grid: {len(missing)} missing; first={missing[:10]}")
        return pd.DataFrame(results)
    res=collect(jobs)
    regions=pd.read_csv(prep/"regions.tsv",sep="\t"); ndev=int((regions.split=="development").sum())
    def grid_table(res):
        rows=[]
        for theta,g in res.groupby("theta"):
            good=g[g.status=="ok"]; valid=(len(g)==ndev and len(good)==ndev)
            rows.append({"theta":float(theta),"primary_loss":float(np.sqrt(np.mean(good.primary_rmse**2))) if valid else np.nan,
                "mean_region_rmse":float(good.primary_rmse.mean()) if len(good) else np.nan,"n_regions":len(g),"successful_regions":len(good),
                "globally_valid":valid,"invalid_regions":";".join(g.loc[g.status!="ok","region_id"].astype(str)),
                "distinct_assignment_signatures":good.assignment_signature.nunique()})
        return pd.DataFrame(rows).sort_values("theta")
    tab=grid_table(res); tab.to_csv(OUT/"results/development_grid.tsv",sep="\t",index=False)
    if not all(np.any(np.isclose(res.theta,t)) for t in THETAS): raise RuntimeError("the complete 17-point coarse grid has not run")
    validtab=tab[tab.globally_valid]
    if validtab.empty: raise RuntimeError("every theta is invalid on at least one fixed development region")
    plan=OUT/"results/refinement_plan.json"
    if not plan.exists():
        coarse_best=float(validtab.sort_values(["primary_loss","theta"]).iloc[0].theta)
        baseline=float(validtab.loc[np.isclose(validtab.theta,1.0),"primary_loss"].iloc[0])
        new=[]
        if not np.isclose(coarse_best,1.0):
            lo=max(0.0,coarse_best-.125); hi=min(2.0,coarse_best+.125)
            new=[float(v) for v in np.linspace(lo,hi,10)[1:-1] if not np.any(np.isclose(tab.theta,v))][:8]
        if new:
            extra=[]
            for _,rg in regions[regions.split=="development"].iterrows():
                for th in new:
                    jid=f"{rg.region_id}_t{th:.6f}"
                    extra.append({"job_id":jid,"phase":"development_refinement","split":"development","region_id":rg.region_id,
                        "chromosome":rg.chromosome,"theta":th,"sketch_prefix":str(source_prefix(rg.chromosome)),"metadata_path":rg.metadata_path,
                        "rank_cache":rg.rank_cache,"pair_cache":rg.pair_cache,"B":B,"seed":SEED,"input_hash":rg.input_hash,
                        "code_hash":sha(CODE/"sketch_mwe.py"),"result_path":str(OUT/"results"/(jid+".json")),"n_variants":rg.n_variants})
            pd.concat([alljobs,pd.DataFrame(extra,columns=alljobs.columns)],ignore_index=True).to_csv(prep/"jobs.tsv",sep="\t",index=False)
            plan.write_text(json.dumps({"status":"refinement_jobs_appended","coarse_winner":coarse_best,"baseline_loss":baseline,
                "theta_values":new,"reason":"non-baseline coarse minimum; eight points within adjacent coarse intervals"},indent=2)+"\n")
            print(json.dumps({"status":"refinement_jobs_ready","theta_values":new,"jobs":len(extra)})); return
        plan.write_text(json.dumps({"status":"no_refinement","coarse_winner":coarse_best,"baseline_loss":baseline,
            "theta_values":[],"reason":"theta=1 is the coarse minimum; no additional tuning knob was warranted"},indent=2)+"\n")
    # A refinement plan with theta values requires all appended jobs before freezing.
    refinement=json.loads(plan.read_text());
    if refinement["theta_values"]:
        res=collect(pd.read_csv(prep/"jobs.tsv",sep="\t").query("split == 'development'"))
        tab=grid_table(res); tab.to_csv(OUT/"results/development_grid.tsv",sep="\t",index=False)
        validtab=tab[tab.globally_valid]
    minloss=float(validtab.primary_loss.min()); ties=validtab[np.abs(validtab.primary_loss-minloss)<=1e-6].copy(); ties["dist1"]=(ties.theta-1).abs()
    best=float(ties.sort_values(["dist1","theta"]).iloc[0].theta)
    res.to_csv(OUT/"results/development_results.tsv",sep="\t",index=False)
    # Freeze before materializing/submitting any validation outcome job.
    frozen={"status":"frozen_before_validation_review","theta_star":best,"baseline_theta":1.0,"B":B,"seed":SEED,
      "formula_version":"global_homozygosity_multiplier_rank_quantile_v1","objective":"equal region weight; equal nonempty target-|r| bins; fixed target pairs",
      "selected_development_loss":float(tab.loc[tab.theta==best,"primary_loss"].iloc[0]),"baseline_development_loss":float(tab.loc[tab.theta==1,"primary_loss"].iloc[0]),
      "refinement":refinement,
      "region_pair_definitions":"frozen in prepared/regions.tsv and per-region .pairs.npz",
      "acceptance_contract":"docs/sketch_genotype_mwe_luna_prompt.md initial thresholds, recorded pre-validation",
      "runtime":json.loads((prep/"runtime.json").read_text()),"sources":json.loads((prep/"sources.json").read_text()),
      "grid_complete":True,"grid_values":sorted([float(x) for x in tab.theta]),"code_sha256":sha(CODE/"sketch_mwe.py"),"regions_sha256":sha(prep/"regions.tsv"),
      "input_hashes":{r.region_id:r.input_hash for _,r in pd.read_csv(prep/"regions.tsv",sep="\t").iterrows()},
      "selection_objective_loss_table":tab.to_dict(orient="records"),"tie_rule":"within 1E-6, theta closest to 1 then smaller theta"}
    (OUT/"frozen_parameters.json").write_text(json.dumps(frozen,indent=2,allow_nan=True)+"\n")
    # Only now append held-out jobs at theta* and the fixed baseline.
    regions=pd.read_csv(prep/"regions.tsv",sep="\t"); rows=[]
    for _,r in regions[regions.split=="validation"].iterrows():
        for theta in sorted(set([best,1.0])):
            jid=f"{r.region_id}_t{theta:.3f}"
            rows.append({"job_id":jid,"phase":"frozen_validation","split":"validation","region_id":r.region_id,
                "chromosome":r.chromosome,"theta":theta,"sketch_prefix":str(source_prefix(r.chromosome)),"metadata_path":r.metadata_path,
                "rank_cache":r.rank_cache,"pair_cache":r.pair_cache,"B":B,"seed":SEED,"input_hash":r.input_hash,
                "code_hash":sha(CODE/"sketch_mwe.py"),"result_path":str(OUT/"results"/(jid+".json")),"n_variants":r.n_variants})
    pd.DataFrame(rows,columns=jobs.columns).to_csv(prep/"validation_jobs.tsv",sep="\t",index=False)
    pd.concat([jobs,pd.DataFrame(rows,columns=jobs.columns)],ignore_index=True).to_csv(prep/"jobs.tsv",sep="\t",index=False)
    print(json.dumps({"status":"frozen_validation_jobs_ready","theta_star":best,"dev_loss":float(tab.loc[tab.theta==best,"primary_loss"].iloc[0]),"validation_jobs":len(rows)},indent=2))

def finalize():
    prep=OUT/"prepared"; jobs=pd.read_csv(prep/"validation_jobs.tsv",sep="\t"); results=[]; missing=[]
    for _,j in jobs.iterrows():
        p=pathlib.Path(j.result_path)
        if not p.exists(): missing.append(j.job_id); continue
        z=json.loads(p.read_text())
        if z.get("input_hash")!=j.input_hash or z.get("code_hash")!=sha(CODE/"sketch_mwe.py") or z.get("seed")!=SEED: raise RuntimeError(f"identity mismatch {j.job_id}")
        if z.get("status")!="ok": raise RuntimeError(f"invalid/incomplete validation: {j.job_id}: {z.get('error_reason')}")
        results.append(z)
    if missing: raise RuntimeError(f"incomplete validation: {len(missing)} missing")
    val=pd.DataFrame(results); dev=pd.read_csv(OUT/"results/development_results.tsv",sep="\t")
    theta=float(json.loads((OUT/"frozen_parameters.json").read_text())["theta_star"])
    val=val[val.theta==theta]
    aggregate={"development":{"n_regions":len(dev[(dev.split=="development")&(dev.theta==theta)]),"theta":theta,
            "weighted_rmse":float(np.sqrt(np.mean(dev[(dev.split=="development")&(dev.theta==theta)].primary_rmse**2))),
            "unweighted_rmse_mean":float(dev[(dev.split=="development")&(dev.theta==theta)].unweighted_rmse.mean())},
        "validation_at_theta_star":{"n_regions":len(val),"theta":theta,"weighted_rmse":float(np.sqrt(np.mean(val.primary_rmse**2)),),
            "unweighted_rmse_mean":float(val.unweighted_rmse.mean()),"signed_r_corr_mean":float(val.signed_ld_correlation.mean()),
            "r2_rmse_mean":float(val.r2_rmse.mean()),"max_af_error":float(val.max_af_error.max()),
            "chromosome_weighted_rmse":val.groupby("chromosome").apply(lambda x:float(np.sqrt(np.mean(x.primary_rmse**2)))).to_dict()}}
    (OUT/"results/aggregate.json").write_text(json.dumps(aggregate,indent=2,allow_nan=True)+"\n")
    val.to_csv(OUT/"results/validation_results.tsv",sep="\t",index=False)
    print(json.dumps(aggregate,indent=2,allow_nan=True))

def make_export(theta=None):
    prep=OUT/"prepared"; regions=pd.read_csv(prep/"regions.tsv",sep="\t")
    if theta is None: theta=json.loads((OUT/"frozen_parameters.json").read_text())["theta_star"]
    exp=OUT/"pilot"; exp.mkdir(parents=True,exist_ok=True)
    fam=exp/"pilot.fam"
    with open(fam,"w") as f:
        for i in range(1,B+1): f.write(f"SYN_EUR_{i:06d} SYN_EUR_{i:06d} 0 0 0 -9\n")
    bim=exp/"pilot.bim"; allelemap=exp/"pilot_allele_map.tsv"; bed=exp/"pilot.bed"
    with open(bed,"wb") as bf, open(bim,"w") as bmf, open(allelemap,"w") as amf:
        bf.write(bytes([0x6c,0x1b,0x01])); amf.write("CHR\tPOS\tID\tREF\tALT\tCOUNTED_A1\tTHETA\tSPLIT\n")
        for _,rg in regions.iterrows():
            if rg.split not in ("development","validation"): continue
            meta=pd.read_csv(rg.metadata_path,sep="\t"); p=meta.p_freq.to_numpy(float)
            ranks=np.fromfile(rg.rank_cache,dtype=np.uint16).reshape((len(p),B))
            g,n0,n1,n2,M,clip=transform(ranks,p,float(theta))
            for j,row in meta.iterrows():
                chrom=chrom_norm(row.CHROM); pos=int(row.POS); vid=str(row.ID); ref=str(row.REF); alt=str(row.ALT)
                # BIM A1 is ALT. PLINK1 SNP-major BED codes: 00 A1/A1, 10 A1/A2, 11 A2/A2, 01 missing.
                bmf.write(f"{chrom}\t{vid}\t0\t{pos}\t{alt}\t{ref}\n")
                amf.write(f"{chrom}\t{pos}\t{vid}\t{ref}\t{alt}\t{alt}\t{theta:.6f}\t{rg.split}\n")
                for s in range(0,B,4):
                    byte=0
                    for k in range(4):
                        if s+k>=B: code=1
                        else: code=[3,2,0][int(g[j,s+k])]
                        byte|=(code<<(2*k))
                    bf.write(bytes([byte]))
    (exp/"export.json").write_text(json.dumps({"theta":theta,"B":B,"regions":len(regions),"variants":int(regions.n_variants.sum()),"bed_bytes":bed.stat().st_size,"expected_bed_bytes":3+int(regions.n_variants.sum())*math.ceil(B/4),"bed_sha256":sha(bed),"bim_sha256":sha(bim),"fam_sha256":sha(fam)},indent=2)+"\n")

def roundtrip():
    exp=OUT/"pilot"; base=exp/"pilot"; log=exp/"plink_roundtrip.log"
    cmd=[str(PLINK),"--bfile",str(base),"--freq","--missing","--recode","A","--out",str(exp/"roundtrip")]
    cp=subprocess.run(cmd,text=True,capture_output=True)
    log.write_text(cp.stdout+"\n--- STDERR ---\n"+cp.stderr)
    if cp.returncode: raise RuntimeError(f"PLINK round-trip failed: {cp.stderr[-1000:]}")
    # A independent PLINK reader must reproduce exact sample and variant order/count.
    fam=pd.read_csv(str(base)+".fam",sep=r"\s+",header=None)
    bim=pd.read_csv(str(base)+".bim",sep=r"\s+",header=None)
    raw=pd.read_csv(str(exp/"roundtrip.raw"),sep=r"\s+",dtype=str)
    if len(fam)!=B or len(bim)!=len(raw) or raw.shape[0]!=B: raise RuntimeError("PLINK roundtrip dimension mismatch")
    if (exp/"pilot.bed").stat().st_size != 3+len(bim)*math.ceil(B/4): raise RuntimeError("BED byte count mismatch")
    (exp/"roundtrip_verified.json").write_text(json.dumps({"status":"reader_pass","samples":len(fam),"variants":len(bim),"raw_dimensions":[int(raw.shape[0]),int(raw.shape[1])],"plink":"1.9","log":str(log)},indent=2)+"\n")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("command",choices=["prepare","jobs","worker","reduce","finalize","export","roundtrip"]); ap.add_argument("--index",type=int); ap.add_argument("--manifest")
    a=ap.parse_args()
    {"prepare":prepare,"jobs":make_jobs,"worker":lambda:worker(a.index,a.manifest),"reduce":reduce,"finalize":finalize,"export":make_export,"roundtrip":roundtrip}[a.command]()
if __name__=="__main__": main()
