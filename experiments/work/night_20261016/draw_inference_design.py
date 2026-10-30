"""Draw the two fixed inference candidates, without inventing prediction masks."""
from pathlib import Path
import hashlib, json
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
OUT=ROOT/'outputs/TerraScope_夜间优化_20261016'
row=next(r for r in json.loads((HERE/'manifest.json').read_text()) if r['id']=='6598')
path=ROOT/'work/finetune_formal_20261015/data/6598/RGB.jpg'
assert hashlib.sha256(path.read_bytes()).hexdigest()==row['rgb_sha256']
rgb=np.array(Image.open(path).convert('RGB'))
plt.rcParams.update({'font.family':['Songti SC','Times New Roman'],'font.size':12,'text.color':'#253D36','mathtext.fontset':'stix'})
fig=plt.figure(figsize=(16,8.6),facecolor='white')
green='#518875';blue='#658CA7';edge='#A7B9AF'
fig.text(.035,.96,'同一组模型的两种推理优化',fontsize=25,fontweight='bold',va='top')
fig.text(.965,.954,'TerraScope · 候选方法示意',fontsize=14,color=green,ha='right')

def panel(rect,title,color):
 ax=fig.add_axes(rect);ax.set(xlim=(0,100),ylim=(0,100));ax.axis('off')
 ax.add_patch(FancyBboxPatch((.3,.3),99.4,99.4,boxstyle='round,pad=0,rounding_size=2',fc='white',ec=edge,lw=1))
 ax.plot([3,3],[90,96],lw=3,color=color,solid_capstyle='round');ax.text(5,93,title,va='center',fontsize=17,fontweight='bold')
 return ax
def box(ax,x,y,w,h,title,fill='#EAF3ED',color=green,size=12):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.2,rounding_size=1.7',fc=fill,ec=color,lw=1))
 ax.text(x+w/2,y+h/2,title,ha='center',va='center',fontsize=size)
def arrow(ax,start,end,color='#7E9588'):
 ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=12,lw=1.15,color=color))

a=panel([.03,.20,.46,.66],'(a) 四视图：在输出空间平均',blue)
views=[rgb,rgb[:,::-1],rgb[::-1],rgb[::-1,::-1]]
labels=['原图','水平翻转','垂直翻转','双向翻转']
for x,im,label in zip([4,28,52,76],views,labels):
 ia=a.inset_axes([x/100,.66,.20,.18]);ia.imshow(im);ia.axis('off')
 a.text(x+10,62,label,ha='center',fontsize=11)
 arrow(a,(x+10,58),(x+10,53))
 box(a,x,42,20,10,'同一模型',fill='#EBF1F6',color=blue,size=11)
 arrow(a,(x+10,42),(x+10,36))
 a.text(x+10,32,'还原坐标',ha='center',fontsize=11,color=blue)
 a.plot([x+10,x+10],[28,24],color=edge,lw=1)
a.plot([14,86],[24,24],color=edge,lw=1);arrow(a,(50,24),(50,20))
box(a,12,7,76,12,'对齐后的 logits 求均值 → 固定阈值 → 掩膜',fill='#EBF1F6',color=blue,size=13)

b=panel([.51,.20,.46,.66],'(b) 跨种子平均：在参数空间平均',green)
b.text(50,82,'同一初始模型 · 相同可训练层',ha='center',fontsize=13,fontweight='bold')
for y,label,color,fill in [(66,'Dice',green,'#EAF3ED'),(50,'Lovász',blue,'#EBF1F6')]:
 b.text(5,y+5,label,va='center',fontsize=12,color=color)
 for x,seed in zip([30,52,74],[1,2,3]):box(b,x,y,17,10,f'种子 {seed}',fill=fill,color=color,size=11)
b.text(50,43,'只平均分割头与文本投影层的参数',ha='center',fontsize=11,color='#63796E')
arrow(b,(50,39),(50,36))
for x,label in [(4,'3 个 Dice'),(37,'3 个 Lovász'),(70,'全部 6 个')]:
 box(b,x,23,26,12,label,size=12)
b.text(50,14.5,r'$\overline{\theta}=\frac{1}{K}\sum_{k=1}^{K}\theta_k$',ha='center',va='center',fontsize=18)
b.text(50,4.5,'验证集选一个方案 → 单模型、单视图推理',ha='center',fontsize=12)

ax=fig.add_axes([.03,.045,.94,.11]);ax.set(xlim=(0,100),ylim=(0,100));ax.axis('off')
box(ax,.2,5,99.5,90,'80 幅验证集统一选型：原单模型 / 四视图 / 参数平均\n448 幅测试与额外 370 幅分别评测；两条优化路线不叠加使用',fill='#F3F6F1',color=edge,size=14)
fig.savefig(OUT/'09_推理优化方法示意.png',dpi=220)
fig.savefig(OUT/'09_推理优化方法示意.svg')
print(OUT/'09_推理优化方法示意.png')
