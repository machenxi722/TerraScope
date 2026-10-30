"""Audit all saved four-view masks; requires audited primary and holdout backups."""
from pathlib import Path
import argparse, hashlib, json, zipfile
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('archive',type=Path);args=ap.parse_args()
dest=HERE/'tta_backup';dest.mkdir(exist_ok=True)
with zipfile.ZipFile(args.archive)as z:
 assert z.testzip()is None
 hashes=json.loads(z.read('result_sha256.json'))
 for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
 for name in z.namelist():assert (dest/name).resolve().is_relative_to(dest.resolve())
 z.extractall(dest)
for name,digest in json.loads((HERE/'tta_code_sha256.json').read_text()).items():
 assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==digest,name
report=json.loads((dest/'results/report.json').read_text());assert report['completed']
assert 'validation_choice_locked_at'in report
manifest=json.loads((dest/'manifest.json').read_text());assert len(manifest)==898
night=json.loads((HERE/'backup/results/report.json').read_text())
assert report['checkpoint_name']==max(night['arms'],key=lambda n:night['arms'][n]['best_val_global_iou'])
out=ROOT/'outputs/TerraScope_夜间优化_20261016'
assert (out/'核验与汇总.json').exists()and(out/'额外370幅核验结果.json').exists()
audit={'archive_sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest(),'code_hashes_verified':True,'checkpoint_name':report['checkpoint_name'],'deployment_mode_selected_by_validation':report['deployment_mode_selected_by_validation'],'splits':{}}
for split,expected_n,expected_pos in [('val',80,30),('test',448,49),('holdout',370,23)]:
 selected=[r for r in manifest if r['split']==split];assert len(selected)==expected_n
 stats={}
 for mode in ['single_view','tta4']:
  folder=dest/'results/predictions'/mode/split
  assert {p.stem for p in folder.glob('*.png')}=={r['id']for r in selected}
  saved=json.loads((dest/'results'/f'{mode}_{split}.json').read_text())
  expected={r['id']:r for r in saved['per_image']};assert set(expected)=={r['id']for r in selected}
  rows=[];max_disagreement=0
  for row in selected:
   sid=row['id'];label=(HERE/'holdout/data'if split=='holdout'else ROOT/'work/finetune_formal_20261015/data')/sid/'labels.png'
   assert hashlib.sha256(label.read_bytes()).hexdigest()==row['label_sha256']
   y=np.array(Image.open(label));mask=np.array(Image.open(folder/f'{sid}.png'))
   assert mask.shape==y.shape and set(np.unique(mask)).issubset({0,255})
   p=mask>0;g=y==3;v=y!=255
   rec={'id':sid,'tp':int((p&g&v).sum()),'fp':int((p&~g&v).sum()),'fn':int((~p&g&v).sum()),'valid_pixels':int(v.sum()),'pred_pixels':int((p&v).sum()),'gt_pixels':int((g&v).sum())}
   for key,value in rec.items():assert expected[sid][key]==value,(split,mode,sid,key)
   rows.append(rec)
   if mode=='single_view'and split!='val':
    reference=(HERE/'backup/results/predictions'/report['checkpoint_name']/'test'if split=='test'else HERE/'holdout_backup/results/predictions'/report['holdout_label']/'holdout')/f'{sid}.png'
    old=np.array(Image.open(reference))>0;assert old.shape==p.shape
    difference=float(np.mean(old!=p));assert difference<=1e-4
    max_disagreement=max(max_disagreement,difference)
  pos=[r for r in rows if r['gt_pixels']];neg=[r for r in rows if not r['gt_pixels']];assert len(pos)==expected_pos
  tp=sum(r['tp']for r in rows);fp=sum(r['fp']for r in rows);fn=sum(r['fn']for r in rows)
  m={'global_iou':tp/max(1,tp+fp+fn),'global_dice':2*tp/max(1,2*tp+fp+fn),'coverage_mae_pp':float(np.mean([abs(r['pred_pixels']-r['gt_pixels'])/r['valid_pixels']*100 for r in rows])),
     'scene_tp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in pos),'scene_fp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in neg),
     'positive_macro_iou':float(np.mean([r['tp']/max(1,r['tp']+r['fp']+r['fn'])for r in pos])),
     'positive_coverage_mae_pp':float(np.mean([abs(r['pred_pixels']-r['gt_pixels'])/r['valid_pixels']*100 for r in pos]))}
  for key,value in m.items():
   if key in saved['summary']:assert abs(value-saved['summary'][key])<1e-10,(split,mode,key)
  stats[mode]=m
  if mode=='single_view':stats['max_reference_disagreement_fraction']=max_disagreement
 audit['splits'][split]=stats
