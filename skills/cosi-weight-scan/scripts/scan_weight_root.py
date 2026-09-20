#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

MODELS = ["P0.001.txt", "P0.05.txt", "PRScs.txt", "SDPR.txt", "lassosum.txt"]


def load_regions(path):
    regions = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            chrom = row.get("#chr") or row.get("chr") or row.get("chrom") or row.get("CHROM")
            start = row.get("start") or row.get("START")
            end = row.get("end") or row.get("END")
            gene = row.get("gene_id") or row.get("TargetID") or row.get("gene") or ""
            if chrom and start and end:
                regions.append((f"{chrom}_{start}_{end}", gene))
    return regions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weight-root", required=True)
    ap.add_argument("--region-list", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.weight_root)
    regions = load_regions(args.region_list)

    model = {m: {"exist": 0, "good": 0, "header": 0, "missing": 0} for m in MODELS}
    buckets = {"all5_good": 0, "any_good": 0, "zero_good": 0, "all5_exist": 0, "missing_all": 0}

    for region, _gene in regions:
        good = 0
        exist = 0
        for m in MODELS:
            p = root / region / "cache" / m
            if not p.exists():
                model[m]["missing"] += 1
                continue
            exist += 1
            model[m]["exist"] += 1
            size = p.stat().st_size
            if size > 28:
                good += 1
                model[m]["good"] += 1
            elif size == 28:
                model[m]["header"] += 1
        buckets["all5_exist"] += int(exist == len(MODELS))
        buckets["missing_all"] += int(exist == 0)
        buckets["all5_good"] += int(good == len(MODELS))
        buckets["any_good"] += int(good > 0)
        buckets["zero_good"] += int(good == 0)

    total_models = len(regions) * len(MODELS)
    good_models = sum(v["good"] for v in model.values())
    out = {
        "weight_root": str(root),
        "region_list": args.region_list,
        "regions": len(regions),
        **buckets,
        "remaining_regions_without_all5_good": len(regions) - buckets["all5_good"],
        "total_model_slots": total_models,
        "good_model_outputs": good_models,
        "remaining_model_outputs_without_good": total_models - good_models,
        "models": model,
    }

    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        for k in [
            "regions",
            "all5_good",
            "any_good",
            "zero_good",
            "all5_exist",
            "missing_all",
            "remaining_regions_without_all5_good",
            "total_model_slots",
            "good_model_outputs",
            "remaining_model_outputs_without_good",
        ]:
            print(f"{k}\t{out[k]}")
        print("model\texist\tgood\theader\tmissing")
        for m in MODELS:
            v = model[m]
            print(f"{m}\t{v['exist']}\t{v['good']}\t{v['header']}\t{v['missing']}")


if __name__ == "__main__":
    main()
