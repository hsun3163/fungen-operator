"""Frozen de novo RNA fixture: 500 people, four regions, six artificial contexts.

Acceptance v1 is declared before fitting: all 24 causal pairs must have nominal
P < 5E-8, the counted-G direction, and causal membership in a 95% SuSiE CS;
at most one of 24 null traits may cross 5E-8. No seed/trait selection by results.
"""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess

SEED=20261020
RECOVERY={'nominal_p':5E-8,'credible_set_coverage':0.95,'planted_required':24,'null_max':1,
          'genetic_variance':0.35,'covariate_variance':0.10,'residual_variance':0.55}


def rng_for(name):
    import numpy as np
    return np.random.default_rng([SEED,int.from_bytes(hashlib.sha256(name.encode()).digest()[:4],'little')])


def generate(root):
    import numpy as np
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    metadata={'revision':1,'seed':SEED,'samples':500,'regions':4,'variants_per_region':128,
              'contexts':6,'traits_per_context':8,'recovery':RECOVERY,'provenance':'de novo simulated diploid haplotypes; no individual-derived input'}
    sentinel=root/'fixture.json'
    if sentinel.exists():
        if json.loads(sentinel.read_text())!=metadata:
            raise ValueError('Fixture contract changed. Choose a new output folder.')
        return
    ids=[f'SYN{i:04}' for i in range(1,501)]
    geno=[];variants=[];causal=[];coords=[]
    for region in range(4):
        rng=rng_for(f'genotype:{region}')
        # Two diploid haplotypes, mild regional LD and no perfect proxies.
        for snp in range(128):
            if snp % 8 == 0:
                block=rng.binomial(1,0.3,(500,2))
            calls=np.where(rng.random((500,2))<0.45,block,rng.binomial(1,0.3,(500,2))).sum(1)
            chrom=1+region//2;position=2_000_000+(region%2)*4_000_000+snp*100
            variant=f'{chrom}:{position}:A:G'
            geno.append(calls);variants.append((chrom,variant,position));
        causal.append(region*128+32);coords.append((1+region//2,2_003_200+(region%2)*4_000_000))
    geno=np.asarray(geno,dtype='uint8')
    with (root/'synthetic.bed').open('wb') as f:
        f.write(b'\x6c\x1b\x01')
        # PLINK1 00=A1/A1, 10=heterozygous, 11=A2/A2; A1=G is counted.
        codes=np.array([3,2,0],dtype='uint8')[geno]
        packed=codes[:,0::4] | (codes[:,1::4]<<2) | (codes[:,2::4]<<4) | (codes[:,3::4]<<6)
        f.write(packed.tobytes())
    (root/'synthetic.bim').write_text(''.join(f'{c}\t{v}\t0\t{p}\tG\tA\n' for c,v,p in variants))
    (root/'synthetic.fam').write_text(''.join(f'{s}\t{s}\t0\t0\t0\t-9\n' for s in ids))
    rng=rng_for('metadata');age=rng.normal(0,1,500);sex=rng.binomial(1,.5,500)
    cov=np.vstack([age,sex])
    with gzip.open(root/'fixed.cov.gz','wt') as f:
        f.write('#id\t'+'\t'.join(ids)+'\n')
        for name,values in zip(['age','sex'],cov):
            f.write(name+'\t'+'\t'.join(f'{x:.10g}' for x in values)+'\n')
    truth=['context\ttrait\tvariant\tcounted_allele\tdirection\tplanted\tchrom\tposition']
    for context in range(1,7):
        name=f'RNA{context}'
        rng=rng_for(name)
        rows=[]
        for region,(chrom,position) in enumerate(coords):
            for planted in (True,False):
                trait=f'synthetic_r{region+1}_'+('causal' if planted else 'null')
                effect=1 if (region+context)%2 else -1
                g=geno[causal[region]].astype(float);g=(g-g.mean())/g.std()
                c=age+.5*(sex-sex.mean());c=(c-c.mean())/c.std()
                noise=rng.normal(size=500)
                y=np.sqrt(.1)*c+np.sqrt(.55 if planted else .9)*noise
                if planted: y+=effect*np.sqrt(.35)*g
                rows.append((chrom,position-1,position,trait,y))
                truth.append(f'{name}\t{trait}\t{variants[causal[region]][1]}\tG\t{effect if planted else 0}\t{int(planted)}\t{chrom}\t{position}')
        path=root/f'{name}.bed'
        with path.open('w') as f:
            f.write('#chr\tstart\tend\tID\t'+'\t'.join(ids)+'\n')
            for chrom,start,end,trait,y in sorted(rows,key=lambda x:(x[0],x[1],x[3])):
                f.write(f'chr{chrom}\t{start}\t{end}\t{trait}\t'+'\t'.join(f'{x:.10g}' for x in y)+'\n')
        subprocess.run(['bgzip','-f',str(path)],check=True)
        subprocess.run(['tabix','-f','-p','bed',str(path)+'.gz'],check=True)
    (root/'truth.tsv').write_text('\n'.join(truth)+'\n')
    sentinel.write_text(json.dumps(metadata,indent=2)+'\n')


def grade(root,work):
    import pandas as pd
    root,work=Path(root),Path(work)
    truth=pd.read_csv(root/'truth.tsv',sep='\t')
    rows=[];null_hits=0
    for context,group in truth.groupby('context'):
        tables=list((work/'association_scan'/context/'TensorQTL').glob('*.cis_qtl.pairs.tsv.gz'))
        if not tables: raise ValueError(f'Missing nominal products for {context}')
        df=pd.concat([pd.read_csv(p,sep='\t') for p in tables],ignore_index=True)
        trait_col=next(c for c in ['phenotype_id','molecular_trait_id','molecular_trait_object_id','ID'] if c in df)
        slope=next(c for c in ['slope','beta','bhat'] if c in df)
        pcol=next(c for c in ['pval_nominal','pvalue','p_nominal'] if c in df)
        for t in group.itertuples():
            matches=df[(df[trait_col]==t.trait)&(df['variant_id']==t.variant)]
            if len(matches)!=1: raise ValueError(f'Missing/duplicate causal pair {context}/{t.trait}')
            r=matches.iloc[0]
            direction=(float(r[slope])>0)-(float(r[slope])<0)
            if not t.planted:
                null_hits+=int((df.loc[df[trait_col]==t.trait,pcol]<RECOVERY['nominal_p']).any())
            rows.append({'context':context,'trait':t.trait,'planted':int(t.planted),
                         'nominal_pass':float(r[pcol])<RECOVERY['nominal_p'],
                         'direction_pass':direction==t.direction})
    output=work.parent/'recovery.tsv'
    pd.DataFrame(rows).to_csv(output,sep='\t',index=False)
    positive=[r for r in rows if r['planted']]
    association=all(r['nominal_pass'] and r['direction_pass'] for r in positive) and null_hits<=RECOVERY['null_max']
    # Native SuSiE objects are graded by the retained R reader, not by a done marker.
    reader=Path(__file__).with_name('resources')/'grade_susie.R'
    subprocess.run(['Rscript',str(reader),str(root/'truth.tsv'),str(work),str(work.parent/'credible_sets.tsv')],check=True)
    cs=pd.read_csv(work.parent/'credible_sets.tsv',sep='\t')
    complete=len(cs)==24 and cs['causal_in_95cs'].all()
    result={'passed':bool(association and complete),'planted_total':24,
            'nominal_direction_recovered':sum(r['nominal_pass'] and r['direction_pass'] for r in positive),
            'credible_set_recovered':int(cs['causal_in_95cs'].sum()),'null_calls':null_hits,'criterion':RECOVERY}
    (work.parent/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['passed']: raise ValueError('Planted recovery failed; see acceptance.json. Keep the frozen fixture unchanged.')
    return result
