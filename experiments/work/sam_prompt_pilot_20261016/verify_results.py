"""Verify downloaded pilot artifacts against local frozen labels."""
from pathlib import Path
import json, hashlib, zipfile, csv
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
BACKUP = ROOT / 'backup'
OUT = PROJECT / 'outputs/TerraScope_SAM2空间提示小实验_20261016'
OUT.mkdir(parents=True, exist_ok=True)

archive = ROOT / 'sam_prompt_pilot_small_backup.zip'
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    hashes = json.loads(z.read('result_sha256.json'))
    assert set(z.namelist()) == set(hashes) | {'result_sha256.json'}
    for name, sha in hashes.items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert hashlib.sha256(z.read(name)).hexdigest() == sha, name
    z.extractall(BACKUP)

report = json.loads((BACKUP/'results/report.json').read_text())
assert report['completed'] and report['paired_sampling_identical']
assert report['test_accessed'] is False
assert report['preflight']['zero_gate_max_logit_difference'] == 0
manifest = json.loads((BACKUP/'manifest.json').read_text())
validation = {r['id']: r for r in manifest if r['split'] == 'val'}
assert len(validation) == 80
verified = {}
for name in ['initial_single_view', 'continued_control_selected',
             'dense_prompt_selected', 'dense_prompt_prompt_disabled']:
    result = json.loads((BACKUP/'results'/f'{name}_val.json').read_text())
    assert {r['id'] for r in result['per_image']} == set(validation)
    totals = np.zeros(3, dtype=np.int64)
    for row in result['per_image']:
        sid = row['id']
        label_path = PROJECT/'work/finetune_formal_20261015/data'/sid/'labels.png'
        assert hashlib.sha256(label_path.read_bytes()).hexdigest() == validation[sid]['label_sha256']
        label = np.array(Image.open(label_path))
        pred = np.array(Image.open(BACKUP/'results/predictions'/name/f'{sid}.png')) > 0
        assert pred.shape == label.shape
        gt, valid = label == 3, label != 255
        counts = [int((pred & gt & valid).sum()), int((pred & ~gt & valid).sum()),
                  int((~pred & gt & valid).sum())]
        assert counts == [row['tp'], row['fp'], row['fn']], (name, sid)
        totals += counts
    iou = int(totals[0]) / max(1, int(totals.sum()))
    assert abs(iou - result['summary']['global_iou']) < 1e-12
    verified[name] = {'tp_fp_fn': totals.tolist(), 'global_iou': iou, 'n': 80}

traces = {name: json.loads((BACKUP/'results'/f'{name}_training.json').read_text())
          for name in ['continued_control', 'dense_prompt']}
assert traces['continued_control']['sampling_sequence'] == traces['dense_prompt']['sampling_sequence']
assert all(len(t['trace']) == 1200 for t in traces.values())
audit = {'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
         'verified_members': len(hashes), 'verified_prediction_masks': 320,
         'recomputed_validation': verified, 'paired_sample_sequence_equal': True,
         'test_accessed': False}
(OUT/'本地复算与文件校验.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
(OUT/'实验报告原始.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
with (OUT/'验证曲线.csv').open('w') as f:
    w = csv.writer(f)
    w.writerow(['方法', '训练微步数', '验证IoU百分比', '覆盖率MAE百分点'])
    for arm, tr in traces.items():
        for r in tr['validation']:
            w.writerow([arm, r['micro_step'], r['global_iou']*100, r['coverage_mae_pp']])
print(json.dumps({'audit':audit, 'preflight':report['preflight'], 'arms':report['arms'],
                  'elapsed_seconds': report['elapsed_seconds']}, ensure_ascii=False, indent=2))
