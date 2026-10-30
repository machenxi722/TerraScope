from pathlib import Path
import numpy as np,json
from PIL import Image,ImageFilter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager
R=Path.cwd();O=R/'work/editorial_v2_20261016/assets';O.mkdir(exist_ok=True);A=R/'work/final_talk_20261016/assets';T=R/'work/night_20261016/tta_backup/results'
# Scientific raster transformations preserve the original array grid.
z=np.load(T/'diagnostic_logits/6598.npz');v=z['aligned_logits'][:,0,0]
for i,axes in enumerate([(),(1,),(0,),(0,1)]):
 b=v[i]>0;raw=np.flip(b,axes) if axes else b
 for tag,arr in [('aligned',b),('raw',raw)]:
  a=np.full((*arr.shape,3),247,np.uint8);a[arr]=[79,139,160];Image.fromarray(a).save(O/f'tta_{tag}_{i}.png')
# Use the same coordinate window for every comparison in each case.
boxes={'7461':(100,90,770,600),'7301':(60,100,655,590),'7986':(110,180,800,690)}
for sid,crop in boxes.items():
 for mode in ['rgb','baseline','tta4','gt','difference']:
  im=Image.open(A/f'{sid}_{mode}.png');im.crop(crop).save(O/f'{sid}_{mode}_detail.png')
# Pixel-based application measurements and class consistency.
sid='7301';lab=np.array(Image.open(R/f'work/finetune_formal_20261015/data/{sid}/labels.png'));valid=lab!=255;gt=lab==3
out={}
for mode in ['single_view','tta4']:
 p=np.array(Image.open(T/f'predictions/{mode}/test/{sid}.png'))>0
 tp=int((p&gt&valid).sum());fp=int((p&~gt&valid).sum());fn=int((~p&gt&valid).sum())
 out[mode]={'tp':tp,'fp':fp,'fn':fn,'pred_pixels':int((p&valid).sum()),'gt_pixels':int(gt.sum()),'valid_pixels':int(valid.sum()),'precision':tp/(tp+fp),'recall':tp/(tp+fn),'iou':tp/(tp+fp+fn),'coverage':float((p&valid).sum()/valid.sum()*100)}
# New per-image evidence for the additional set, based on every labeled positive image.
s=json.load(open(T/'single_view_holdout.json'));t=json.load(open(T/'tta4_holdout.json'));print('sample keys',s['per_image'][0])
a={x['id']:x for x in s['per_image']};b={x['id']:x for x in t['per_image']};ids=[i for i in a if a[i]['gt_pixels']>0];ids.sort(key=lambda i:a[i]['iou'])
fontManager.addfont(str(R/'work/journal_figures/fonts/SongtiSC-Regular.ttf'));fontManager.addfont(str(R/'work/journal_figures/fonts/SongtiSC-Bold.ttf'))
plt.rcParams.update({'font.family':['Songti SC','Times New Roman'],'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#657B76','axes.labelcolor':'#264A40','text.color':'#264A40','xtick.color':'#657B76','ytick.color':'#657B76','font.size':11,'axes.unicode_minus':False})
fig,ax=plt.subplots(figsize=(6.3,2.4));x=np.arange(len(ids));y1=np.array([a[i]['iou']*100 for i in ids]);y2=np.array([b[i]['iou']*100 for i in ids]);
for k in x:ax.plot([k,k],[y1[k],y2[k]],color='#ADBEB5',lw=1)
ax.plot(x,y1,'o',ms=4,color='#799EB3',label='单视图');ax.plot(x,y2,'D',ms=3.6,color='#538F79',label='四视图');ax.set_ylabel('逐景 IoU（%）');ax.set_xticks([0,5,10,15,22],['1','6','11','16','23']);ax.set_xlabel('23 幅受淹影像（按单视图 IoU 排序）');ax.set_ylim(-4,104);ax.grid(axis='y',color='#E4EBE7',ls='--',lw=.6);ax.legend(frameon=False,loc='upper left',ncol=2,fontsize=10);fig.subplots_adjust(left=.12,bottom=.25,right=.99,top=.97);fig.savefig(O/'holdout_per_image.png',dpi=240,transparent=True);plt.close(fig)
out['extra_positive_comparison']={'n':len(ids),'improved':int((y2>y1).sum()),'decreased':int((y2<y1).sum()),'same':int((y2==y1).sum())}
(O/'measurements.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
