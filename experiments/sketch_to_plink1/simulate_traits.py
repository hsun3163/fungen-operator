#!/usr/bin/env python3
"""Deterministic nontrivial traits for the fixed-bin behavioral genotype fixture.

Y_j = C gamma_j + k_j (g_j - Proj_[1,C](g_j)) + sigma_j epsilon_j.
Covariate and conditional genetic components have declared empirical variances;
epsilon is independent N(0,1), never selected for favorable association results.
This specifies synthetic test content, not fidelity to a real cohort or its LD.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import resource
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pysam
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV = pathlib.Path('/sc/arion/work/sunh14/conda/envs/py3.11/bin')
PROTOCOL = ROOT.parent/'xqtl/xqtl-protocol/code/script/association_scan/TensorQTL/TensorQTL.py'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def z(x):
    return (x-x.mean(axis=0))/x.std(axis=0, ddof=1)


def table(frame, path, index=False):
    compression = {'method': 'gzip', 'mtime': 0} if str(path).endswith('.gz') else None
    frame.to_csv(path, sep='\t', index=index, float_format='%.12g', compression=compression)


def run(cmd, log):
    result = subprocess.run(list(map(str, cmd)), text=True, capture_output=True)
    log.write_text(result.stdout+'\n'+result.stderr)
    if result.returncode:
        raise RuntimeError(f'{cmd[0]} failed ({result.returncode}); see {log}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--genotype-prefix', type=pathlib.Path,
                    default=ROOT/'output/sketch_to_plink1/behavioral_fixture/genotype')
    ap.add_argument('--output-dir', type=pathlib.Path,
                    default=ROOT/'output/sketch_to_plink1/behavioral_fixture/traits')
    ap.add_argument('--seed', type=int, default=20260924)
    args = ap.parse_args()
    started = time.monotonic()
    out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    prefix = args.genotype_prefix.resolve()
    rng = np.random.default_rng(args.seed)
    fam = pd.read_csv(str(prefix)+'.fam', sep=r'\s+', header=None, dtype=str)
    bim = pd.read_csv(str(prefix)+'.bim', sep=r'\s+', header=None,
                      names=['chr', 'variant_id', 'cm', 'pos', 'ALT', 'REF'], dtype={'chr': str})
    n, p = len(fam), len(bim)
    ids = fam[1].to_list()
    if fam[[0, 1]].duplicated().any() or len(set(ids)) != n:
        raise ValueError('Synthetic sample IDs must be unique')
    if not all(s.startswith('SYN_EUR_') for s in ids):
        raise ValueError('Expected the synthetic fixed-bin fixture')
    bed = pathlib.Path(str(prefix)+'.bed')
    with bed.open('rb') as f:
        if f.read(3) != bytes([0x6c, 0x1b, 0x01]):
            raise ValueError('Expected SNP-major PLINK1 BED')
    width = (n+3)//4
    if bed.stat().st_size != 3+p*width:
        raise ValueError('BED dimensions disagree with BIM/FAM')
    packed = np.memmap(bed, dtype=np.uint8, mode='r', offset=3, shape=(p, width))
    # BED 00=A1/A1, 01=missing, 10=A1/A2, 11=A2/A2. A1 is ALT.
    codes = ((packed[:, :, None] >> np.array([0, 2, 4, 6], dtype=np.uint8)) & 3)
    geno = np.array([2, 255, 1, 0], dtype=np.uint8)[codes.reshape(p, -1)[:, :n]]
    del codes
    if np.any(geno == 255):
        raise ValueError('Fixed-bin fixture is expected to have complete calls')
    af = geno.mean(axis=1)/2; maf = np.minimum(af, 1-af)
    common = np.flatnonzero((maf >= .1) & (bim.ALT.str.len() == 1) & (bim.REF.str.len() == 1))
    causal_eligible = np.flatnonzero((maf >= .05) & (bim.ALT.str.len() == 1) & (bim.REF.str.len() == 1))
    # Exact PCA on a small, evenly spaced common-SNP panel; no ancestry claim.
    pc_idx = common[np.linspace(0, len(common)-1, min(256, len(common)), dtype=int)]
    panel = z(geno[pc_idx].T.astype(float))
    eigen, vectors = np.linalg.eigh(panel.T @ panel/(n-1))
    loadings = vectors[:, -3:][:, ::-1]
    for j in range(3):
        loadings[:, j] *= np.sign(loadings[np.argmax(np.abs(loadings[:, j])), j])
    pcs = z(panel @ loadings)
    table(bim.iloc[pc_idx][['variant_id', 'chr', 'pos', 'ALT', 'REF']], out/'pc_variants.tsv')

    # Imbalanced batches and correlated demographic/technical covariates.
    batch_score = .35*pcs[:, 0]+rng.normal(size=n)
    batch = np.digitize(batch_score, np.quantile(batch_score, [.1, .3, .6]))
    age = np.clip(58+9*rng.normal(size=n)+2*pcs[:, 0]+1.5*(batch-1.5), 25, 90)
    sex = rng.binomial(1, stats.logistic.cdf(.1+.15*pcs[:, 1]+.1*(batch-1.5)))
    bmi = np.clip(25+.13*(age-58)+1.2*sex+.6*(batch-1.5)+3*rng.normal(size=n), 16, 45)
    cell = stats.logistic.cdf(-.4+.025*(age-58)+.35*pcs[:, 1]+.3*(batch-1.5)+.65*rng.normal(size=n))
    loglib = 15+.16*(batch-1.5)+.4*(cell-.5)+.2*rng.normal(size=n)
    cov = pd.DataFrame({
        'age_z': z(age), 'age_squared_z': z((age-age.mean())**2),
        'sex_01': sex, 'bmi_z': z(bmi),
        'batch_B': (batch == 1).astype(int), 'batch_C': (batch == 2).astype(int),
        'batch_D': (batch == 3).astype(int), 'cell_fraction_z': z(cell),
        'log_library_z': z(loglib), 'PC1': pcs[:, 0], 'PC2': pcs[:, 1], 'PC3': pcs[:, 2]}, index=ids)
    cov.index.name = 'IID'
    X = np.column_stack([np.ones(n), cov.to_numpy()])
    if np.linalg.matrix_rank(X) != X.shape[1]:
        raise ValueError('Covariates are not full rank with an intercept')
    Q, _ = np.linalg.qr(X)
    cov_out = cov.copy(); cov_out.insert(0, 'FID', fam[0].to_numpy())
    cov_out.insert(1, 'IID', ids); table(cov_out, out/'covariates.tsv')
    cov_t = cov.T; cov_t.index.name = '#id'; table(cov_t, out/'covariates.cov.gz', index=True)
    raw = pd.DataFrame({'FID': fam[0], 'IID': ids, 'age_years': age, 'sex_01': sex,
                        'bmi': bmi, 'batch': np.array(list('ABCD'))[batch],
                        'cell_fraction': cell, 'log_library_size': loglib})
    table(raw, out/'sample_metadata.tsv')
    table(cov.corr().rename_axis('covariate'), out/'covariate_correlations.tsv', index=True)
    means = cov.mean().to_numpy()
    weights = np.array([.55, .25, -.3, .35, .15, -.25, .35, .45, .25, .35, -.25, .2])
    regions = pd.read_csv(ROOT/'output/sketch_to_plink1/prepared/regions.tsv', sep='\t')
    ys, coords, causal_rows, truth_rows, model_rows, component_cols = [], [], [], [], [], {}
    region_indices = {}
    trait_causes = {}
    for rid, rg in regions.iterrows():
        source = pd.read_csv(rg.metadata_path, sep='\t')
        index = bim.index[bim.variant_id.isin(source.ID)].to_numpy()
        if len(index) != int(rg.n_variants):
            raise ValueError(f'Region {rg.region_id} does not match exported BIM')
        candidates = np.intersect1d(index, causal_eligible)
        if len(candidates) < 2:
            raise ValueError(f'Region {rg.region_id} has fewer than two eligible MAF>=0.05 SNPs')
        midpoint = (int(rg.region_start)+int(rg.region_end))/2
        near = candidates[np.abs(bim.pos.to_numpy()[candidates]-midpoint) < 450000]
        if len(near) >= 3:
            candidates = near
        candidates = rng.permutation(candidates)
        chosen = [int(candidates[0])]
        if rid % 2:
            for first in candidates:
                other = candidates[(candidates != first) & (np.abs(bim.pos.to_numpy()[candidates]-bim.pos.iloc[first]) <= 500000)]
                if not len(other):
                    continue
                corr = z(geno[other].T.astype(float)).T @ z(geno[first].astype(float))/(n-1)
                ok = np.flatnonzero(np.abs(corr) < .2)
                if len(ok):
                    chosen = [int(first), int(other[ok[0]])]; break
            if len(chosen) != 2:
                raise ValueError(f'No low-LD causal pair found in {rg.region_id}')
        anchor = int(bim.pos.iloc[chosen[0]])
        weights_j = weights * rng.uniform(.7, 1.3, len(weights))
        cv = (cov.to_numpy()-means) @ weights_j
        gamma = weights_j*np.sqrt(.25)/cv.std(ddof=1)
        cv = (cov.to_numpy()-means) @ gamma
        for kind in ['signal', 'null']:
            trait = f'SYN_TRAIT_{rid+1:02d}_{kind.upper()}'
            h = [.03, .06, .12][rid % 3] if kind == 'signal' else 0.
            # Alternating directions and opposing effects in two-causal traits.
            raw_beta = np.array([1., -.7][:len(chosen)]) * (1 if rid % 4 < 2 else -1)
            raw_g = geno[chosen].T @ raw_beta if h else np.zeros(n)
            alpha = np.linalg.lstsq(X, raw_g, rcond=None)[0]
            residual_g = raw_g-X @ alpha
            k = np.sqrt(h)/residual_g.std(ddof=1) if h else 0.
            genetic = k*residual_g
            sigma = np.sqrt(1-.25-h)
            noise = sigma*rng.normal(size=n)
            y = cv+genetic+noise
            ys.append(y); coords.append(['chr'+str(rg.chromosome), anchor-1, anchor, trait])
            region_indices[trait] = index
            trait_causes[trait] = chosen if h else []
            component_cols[f'{trait}:covariate'] = cv
            component_cols[f'{trait}:genetic'] = genetic
            component_cols[f'{trait}:noise'] = noise
            # Equivalent direct model Y = intercept + C gamma_eff + G_ALT beta + noise.
            direct = np.r_[-means @ gamma, gamma]-k*alpha
            model_rows.extend({'phenotype_id': trait, 'term': term, 'coefficient': float(v)}
                              for term, v in zip(['intercept']+list(cov.columns), direct))
            if h:
                causal_rows.extend({'phenotype_id': trait, 'region_id': rg.region_id,
                                    'variant_id': bim.variant_id.iloc[c], 'chr': str(bim.chr.iloc[c]),
                                    'pos': int(bim.pos.iloc[c]), 'effect_allele': bim.ALT.iloc[c],
                                    'other_allele': bim.REF.iloc[c], 'maf': float(maf[c]),
                                    'beta_per_ALT': float(k*b)} for c, b in zip(chosen, raw_beta))
            truth_rows.append({'phenotype_id': trait, 'region_id': rg.region_id, 'kind': kind,
                               'n_causal': len(chosen) if h else 0,
                               'nominal_genetic_variance': h, 'nominal_covariate_variance': .25,
                               'noise_variance_parameter': sigma**2,
                               'nominal_conditional_h2': h/.75,
                               'genetic_variance': float(genetic.var(ddof=1)),
                               'covariate_variance': float(cv.var(ddof=1)),
                               'noise_variance': float(noise.var(ddof=1)),
                               'phenotype_variance': float(y.var(ddof=1)),
                               'genetic_covariate_covariance': float(np.cov(genetic, cv)[0, 1]),
                               'genetic_noise_covariance': float(np.cov(genetic, noise)[0, 1]),
                               'covariate_noise_covariance': float(np.cov(cv, noise)[0, 1])})
    ph = pd.DataFrame(np.array(ys).T, index=ids, columns=[c[3] for c in coords])
    ph_out = ph.copy(); ph_out.insert(0, 'FID', fam[0].to_numpy()); ph_out.insert(1, 'IID', ids)
    table(ph_out, out/'phenotypes.tsv')
    coord_df = pd.DataFrame(coords, columns=['#chr', 'start', 'end', 'ID'])
    wide = pd.concat([coord_df, pd.DataFrame(ys, columns=ids)], axis=1)
    # Natural chromosome order, half-open BED coordinates, synthetic trait IDs.
    wide['_chr'] = wide['#chr'].str.removeprefix('chr').astype(int)
    wide = wide.sort_values(['_chr', 'start', 'ID']).drop(columns='_chr')
    table(wide, out/'phenotypes.bed')
    pysam.tabix_compress(str(out/'phenotypes.bed'), str(out/'phenotypes.bed.gz'), force=True)
    pysam.tabix_index(str(out/'phenotypes.bed.gz'), preset='bed', force=True)
    table(pd.DataFrame(causal_rows), out/'causal_truth.tsv')
    table(pd.DataFrame(truth_rows), out/'phenotype_truth.tsv')
    table(pd.DataFrame(model_rows), out/'covariate_model_truth.tsv')
    comp = pd.DataFrame(component_cols, index=ids); comp.index.name = 'IID'
    table(comp, out/'phenotype_components.tsv.gz', index=True)

    # Verify serialized inputs with the actual canonical reader functions.
    spec = importlib.util.spec_from_file_location('native_tensorqtl_interface', PROTOCOL)
    native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
    read_cov = native.load_covariates(str(out/'covariates.cov.gz'))
    read_ph, read_pos = native.load_phenotype_bed(str(out/'phenotypes.bed.gz'))
    if list(read_cov.index) != ids or list(read_ph.columns) != ids:
        raise ValueError('Native reader sample order differs from FAM')
    np.testing.assert_allclose(read_cov.to_numpy(), cov.to_numpy(), rtol=1E-10, atol=1E-10)
    np.testing.assert_allclose(read_ph.loc[ph.columns].to_numpy().T, ph.to_numpy(), rtol=1E-10, atol=1E-10)
    with pysam.TabixFile(str(out/'phenotypes.bed.gz')) as tbx:
        if sum(sum(1 for _ in tbx.fetch(c)) for c in tbx.contigs) != len(ph.columns):
            raise ValueError('Tabix retrieval did not cover all phenotypes')
    # Inferential QC uses saved covariates/phenotypes, without selecting seeds or effects by P.
    X = np.column_stack([np.ones(n), read_cov.to_numpy()]); Q, _ = np.linalg.qr(X)
    n_cov = X.shape[1]; assoc, joint = [], []
    causals = pd.DataFrame(causal_rows)
    for trait in ph.columns:
        y = read_ph.loc[trait].to_numpy(float); yr = y-Q @ (Q.T @ y)
        index = region_indices[trait]
        gr = geno[index].T.astype(float); gr -= Q @ (Q.T @ gr)
        ss = np.sum(gr*gr, axis=0)
        beta = gr.T @ yr/ss
        sse = np.maximum(np.sum(yr*yr)-beta*beta*ss, 0.)
        se = np.sqrt(sse/(n-n_cov-1)/ss)
        pv = 2*stats.t.sf(np.abs(beta/se), n-n_cov-1)
        for j, i in enumerate(index):
            assoc.append({'phenotype_id': trait, 'variant_id': bim.variant_id.iloc[i],
                          'beta_ALT': beta[j], 'se': se[j], 'p_value': pv[j],
                          'causal': i in trait_causes[trait]})
        chosen = trait_causes[trait]
        if chosen:
            design = np.column_stack([X, geno[chosen].T])
            b = np.linalg.lstsq(design, y, rcond=None)[0]
            resid = y-design @ b; df = n-design.shape[1]
            ses = np.sqrt(np.diag(np.linalg.inv(design.T @ design))*np.sum(resid*resid)/df)
            for j, c in enumerate(chosen):
                expected = float(causals.loc[(causals.phenotype_id == trait) & (causals.variant_id == bim.variant_id.iloc[c]), 'beta_per_ALT'].iloc[0])
                observed = b[n_cov+j]; serr = ses[n_cov+j]
                joint.append({'phenotype_id': trait, 'variant_id': bim.variant_id.iloc[c],
                              'expected_beta_ALT': expected, 'estimated_beta_ALT': observed,
                              'se': serr, 'p_value': float(2*stats.t.sf(abs(observed/serr), df)),
                              'correct_direction': bool(expected*observed > 0),
                              'estimation_error_in_SE': float((observed-expected)/serr)})
    assoc = pd.DataFrame(assoc); joint = pd.DataFrame(joint)
    table(assoc, out/'regional_association_qc.tsv.gz'); table(joint, out/'joint_causal_recovery.tsv')
    null = assoc[assoc.phenotype_id.str.endswith('_NULL')]
    # Independent native PLINK association smoke test across all planted variants/traits.
    native_dir = out/'plink_qc'; native_dir.mkdir(exist_ok=True)
    selected = out/'causal_variant_ids.txt'
    selected.write_text('\n'.join(causals.variant_id.drop_duplicates())+'\n')
    command = [ENV/'plink', '--bfile', prefix, '--keep-allele-order', '--extract', selected,
               '--pheno', out/'phenotypes.tsv', '--all-pheno', '--covar', out/'covariates.tsv',
               '--linear', 'hide-covar', '--allow-no-sex', '--memory', '1024', '--threads', '1',
               '--out', native_dir/'association']
    run(command, native_dir/'command.log')
    save_json(native_dir/'command.json', list(map(str, command)))
    native_checks = []
    for trait in ph.columns:
        native_result = pd.read_csv(native_dir/f'association.{trait}.assoc.linear', sep=r'\s+')
        if len(native_result) != causals.variant_id.nunique() or not np.isfinite(native_result.P).all():
            raise ValueError(f'PLINK failed to test all selected variants for {trait}')
        for row in native_result.itertuples():
            expected_allele = bim.loc[bim.variant_id == row.SNP, 'ALT'].iloc[0]
            if row.A1 != expected_allele or row.NMISS != n:
                raise ValueError('PLINK allele or sample count mismatch')
            local = assoc[(assoc.phenotype_id == trait) & (assoc.variant_id == row.SNP)]
            if len(local):
                expected = float(local.beta_ALT.iloc[0])
                if not np.isclose(row.BETA, expected, rtol=.002, atol=1E-6):
                    raise ValueError(f'PLINK beta differs from adjusted OLS at {trait}/{row.SNP}')
            native_checks.append({'phenotype_id': trait, 'variant_id': row.SNP,
                                  'beta_ALT': row.BETA, 'p_value': row.P, 'N': int(row.NMISS)})
    table(pd.DataFrame(native_checks), out/'native_plink_association_qc.tsv')
    summary = {
        'status': 'complete', 'seed': args.seed, 'samples': n, 'variants': p,
        'covariates': cov.shape[1], 'design_rank_including_intercept': int(np.linalg.matrix_rank(X)),
        'design_condition_number': float(np.linalg.cond(X)),
        'phenotypes': len(ph.columns), 'signal_phenotypes': 20, 'null_phenotypes': 20,
        'causal_effects': len(joint), 'causal_effects_correct_direction': int(joint.correct_direction.sum()),
        'causal_effects_joint_P_below_5E_8': int((joint.p_value < 5E-8).sum()),
        'max_joint_causal_P': float(joint.p_value.max()),
        'null_tests': len(null), 'null_nominal_P_below_005_fraction': float((null.p_value < .05).mean()),
        'null_traits_region_Bonferroni_significant': int((null.groupby('phenotype_id').p_value.min() < .05/1000).sum()),
        'native_reader_sample_alignment': 'exact', 'native_PLINK_tests': len(native_checks),
        'native_PLINK_local_betas_match_OLS': True, 'tabix_index': 'verified',
        'missing_covariates': int(read_cov.isna().sum().sum()), 'missing_phenotypes': int(read_ph.isna().sum().sum()),
        'runtime_seconds': time.monotonic()-started, 'peak_rss_MB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        'interpretation': 'Planted signal is answerable in this artificial matrix; original LD fidelity and fine-mapping performance remain unclaimed.'}
    save_json(out/'qc_summary.json', summary)
    provenance = {'generator': str(pathlib.Path(__file__).resolve()), 'generator_sha256': sha(__file__),
                  'seed': args.seed, 'command': sys.argv, 'python': sys.version,
                  'LD_LIBRARY_PATH': os.environ.get('LD_LIBRARY_PATH', ''),
                  'numpy_version': np.__version__, 'pandas_version': pd.__version__,
                  'genotype_prefix': str(prefix), 'input_sha256': {e: sha(str(prefix)+'.'+e) for e in ['bed', 'bim', 'fam']},
                  'canonical_reader': str(PROTOCOL), 'canonical_reader_sha256': sha(PROTOCOL),
                  'pc_panel_size': len(pc_idx), 'pc_variance_fractions': (eigen[-3:][::-1]/eigen.sum()).tolist(),
                  'causal_MAF_minimum': .05, 'pc_MAF_minimum': .1,
                  'genetic_variance_grid': [.03, .06, .12], 'covariate_variance': .25,
                  'epsilon': 'independent standard Gaussian; not orthogonalized or outcome-selected',
                  'artifact_sha256': {str(f.relative_to(out)): sha(f) for f in sorted(out.iterdir()) if f.is_file() and f.name != 'provenance.json'}}
    save_json(out/'provenance.json', provenance)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
