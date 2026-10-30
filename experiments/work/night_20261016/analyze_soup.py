"""Independently reconstruct the chosen parameter average and audit every mask."""
from pathlib import Path
import argparse, hashlib, json, zipfile
import numpy as np
from PIL import Image
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('archive',type=Path);args=ap.parse_args()
dest=HERE/'soup_backup';dest.mkdir(exist_ok=True)
with zipfile.ZipFile(args.archive)as z:
 assert z.testzip()is None
 hashes=json.loads(z.read('result_sha256.json'))
 for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
 for name in z.namelist():assert (dest/name).resolve().is_relative_to(dest.resolve())
 z.extractall(dest)
for name,digest in json.loads((HERE/'soup_code_sha256.json').read_text()).items():
 assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==digest,name
report=json.loads((dest/'results/report.json').read_text());assert report['completed']
assert 'validation_choice_locked_at'in report
manifest=json.loads((dest/'manifest.json').read_text());assert len(manifest)==898
out=ROOT/'outputs/TerraScope_夜间优化_20261016'
assert (out/'核验与汇总.json').exists()and(out/'四视图推理核验.json').exists()
chosen=report['selected_soup_by_validation']
assert chosen==max(report['candidates'],key=lambda n:report['candidates'][n]['validation']['global_iou'])
members=report['candidates'][chosen]['members']
states=[]
for member in members:
 path=HERE/'backup/results'/f"{member['name']}_best_delta.pt"
 assert hashlib.sha256(path.read_bytes()).hexdigest()==member['sha256']
 states.append(torch.load(path,map_location='cpu',weights_only=True))
saved=torch.load(dest/'results/best_soup_weights.pt',map_location='cpu',weights_only=True)
assert all(set(s)==set(saved)for s in states)
# An independent float64 sum checks the server's online float32 averaging.
max_error=0.;parameter_count=0
for key,tensor in saved.items():
 total=torch.zeros_like(tensor,dtype=torch.float64)
 for state in states:
  assert state[key].shape==tensor.shape
  total.add_(state[key].double())
 expected=(total/len(states)).to(tensor.dtype)
 assert torch.allclose(tensor,expected,atol=1e-6,rtol=2e-6),key
 max_error=max(max_error,float((tensor-expected).abs().max()));parameter_count+=tensor.numel()
assert parameter_count==17981509
del states,saved,total,expected
audit={'archive_sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest(),'chosen_soup':chosen,'members':members,
       'averaged_parameters_verified':parameter_count,'max_parameter_average_error':max_error,'deployment_choice_by_validation':report['deployment_choice_by_validation'],'evaluations':{}}
tasks=[(name,'val',80,30)for name in report['candidates']]+[('selected_soup','test',448,49),('selected_soup','holdout',370,23)]
for name,split,n,npos in tasks:
 rows=[];selected=[r for r in manifest if r['split']==split];assert len(selected)==n
 folder=dest/'results/predictions'/name/split
 assert {p.stem for p in folder.glob('*.png')}=={r['id']for r in selected}
 source=json.loads((dest/'results'/f'{name}_{split}.json').read_text());reference={r['id']:r for r in source['per_image']}
 for row in selected:
  sid=row['id'];label=(HERE/'holdout/data'if split=='holdout'else ROOT/'work/finetune_formal_20261015/data')/sid/'labels.png'
  assert hashlib.sha256(label.read_bytes()).hexdigest()==row['label_sha256']
  y=np.array(Image.open(label));mask=np.array(Image.open(folder/f'{sid}.png'))
  assert mask.shape==y.shape and set(np.unique(mask)).issubset({0,255})
  p=mask>0;g=y==3;v=y!=255
  r={'id':sid,'tp':int((p&g&v).sum()),'fp':int((p&~g&v).sum()),'fn':int((~p&g&v).sum()),'valid_pixels':int(v.sum()),'pred_pixels':int((p&v).sum()),'gt_pixels':int((g&v).sum())}
  for key,value in r.items():assert reference[sid][key]==value,(name,split,sid,key)
  rows.append(r)
 tp=sum(r['tp']for r in rows);fp=sum(r['fp']for r in rows);fn=sum(r['fn']for r in rows)
 pos=[r for r in rows if r['gt_pixels']];neg=[r for r in rows if not r['gt_pixels']];assert len(pos)==npos
 metrics={'global_iou':tp/max(1,tp+fp+fn),'coverage_mae_pp':float(np.mean([abs(r['pred_pixels']-r['gt_pixels'])/r['valid_pixels']*100 for r in rows])),
          'positive_macro_iou':float(np.mean([r['tp']/max(1,r['tp']+r['fp']+r['fn'])for r in pos])),
          'scene_tp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in pos),'scene_fp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in neg)}
 for key,value in metrics.items():assert abs(value-source['summary'][key])<1e-10,(name,split,key)
 audit['evaluations'][f'{name}/{split}']=metrics
