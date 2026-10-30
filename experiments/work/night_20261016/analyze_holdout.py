"""Verify every extra-holdout mask and compare the same selected checkpoints."""
from pathlib import Path
import argparse,json,hashlib,zipfile
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
LOCAL=Path(__file__).resolve().parent;ROOT=LOCAL.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('archive',type=Path);args=ap.parse_args()
dest=LOCAL/'holdout_backup';dest.mkdir(exist_ok=True)
with zipfile.ZipFile(args.archive)as z:
 assert z.testzip()is None
 hashes=json.loads(z.read('result_sha256.json'))
 for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
 for name in z.namelist():assert (dest/name).resolve().is_relative_to(dest.resolve())
 z.extractall(dest)
for name,digest in json.loads((LOCAL/'holdout_code_sha256.json').read_text()).items():assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==digest,name
report=json.loads((dest/'results/report.json').read_text());assert report['completed']
manifest=json.loads((dest/'manifest.json').read_text());assert len(manifest)==370
assert not {r['id']for r in manifest}&{r['id']for r in json.loads((LOCAL/'manifest.json').read_text())}
out=ROOT/'outputs/TerraScope_夜间优化_20261016';out.mkdir(exist_ok=True)
records={}
for name,method in report['arms'].items():
 folder=dest/'results/predictions'/name/'holdout';assert {p.stem for p in folder.glob('*.png')}=={r['id']for r in manifest}
 original=json.loads((dest/'results'/f'{name}_holdout.json').read_text());expected={r['id']:r for r in original['per_image']}
 rows=[]
 for row in manifest:
  sid=row['id'];label=LOCAL/'holdout/data'/sid/'labels.png';assert hashlib.sha256(label.read_bytes()).hexdigest()==row['label_sha256']
  y=np.array(Image.open(label));mask=np.array(Image.open(folder/f'{sid}.png'));assert mask.shape==y.shape;assert set(np.unique(mask)).issubset({0,255})
  p=mask>0;g=y==3;v=y!=255
  rec={'id':sid,'tp':int((p&g&v).sum()),'fp':int((p&~g&v).sum()),'fn':int((~p&g&v).sum()),'valid_pixels':int(v.sum()),'pred_pixels':int((p&v).sum()),'gt_pixels':int((g&v).sum())}
  for key,value in rec.items():assert expected[sid][key]==value,(name,sid,key)
  rows.append(rec)
 tp=sum(r['tp']for r in rows);fp=sum(r['fp']for r in rows);fn=sum(r['fn']for r in rows)
 positive=[r for r in rows if r['gt_pixels']];negative=[r for r in rows if not r['gt_pixels']];assert len(positive)==23 and len(negative)==347
 metrics={'global_iou':tp/max(1,tp+fp+fn),'global_dice':2*tp/max(1,2*tp+fp+fn),'coverage_mae_pp':float(np.mean([abs(r['pred_pixels']-r['gt_pixels'])/r['valid_pixels']*100 for r in rows])),
 'positive_macro_iou':float(np.mean([r['tp']/max(1,r['tp']+r['fp']+r['fn'])for r in positive])),
 'positive_coverage_mae_pp':float(np.mean([abs(r['pred_pixels']-r['gt_pixels'])/r['valid_pixels']*100 for r in positive])),
 'negative_mean_prediction_pp':float(np.mean([r['pred_pixels']/r['valid_pixels']*100 for r in negative])),
 'scene_tp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in positive),'scene_fp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in negative)}
 for key,value in metrics.items():
  if key in method['holdout']:assert abs(value-method['holdout'][key])<1e-10,(name,key)
 records[name]={'checkpoint_name':method['checkpoint_name'],'validation_iou':method['best_original_80_val_global_iou'],'recomputed':metrics}
 print(name,json.dumps(metrics))
audit={'archive_sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest(),'files_verified':len(hashes),'mask_count_verified':370*4,'n_images':370,'n_positive':23,'original_test_overlap':0,'methods':records}
(out/'额外370幅核验结果.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
old=json.loads((ROOT/'work/finetune_backups_20261015/formal/results/report.json').read_text())['arms']
new=json.loads((LOCAL/'backup/results/report.json').read_text())['arms']
order=['original_head','original_lora','long_bce_dice','long_bce_lovasz']
labels=['原分割头微调','原语言 LoRA','延长训练','IoU 导向损失']
colors=['#A7B9AE','#B4ACC7','#7EAA95','#82A7BC']
plt.rcParams.update({'font.family':['Songti SC','Times New Roman'],'font.size':12,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#63766C','text.color':'#253C36','axes.labelcolor':'#253C36'})
fig,axes=plt.subplots(1,2,figsize=(12.5,4.3))
x=np.arange(4);width=.32
for index,metric in enumerate(['global_iou','coverage_mae_pp']):
 ax=axes[index]
 for split,offset,hatch in [('test',-width/2,None),('holdout',width/2,'///')]:
  values=[]
  for name in order:
   r=records[name];checkpoint=r['checkpoint_name']
   v=(old.get(checkpoint)or new.get(checkpoint))['test'][metric]if split=='test'else r['recomputed'][metric]
   values.append(v*(100 if metric=='global_iou'else 1))
  bars=ax.bar(x+offset,values,width,color=colors,hatch=hatch,edgecolor='#62766F',linewidth=.7)
  for bar,value in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height(),f'{value:.1f}'if metric=='global_iou'else f'{value:.2f}',ha='center',va='bottom',fontsize=10)
 ax.set_xticks(x,labels);ax.grid(axis='y',ls='--',alpha=.2);ax.set_axisbelow(True)
 if metric=='global_iou':ax.set_title('(a) 受淹道路分割');ax.set_ylabel('IoU（%）');ax.set_ylim(0,max(70,ax.get_ylim()[1]*1.1));ax.axhline(50,color='#C1A267',ls='--',lw=1)
 else:ax.set_title('(b) 覆盖率估算');ax.set_ylabel('绝对误差（百分点）');ax.set_ylim(0,ax.get_ylim()[1]*1.15)
fig.legend([Patch(facecolor='white',edgecolor='#62766F'),Patch(facecolor='white',edgecolor='#62766F',hatch='///')],['原完整测试集 · 448 幅','额外核验集 · 370 幅'],ncol=2,frameon=False,loc='upper center',bbox_to_anchor=(.5,1.03))
fig.tight_layout(rect=(0,0,1,.94));fig.savefig(out/'04_额外样本核验.png',dpi=240,bbox_inches='tight');plt.close(fig)
print('OUTPUT',out)
