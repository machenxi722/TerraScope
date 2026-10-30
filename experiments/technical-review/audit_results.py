#!/usr/bin/env python3
"""Recompute the supplied TerraScope tables; no model inference or training.

Python standard library only. Run from any directory:
  python3 audit_results.py --out audit_results.json
All bootstrap intervals are exploratory; the package lacks full spatial groups.
"""
import argparse
import csv
import hashlib
import json
import math
import random
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path


def quantile(values, p):
    a = sorted(values)
    pos = (len(a) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(a) - 1)
    return a[lo] + (a[hi] - a[lo]) * (pos - lo)


def wilson(k, n):
    z = 1.959963984540054
    p = k / n
    den = 1 + z*z/n
    mid = (p + z*z/(2*n))/den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [100*(mid-half), 100*(mid+half)]


def bootstrap_mean(values, seed=20261015, repeats=10000):
    rng = random.Random(seed)
    samples = [st.mean(rng.choices(values, k=len(values))) for _ in range(repeats)]
    return [quantile(samples, .025), quantile(samples, .975)]


def cluster_bootstrap(rows, value_fn, seed=20261015, repeats=10000):
    groups = defaultdict(list)
    for row in rows:
        groups[row['影像ID'].rsplit('_', 1)[0]].append(value_fn(row))
    vals = list(groups.values())
    rng = random.Random(seed)
    means = []
    for _ in range(repeats):
        selected = rng.choices(vals, k=len(vals))
        means.append(st.mean(v for group in selected for v in group))
    return {'groups': len(groups), 'ci95_pp': [quantile(means, .025), quantile(means, .975)],
            'assumption': 'Country/event prefix is the available grouping proxy; not a full geographic independence guarantee.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package', type=Path, default=Path(__file__).resolve().parent.parent / 'TerraScope_汇报润色分享包_20261015')
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    root = args.package / '03_结果表与口径'
    accessed = []

    def read_json(name):
        p = root / '原始统计记录' / name
        accessed.append(p)
        return json.loads(p.read_text(encoding='utf-8-sig'))

    def read_csv(name):
        p = root / name
        accessed.append(p)
        with p.open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))

    report = {'scope': 'Aggregate/row-level numeric audit only; raw imagery, prediction masks and teammate source code are absent.',
              'seed': 20261015,
              'inventory': dict(Counter(p.suffix.lower() for p in args.package.rglob('*') if p.is_file()))}
    abc = read_json('ABC_100题汇总.json')
    bc = next(x for x in abc['paired'] if x['split']=='test' and x['left']=='B' and x['right']=='C')
    n_discordant = bc['left_only_correct'] + bc['right_only_correct']
    k_small = min(bc['left_only_correct'], bc['right_only_correct'])
    report['qa100'] = {
        'summary': [x for x in abc['summary'] if x['split']=='test'],
        'B_C_paired': bc,
        'mcnemar_exact_two_sided': min(1, 2*sum(math.comb(n_discordant, k) for k in range(k_small+1))/2**n_discordant),
        'inference_limit': 'Question-wise test; repeated images/geographic dependence cannot be checked from aggregate tables.'}
    small = read_json('12幅水体ABC原统计.json')
    errors = {k: [abs(x[k]-x['gt']) for x in small] for k in 'ABC'}
    common = [x for x in small if x['A_strict'] is not None]
    report['water12'] = {
        'n': len(small), 'mae_pp': {k: st.mean(v) for k,v in errors.items()},
        'B_to_C_improved': sum(c < b for b,c in zip(errors['B'], errors['C'])),
        'B_minus_C_mae_pp': st.mean(b-c for b,c in zip(errors['B'],errors['C'])),
        'B_minus_C_scene_bootstrap95_pp': bootstrap_mean([b-c for b,c in zip(errors['B'],errors['C'])]),
        'A_strict_missing': len(small)-len(common),
        'strict_common7_mae_pp': {k: st.mean(abs(x['A_strict' if k=='A' else k]-x['gt']) for x in common) for k in 'ABC'},
        'reference_below_5pct_count': sum(x['gt'] < 5 for x in small)}
    con = read_json('200题一致性原统计.json')
    all_con = next(x for x in con if x['task']=='all')
    report['consistency200'] = {'by_task': con,
        'flagged_error_precision_pct': 100*all_con['flagged_B_errors']/all_con['flagged'],
        'correct_answers_flagged': all_con['flagged']-all_con['flagged_B_errors'],
        'retained_accuracy_wilson95_pct': wilson(all_con['passed_correct'], all_con['passed'])}
    iou = read_csv('P13_65幅水体IoU对照.csv')
    diff_fn = lambda x: float(x['MNDWI_IoU_pct']) - float(x['TerraScope_IoU_pct'])
    report['water65'] = {'n': len(iou),
        'MNDWI_wins': sum(diff_fn(x)>0 for x in iou),
        'MNDWI_minus_TerraScope_mean_pp': st.mean(map(diff_fn, iou)),
        'paired_event_bootstrap': cluster_bootstrap(iou, diff_fn),
        'by_model': {k: {'mean': st.mean(float(x[k]) for x in iou), 'median': st.median(float(x[k]) for x in iou),
                        'zero_count': sum(float(x[k])==0 for x in iou)} for k in ['TerraScope_IoU_pct','MNDWI_IoU_pct']}}
    water = read_json('水体逐景原统计.json')
    report['water_validity'] = {'total': len(water), 'zero_valid': sum(x.get('valid_fraction',0)==0 for x in water),
        'fully_valid': sum(x.get('valid_fraction')==1 for x in water),
        'below_half_valid': sum(0<x.get('valid_fraction',0)<.5 for x in water)}
    split_root = Path(__file__).resolve().parent / 'dataset_split_snapshot'
    if split_root.exists():
        split_ids = {}
        split_hashes = {}
        for p in sorted(split_root.glob('*.csv')):
            with p.open(encoding='utf-8', newline='') as f:
                rows = list(csv.reader(f))
            split_ids[p.name] = {row[0].rsplit('/',1)[-1].removesuffix('_S1Hand.tif') for row in rows}
            assert len(rows) == len(split_ids[p.name]), 'Duplicate IDs in official split snapshot'
            split_hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        water_ids = {x['id'] for x in water}
        report['official_split_audit'] = {
            'counts': {k:len(v) for k,v in split_ids.items()},
            'package72_overlap': {k:len(v & water_ids) for k,v in split_ids.items()},
            'pairwise_overlap': {a+' + '+b:len(split_ids[a]&split_ids[b]) for a in split_ids for b in split_ids if a<b},
            'sha256': split_hashes,
            'source': 'Official public GCS v1.1/splits/flood_handlabeled; see dataset_split_snapshot/provenance.json'}
        assert not any(report['official_split_audit']['pairwise_overlap'].values())
    roads_all = read_json('道路对齐修正后逐景统计.json')
    roads = [x for x in roads_all if x['split'] in ('evaluation','extension')]
    def outcome(x, key):
        pred = x[key] >= .1
        return ('T' if pred==x['true_priority'] else 'F') + ('P' if pred else 'N')
    base_cm = dict(Counter(outcome(x,'baseline_share') for x in roads))
    report['roads48'] = {
        'n': len(roads), 'confusion': base_cm,
        'accuracy_pct': 100*(base_cm['TP']+base_cm['TN'])/len(roads),
        'accuracy_wilson95_pct': wilson(base_cm['TP']+base_cm['TN'], len(roads)),
        'precision_pct':100*base_cm['TP']/(base_cm['TP']+base_cm['FP']),
        'recall_pct':100*base_cm['TP']/(base_cm['TP']+base_cm['FN']),
        'mae_pp': st.mean(100*abs(x['baseline_share']-x['reference_share']) for x in roads),
        'baseline_mean_road_iou_pct': 100*st.mean(x['baseline_road_iou'] for x in roads),
        'consensus_mean_road_iou_pct': 100*st.mean(x['consensus_road_iou'] for x in roads),
        'consensus_confusion': dict(Counter(outcome(x,'consensus_share') for x in roads)),
        'GT_share_exactly_zero_or_one':sum(x['reference_share'] in (0,1) for x in roads),
        'any_prompt_missing': sum(not x['all_three_valid'] for x in roads),
        'prompt_decision_flips': sum(x['decision_flip'] for x in roads),
        'errors': [{k:x[k] for k in ['id','split','baseline_share','reference_share','range','all_three_valid']} for x in roads if outcome(x,'baseline_share')[0]=='F']}
    road_csv = read_csv('P11_48幅道路逐景结果.csv')
    by_id = {x['id']:x for x in roads}
    for x in road_csv:
        assert math.isclose(float(x['模型道路内水面_pct']), by_id[x['影像ID']]['baseline_share']*100, abs_tol=1e-9)
        assert x['结果类型'] == outcome(by_id[x['影像ID']], 'baseline_share')
    rev = read_json('71幅复核模拟原统计.json')
    rows = rev['rows']
    truth = {x['id']:x['reference_pct'] for x in rows}
    baseline = {x['id']:x['p'][0] for x in rows}
    # Stable alphabetical tie-break; this agrees with provided top-24 membership.
    def top(scores):
        return set(sorted(scores, key=lambda k:(-scores[k], k))[:rev['top_k']])
    ref_top = top(truth)
    assert ref_top == set(rev['reference_top'])
    strategies = {}
    for name in ['no_review','prompt_disagreement','decision_boundary','spectral_disagreement']:
        data = rev['results'][name]
        scores = baseline.copy()
        for image_id in data.get('reviewed_ids',[]):
            scores[image_id] = truth[image_id]
        hits = len(top(scores) & ref_top)
        assert hits == data['top_k_hits'], (name,hits,data['top_k_hits'])
        strategies[name] = hits
    rng = random.Random(20261015)
    random_hits = []
    ids = sorted(truth)
    for _ in range(10000):
        scores = baseline.copy()
        for image_id in rng.sample(ids, rev['budget']):
            scores[image_id] = truth[image_id]
        random_hits.append(len(top(scores) & ref_top))
    report['review71'] = {'n':len(rows),'top_k':rev['top_k'],'budget':rev['budget'],
        'strategies_recomputed':strategies, 'provided_random':rev['results']['random_review']['top_k_hits'],
        'random_10000_new_seed':{'mean':st.mean(random_hits),'p025':quantile(random_hits,.025),'p975':quantile(random_hits,.975),
                                'fraction_hits_ge_18':sum(x>=18 for x in random_hits)/len(random_hits)},
        'large_error_zero_prompt_disagreement':[{k:x[k] for k in ['id','valid_fraction','p','reference_pct','difference_pp']} for x in rows if x['difference_pp']==0 and abs(x['p'][0]-x['reference_pct'])>20],
        'interpretation':'Oracle review simulation only. Random tail frequency is conditional on this fixed pool, not a population-level significance test.'}
    report['source_sha256'] = {str(p.relative_to(args.package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in accessed}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text+'\n', encoding='utf-8')
        print(f'Wrote {args.out}; all cross-table assertions passed.')
    else:
        print(text)


if __name__ == '__main__':
    main()
