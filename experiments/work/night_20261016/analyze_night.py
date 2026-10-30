"""Audit the actual complete-test predictions, then draw Chinese result figures.

Usage: work/flood-env/bin/python work/night_20261016/analyze_night.py PATH_TO_BACKUP_ZIP
Only models with all 448 saved prediction masks are accepted.
"""
from pathlib import Path
import argparse, json, hashlib, zipfile, csv
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
LOCAL=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('archive',type=Path);args=ap.parse_args()
backup=LOCAL/'backup';backup.mkdir(exist_ok=True)
with zipfile.ZipFile(args.archive)as z:
 assert z.testzip()is None
 expected=json.loads(z.read('result_sha256.json'))
 for name,digest in expected.items():
  assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
 for member in z.infolist():
  target=(backup/member.filename).resolve()
  assert target.is_relative_to(backup.resolve()),member.filename
 z.extractall(backup)
code_hashes=json.loads((LOCAL/'code_sha256.json').read_text())
for filename,digest in code_hashes.items():
 assert hashlib.sha256((backup/filename).read_bytes()).hexdigest()==digest,filename
manifest=json.loads((backup/'manifest.json').read_text())
assert hashlib.sha256((backup/'manifest.json').read_bytes()).hexdigest()=='0a016c0b2d9f40064c62a72a18275177efc14944c24c42a53971982554aafde2'
test={r['id']:r for r in manifest if r['split']=='test'}
assert len(test)==448 and sum(bool(r['positive'])for r in test.values())==49
report=json.loads((backup/'results/report.json').read_text())
assert 'selection_locked_at'in report,'No evidence of locked validation choices'
arms={k:v for k,v in report['arms'].items()if v.get('test')is not None}
assert arms,'No completed test evaluation'
data=ROOT/'work/finetune_formal_20261015/data'
out=ROOT/'outputs/TerraScope_夜间优化_20261016';out.mkdir(exist_ok=True)
all_rows={};audit={'archive_sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest(),'member_hashes_verified':len(expected),'n_test':448,'n_positive':49,'complete_six_arms':report.get('completed',False),'methods':{}}

for name,arm in arms.items():
 pdir=backup/'results/predictions'/name/'test'
 assert {p.stem for p in pdir.glob('*.png')}==set(test),name
 recorded=json.loads((backup/'results'/f'{name}_test.json').read_text())
 saved={r['id']:r for r in recorded['per_image']};assert set(saved)==set(test)
 rows=[]
 for sid,row in test.items():
  label_path=data/sid/'labels.png'
  assert hashlib.sha256(label_path.read_bytes()).hexdigest()==row['label_sha256']
  y=np.array(Image.open(label_path));raw=np.array(Image.open(pdir/f'{sid}.png'))
  assert raw.shape==y.shape,(name,sid,raw.shape,y.shape)
  assert set(np.unique(raw)).issubset({0,255})
  pred=raw>0;gt=y==3;valid=y!=255
  rr={'id':sid,'tp':int((pred&gt&valid).sum()),'fp':int((pred&~gt&valid).sum()),'fn':int((~pred&gt&valid).sum()),'valid_pixels':int(valid.sum()),'pred_pixels':int((pred&valid).sum()),'gt_pixels':int((gt&valid).sum())}
  for key in rr:assert rr[key]==saved[sid][key],(name,sid,key)
  rows.append(rr)
 tp=sum(r['tp']for r in rows);fp=sum(r['fp']for r in rows);fn=sum(r['fn']for r in rows)
 positive=[r for r in rows if r['gt_pixels']>0];negative=[r for r in rows if r['gt_pixels']==0]
 assert len(positive)==49 and len(negative)==399
 metrics={'global_iou':tp/max(1,tp+fp+fn),'global_dice':2*tp/max(1,2*tp+fp+fn),'coverage_mae_pp':float(np.mean([abs(r['pred_pixels']-r['gt_pixels'])/r['valid_pixels']*100 for r in rows])),
 'scene_tp':sum(r['gt_pixels']>0 and r['pred_pixels']/r['valid_pixels']>=.01 for r in rows),'scene_fp':sum(r['gt_pixels']==0 and r['pred_pixels']/r['valid_pixels']>=.01 for r in rows),'pixel_precision':tp/max(1,tp+fp),'pixel_recall':tp/max(1,tp+fn),
 'positive_macro_iou':float(np.mean([r['tp']/max(1,r['tp']+r['fp']+r['fn']) for r in positive])),
 'positive_coverage_mae_pp':float(np.mean([abs(r['pred_pixels']-r['gt_pixels'])/r['valid_pixels']*100 for r in positive])),
 'negative_mean_prediction_pp':float(np.mean([r['pred_pixels']/r['valid_pixels']*100 for r in negative]))}
 for key,value in metrics.items():
  if key in arm['test']:assert abs(value-arm['test'][key])<1e-10,(name,key)
 audit['methods'][name]={'recomputed':metrics,'seed':arm['seed'],'kind':arm['kind'],'selected':arm['selected'],'best_val_global_iou':arm['best_val_global_iou']}
 all_rows[name]={r['id']:r for r in rows}
 print(name,json.dumps(metrics))

paired=[]
for seed in report['protocol']['seeds']:
 a='long_bce_dice_seed'+str(seed);b='long_bce_lovasz_seed'+str(seed)
 if a in arms and b in arms:
  # Equal random draws and geometric/color transforms are ensured by seeded code;
  # sample IDs must independently match the recorded training trace.
  ta=json.loads((backup/'results'/f'{a}_training.json').read_text())['trace']
  tb=json.loads((backup/'results'/f'{b}_training.json').read_text())['trace']
  assert [x['sample_id']for x in ta]==[x['sample_id']for x in tb]
  assert len(ta)==len(tb)==4800
  paired.append({'seed':seed,'iou_delta_pp':100*(arms[b]['test']['global_iou']-arms[a]['test']['global_iou'])})
audit['paired_seeds']=paired
audit['uploaded_code_matches_frozen_local_copy']=True
audit['selected_by_validation']=max(arms,key=lambda n:arms[n]['best_val_global_iou'])
audit['method_summary']={}
for kind in report['protocol']['arms']:
 names=[n for n,v in arms.items()if v['kind']==kind];values=np.array([arms[n]['test']['global_iou']*100 for n in names])
 if not len(values):continue
 audit['method_summary'][kind]={'n_seeds':len(values),'mean_iou_pct':float(values.mean()),'sample_sd_pp':float(values.std(ddof=1))if len(values)>1 else None,'min_iou_pct':float(values.min()),'max_iou_pct':float(values.max()),'all_seeds_above_50':bool((values>50).all())}
(out/'核验与汇总.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
with(out/'实验结果.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.writer(f);w.writerow(['方法','种子','验证IoU百分比','测试IoU百分比','覆盖率MAE百分点','命中场景','误报场景','检查点选择'])
 for name,v in arms.items():w.writerow([v['kind'],v['seed'],100*v['best_val_global_iou'],100*v['test']['global_iou'],v['test']['coverage_mae_pp'],v['test']['scene_tp'],v['test']['scene_fp'],v['selected']])

plt.rcParams.update({'font.family':['Songti SC','Times New Roman'],'font.size':13,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#63766C','text.color':'#253C36','axes.labelcolor':'#253C36','xtick.color':'#61746C','ytick.color':'#61746C','savefig.facecolor':'white'})
colors={'long_bce_dice':'#568B78','long_bce_lovasz':'#658BAA'}
labels={'long_bce_dice':'延长训练 · BCE＋Dice','long_bce_lovasz':'延长训练 · BCE＋Lovász'}
fig,axes=plt.subplots(1,2,figsize=(13,4.2),sharey=True)
for ax,kind in zip(axes,report['protocol']['arms']):
 for i,(name,v)in enumerate((n,v)for n,v in arms.items()if v['kind']==kind):
  h=v['validation_history'];ax.plot([r['micro_step']/4 for r in h],[r['global_iou']*100 for r in h],marker=['o','s','D'][i],ls=['-','--',':'][i],lw=1.8,color=colors[kind],alpha=1-i*.15,label=f'种子 {i+1}')
  ax.scatter([1400],[v['late_average_val']['global_iou']*100],marker=['o','s','D'][i],s=65,facecolors='white',edgecolors=colors[kind],zorder=4)
 ax.set(title=labels[kind],xlabel='参数更新次数',xticks=[200,400,600,800,1000,1200,1400],xticklabels=['200','400','600','800','1000','1200','权重平均'])
 ax.axvline(1300,color='#D3DDD7',lw=.8,ls=':')
 ax.grid(axis='y',alpha=.2,ls='--');ax.legend(frameon=False,ncol=3,fontsize=10)
axes[0].set_ylabel('验证集 IoU（%）');fig.tight_layout();fig.savefig(out/'01_验证曲线与权重平均.png',dpi=240);plt.close(fig)

old_head=json.loads((ROOT/'work/finetune_backups_20261015/formal/results/report.json').read_text())['arms']['head_seed20261015']['test']
fig,axes=plt.subplots(1,3,figsize=(13.5,4.6))
for index,metric in enumerate(['global_iou','coverage_mae_pp','scene_fp']):
 ax=axes[index]
 for j,kind in enumerate(report['protocol']['arms']):
  values=[v['test'][metric]*(100 if metric=='global_iou'else 1)for v in arms.values()if v['kind']==kind]
  if not values:continue
  x=np.linspace(j-.08,j+.08,len(values));ax.scatter(x,values,s=55,color=colors[kind],edgecolors='white',linewidth=.7,zorder=4)
  ax.hlines(np.mean(values),j-.19,j+.19,color=colors[kind],lw=3,zorder=3)
 for k,p in enumerate(paired):
  a=arms['long_bce_dice_seed'+str(p['seed'])]['test'][metric];b=arms['long_bce_lovasz_seed'+str(p['seed'])]['test'][metric]
  offset=np.linspace(-.08,.08,len(paired))[k]
  factor=100 if metric=='global_iou'else 1;ax.plot([offset,1+offset],[a*factor,b*factor],color='#ABB6B0',lw=.8,zorder=1)
 ax.axhline(old_head[metric]*(100 if metric=='global_iou'else 1),color='#877B91',ls=':',lw=1.3,label='原 1600 步分割头')
 ax.set_xticks([0,1],['BCE＋Dice','BCE＋Lovász']);ax.set_xlim(-.4,1.4);ax.grid(axis='y',alpha=.2,ls='--')
 if metric=='global_iou':ax.axhline(50,color='#C4A25E',ls='--',lw=1.2);ax.set_title('(a) 完整测试集 IoU');ax.set_ylabel('IoU（%）')
 elif metric=='coverage_mae_pp':ax.set_title('(b) 覆盖率绝对误差');ax.set_ylabel('MAE（百分点）')
 else:ax.set_title('(c) 无受淹道路影像的误报');ax.set_ylabel('误报幅数 / 399')
axes[0].legend(frameon=False,fontsize=10,loc='best')
fig.text(.5,.01,'每个点代表一个随机种子；短横线表示均值；连线连接相同种子的两种损失。',ha='center',fontsize=11)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(out/'02_配对种子与完整测试结果.png',dpi=240);plt.close(fig)

# Reuse previously fixed representative IDs; do not cherry-pick new wins.
prior=json.loads((ROOT/'work/finetune_ppt_20261015/assets/metrics.json').read_text())
case_ids=prior['case_ids']+[prior['diagnostic_case'],prior['negative_case']]
winner=audit['selected_by_validation'];control='head_seed20261015'
fig,axes=plt.subplots(len(case_ids),4,figsize=(12,len(case_ids)*2.25))
palette={'tp':np.array([88,161,129]),'fn':np.array([227,185,101]),'fp':np.array([199,124,143])}
for i,sid in enumerate(case_ids):
 rgb=np.array(Image.open(data/sid/'RGB.jpg').convert('RGB'));y=np.array(Image.open(data/sid/'labels.png'));gt=y==3;valid=y!=255
 old=np.array(Image.open(ROOT/'work/finetune_backups_20261015/formal/results/predictions'/control/'test'/f'{sid}.png'))>0
 new=np.array(Image.open(backup/'results/predictions'/winner/'test'/f'{sid}.png'))>0
 ref=rgb.copy();ref[gt]=(ref[gt]*.4+palette['tp']*.6).astype('uint8')
 def diff(pred):
  image=(rgb*.35+255*.65).astype('uint8');image[pred&gt&valid]=palette['tp'];image[~pred&gt&valid]=palette['fn'];image[pred&~gt&valid]=palette['fp'];return image
 for j,im in enumerate([rgb,ref,diff(old),diff(new)]):axes[i,j].imshow(im);axes[i,j].set_xticks([]);axes[i,j].set_yticks([]);axes[i,j].spines[['left','bottom']].set_visible(False)
 axes[i,0].set_ylabel(sid,rotation=0,labelpad=25)
for j,title in enumerate(['原始 RGB','受淹道路标签','原 1600 步分割头','本轮验证集选中模型']):axes[0,j].set_title(title)
fig.text(.5,.01,'绿色：命中　　金色：遗漏　　粉色：多检',ha='center');fig.tight_layout(rect=(0,.025,1,1));fig.savefig(out/'03_固定案例空间对比.png',dpi=220);plt.close(fig)

# Show every positive test image and the false-positive tail on all negatives.
# The selected model is already locked by validation above.
old_details=json.loads((ROOT/'work/finetune_backups_20261015/formal/results/head_seed20261015_test.json').read_text())
old_by_id={r['id']:r for r in old_details['per_image']};assert set(old_by_id)==set(test)
new_by_id=all_rows[winner];positive_ids=[sid for sid,r in new_by_id.items()if r['gt_pixels']>0]
negative_ids=[sid for sid,r in new_by_id.items()if r['gt_pixels']==0]
for sid in test:
 assert old_by_id[sid]['gt_pixels']==new_by_id[sid]['gt_pixels']
 assert old_by_id[sid]['valid_pixels']==new_by_id[sid]['valid_pixels']
fig,axes=plt.subplots(1,3,figsize=(14.3,4.8))
old_iou=np.array([old_by_id[s]['tp']/max(1,old_by_id[s]['tp']+old_by_id[s]['fp']+old_by_id[s]['fn'])*100 for s in positive_ids])
new_iou=np.array([new_by_id[s]['tp']/max(1,new_by_id[s]['tp']+new_by_id[s]['fp']+new_by_id[s]['fn'])*100 for s in positive_ids])
delta=new_iou-old_iou
point_colors=np.where(delta>1e-10,'#5C967C',np.where(delta < -1e-10,'#BF8A9A','#A4B3AB'))
axes[0].scatter(old_iou,new_iou,c=point_colors,s=38,edgecolors='white',linewidth=.6,alpha=.9,zorder=3)
axes[0].plot([0,100],[0,100],ls='--',lw=1,color='#8E9E95')
axes[0].set(xlim=(-3,103),ylim=(-3,103),xlabel='原分割头 IoU（%）',ylabel='本轮选中模型 IoU（%）',title='(a) 49 幅受淹场景逐幅对照')
axes[0].text(.04,.96,f'改善 {sum(delta>1e-10)} 幅  /  下降 {sum(delta < -1e-10)} 幅',transform=axes[0].transAxes,va='top',fontsize=11)
for values,label,color,ls in [(old_by_id,'原 1600 步分割头','#9B8CA7','--'),(new_by_id,'本轮验证集选中模型','#568B78','-')]:
 fractions=np.sort([values[s]['pred_pixels']/values[s]['valid_pixels']*100 for s in negative_ids])
 thresholds=np.unique(np.r_[0,fractions[fractions>0],100])
 exceedance=np.array([np.mean(fractions>threshold)*100 for threshold in thresholds])
 axes[1].step(thresholds,exceedance,where='post',label=label,color=color,ls=ls,lw=1.8)
axes[1].set_xscale('symlog',linthresh=.1,linscale=.6)
axes[1].axvline(1,color='#C1A267',ls=':',lw=1.2)
axes[1].set(xlabel='误检覆盖率阈值（%）',ylabel='超过阈值的影像比例（%）',title='(b) 399 幅无受淹场景的误检尾部',xlim=(0,100),xticks=[0,.1,1,10,100],xticklabels=['0','0.1','1','10','100'])
axes[1].set_ylim(0,axes[1].get_ylim()[1]*1.1)
axes[1].legend(frameon=False,fontsize=9,loc='upper right')
axes[1].text(1,.05,' 1% 筛查阈值',color='#9E824B',fontsize=9,rotation=90,va='bottom')
positions=np.arange(2);width=.32
strata=[positive_ids,negative_ids]
for j,(values,label,color,hatch)in enumerate([(old_by_id,'原分割头','#C7BED0','///'),(new_by_id,'本轮选中模型','#9FC6B1',None)]):
 vals=[np.mean([abs(values[s]['pred_pixels']-values[s]['gt_pixels'])/values[s]['valid_pixels']*100 for s in ids])for ids in strata]
 bars=axes[2].bar(positions+(j-.5)*width,vals,width,color=color,edgecolor='#6A7F72',lw=.7,hatch=hatch,label=label)
 for bar,value in zip(bars,vals):axes[2].text(bar.get_x()+bar.get_width()/2,bar.get_height(),f'{value:.2f}',ha='center',va='bottom',fontsize=11)
axes[2].set(xticks=positions,xticklabels=['含受淹道路\n49 幅','无受淹道路\n399 幅'],ylabel='覆盖率 MAE（百分点）',title='(c) 分开统计，保留实际难度')
axes[2].set_ylim(0,axes[2].get_ylim()[1]*1.15);axes[2].legend(frameon=False,fontsize=9)
for ax in axes:ax.grid(axis='y',ls='--',alpha=.18);ax.set_axisbelow(True)
fig.tight_layout();fig.savefig(out/'06_受淹场景与误报分解.png',dpi=240);plt.close(fig)
audit['positive_scene_change']={'improved':int(sum(delta>1e-10)),'worsened':int(sum(delta < -1e-10)),'unchanged':int(sum(np.abs(delta)<=1e-10)),'mean_delta_pp':float(delta.mean()),'chosen_by':'validation_global_iou'}
(out/'核验与汇总.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print('OUTPUT',out,'SELECTED_BY_VAL',winner)