(out/'跨种子权重平均核验.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))

night=json.loads((HERE/'backup/results/report.json').read_text())
tta=json.loads((out/'四视图推理核验.json').read_text())
assert tta['checkpoint_name']==report['single_checkpoint_name']
plt.rcParams.update({'font.family':['Songti SC','Times New Roman'],'font.size':12,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#63766C','text.color':'#253C36','axes.labelcolor':'#253C36'})
fig,axes=plt.subplots(1,3,figsize=(13.8,4.7))
names=list(report['candidates']);short={'long_bce_dice':'Dice 三模型','long_bce_lovasz':'Lovász 三模型','all_six':'六模型平均'}
values=[report['candidates'][n]['validation']['global_iou']*100 for n in names]
bars=axes[0].barh(range(3),values,color=['#A4C4B1','#B5C8D4','#C7BED3'],edgecolor='#708579',lw=.7)
for bar,value in zip(bars,values):axes[0].text(value+.35,bar.get_y()+bar.get_height()/2,f'{value:.2f}',va='center',fontsize=10)
axes[0].set(yticks=range(3),yticklabels=[short[n]for n in names],xlabel='验证 IoU（%）',title='(a) 三种固定参数平均方案',xlim=(0,max(values+[report['single_validation_iou']*100])+7))
reference=report['single_validation_iou']*100
axes[0].axvline(reference,color='#987E9C',ls='--',lw=1)
axes[0].text(reference+1.4,2.35,f'最佳单模型 {reference:.2f}%',rotation=90,va='top',fontsize=10,color='#987E9C')
for ax,split,title in zip(axes[1:],['test','holdout'],['(b) 完整测试 · 448 幅','(c) 额外核验 · 370 幅']):
 single=tta['splits'][split]['single_view']['global_iou']*100
 tta4=tta['splits'][split]['tta4']['global_iou']*100
 soup=audit['evaluations'][f'selected_soup/{split}']['global_iou']*100
 bars=ax.bar(range(3),[single,tta4,soup],color=['#BCD0C5','#AABFD0','#C7BED3'],edgecolor='#708579',lw=.7)
 bars[1].set_hatch('///')
 for bar,value in zip(bars,[single,tta4,soup]):ax.text(bar.get_x()+bar.get_width()/2,value,f'{value:.2f}',ha='center',va='bottom',fontsize=11)
 ax.set(xticks=range(3),xticklabels=['单模型','四视图平均','参数平均'],ylabel='IoU（%）',title=title,ylim=(0,max(65,single,tta4,soup)*1.12));ax.axhline(50,color='#C1A267',ls=':',lw=1)
for ax in axes:ax.grid(axis='y',alpha=.18,ls='--');ax.set_axisbelow(True)
fig.text(.5,.015,'参数平均使用验证集选定的方案，部署时仍为单模型、单视图推理。',ha='center',fontsize=11)
fig.tight_layout(rect=(0,.045,1,1));fig.savefig(out/'08_跨种子参数平均对照.png',dpi=240,bbox_inches='tight');plt.close(fig)
print(json.dumps(audit,ensure_ascii=False))
