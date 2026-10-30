"""Paired tile bootstrap; report event dependence rather than treating pixels as independent."""
import argparse
import csv

import numpy as np

from .common import write_json


def read_rows(path):
    with open(path) as f:
        result = {r["id"]: r for r in csv.DictReader(f)}
    for row in result.values():
        for key in ("tp", "fp", "fn", "area_abs_error_pp"):
            row[key] = float(row[key])
    return result


def metrics(rows):
    tp, fp, fn = [sum(r[k] for r in rows) for k in ("tp", "fp", "fn")]
    return np.array([tp / (tp + fp + fn) if tp + fp + fn else np.nan,
                     np.mean([r["area_abs_error_pp"] for r in rows])])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--resamples", type=int, default=2000)
    p.add_argument("--unit", choices=["tile", "country"], default="tile")
    a = p.parse_args()
    b, c = read_rows(a.baseline), read_rows(a.candidate)
    if set(b) != set(c) or not b:
        raise ValueError("Comparisons must contain exactly the same sample IDs")
    if {r["split"] for r in b.values()} != {r["split"] for r in c.values()}:
        raise ValueError("Split mismatch")
    ids = sorted(b)
    groups = {i: [i] for i in ids} if a.unit == "tile" else {
        country: [i for i in ids if i.split("_")[0] == country] for country in {i.split("_")[0] for i in ids}}
    keys = sorted(groups)
    if len(keys) < 2:
        raise ValueError("Need at least two resampling units; Bolivia alone has only one country")
    rng = np.random.default_rng(20261015)
    deltas = []
    for _ in range(a.resamples):
        picked = [i for k in rng.choice(keys, size=len(keys), replace=True) for i in groups[k]]
        deltas.append(metrics([c[i] for i in picked]) - metrics([b[i] for i in picked]))
    deltas = np.array(deltas)
    delta = metrics(list(c.values())) - metrics(list(b.values()))
    write_json(a.out, {"n": len(ids), "resampling_unit": a.unit, "n_units": len(keys),
                       "delta_micro_iou": float(delta[0]), "delta_area_mae_pp": float(delta[1]),
                       "paired_95pct_ci": np.nanpercentile(deltas, [2.5, 97.5], axis=0).T.tolist(),
                       "ci_order": ["micro_iou", "area_mae_pp"],
                       "interpretation": "IoU delta positive is better; area MAE delta negative is better",
                       "limitation": "Tile CI does not establish independence across nearby tiles. Country grouping is only a coarse event proxy; few groups make CI unstable."})


if __name__ == "__main__":
    main()
