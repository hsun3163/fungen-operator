import collections,csv,json,sys
p=json.load(open(sys.argv[1]));counts=collections.Counter();genes=collections.defaultdict(set)
with open(p['inputs']['table']) as f:
 for row in csv.DictReader(f,delimiter='\t'):
  dataset=row['eqtl'];counts[dataset]+=1
  if row['gene'] not in ('','NA','NaN','nan'):genes[dataset].add(row['gene'])
with open(sys.argv[2],'w') as f:
 w=csv.writer(f,delimiter='\t',lineterminator='\n');w.writerow(['eqtl','row_count','distinct_genes','gene','distinct_gene_fraction'])
 for dataset in sorted(counts):w.writerow([dataset,counts[dataset],len(genes[dataset]),min(genes[dataset]) if genes[dataset] else '',len(genes[dataset])/counts[dataset]])