choice='tta4'if audit['splits']['val']['tta4']['global_iou']>audit['splits']['val']['single_view']['global_iou']else 'single_view'
assert choice==audit['deployment_mode_selected_by_validation']
diagnostics=[]
for path in (dest/'results/diagnostic_logits').glob('*.npz'):
 with np.load(path)as npz:
  actual=npz['aligned_logits'].mean(axis=0);saved=npz['mean_logits']
  assert actual.shape==saved.shape
  error=float(np.max(np.abs(actual-saved)));assert error<1e-5
  diagnostics.append({'id':path.stem,'logit_mean_max_error':error})
assert {r['id']for r in diagnostics}=={'6598','6345'}
audit['diagnostic_logit_checks']=diagnostics
(out/'四视图推理核验.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))

plt.rcParams.update({'font.family':['Songti SC','Times New Roman'],'font.size':12,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#63766C','text.color':'#253C36','axes.labelcolor':'#253C36'})
fig,axes=plt.subplots(1,3,figsize=(13.7,4.5))
width=.32;x=np.arange(3);names=['80 幅验证','448 幅测试','370 幅额外核验']
negative_counts={'val':50,'test':399,'holdout':347}
for ax,metric,title,ylabel in zip(axes,['global_iou','coverage_mae_pp','scene_fp'],['(a) 空间分割','(b) 覆盖率误差','(c) 无受淹场景误报'],['IoU（%）','MAE（百分点）','误报率（%）']):
 for j,(mode,label,color,hatch)in enumerate([('single_view','单视图','#BCD0C5',None),('tta4','四视图平均','#AABFD0','///')]):
  values=[audit['splits'][split][mode][metric]*(100 if metric=='global_iou'else 100/negative_counts[split]if metric=='scene_fp'else 1)for split in ['val','test','holdout']]
  bars=ax.bar(x+(j-.5)*width,values,width,label=label,color=color,edgecolor='#657C70',lw=.8,hatch=hatch)
  for bar,value,split in zip(bars,values,['val','test','holdout']):
   label=f"{audit['splits'][split][mode]['scene_fp']}/{negative_counts[split]}"if metric=='scene_fp'else f'{value:.2f}'
   ax.text(bar.get_x()+bar.get_width()/2,bar.get_height(),label,ha='center',va='bottom',fontsize=9.5)
 ax.set(xticks=x,xticklabels=names,title=title,ylabel=ylabel)
 ax.grid(axis='y',alpha=.2,ls='--');ax.set_axisbelow(True);ax.set_ylim(0,ax.get_ylim()[1]*1.15)
 if metric=='global_iou':ax.axhline(50,color='#BEA162',lw=1,ls=':')
fig.legend(*axes[0].get_legend_handles_labels(),ncol=2,frameon=False,loc='upper center',bbox_to_anchor=(.5,1.04))
fig.text(.5,.015,'同一检查点、同一阈值；四视图增加推理次数，模型参数保持不变。',ha='center',fontsize=11)
fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'07_四视图推理对照.png',dpi=240,bbox_inches='tight');plt.close(fig)
print(json.dumps(audit,ensure_ascii=False))
