"""Scientific schematic of the frozen overnight protocol; no predicted results."""
from pathlib import Path
import json
import hashlib
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/TerraScope_夜间优化_20261016'
OUT.mkdir(exist_ok=True)
manifest = json.loads((HERE / 'manifest.json').read_text())
r = next(r for r in manifest if r['id'] == '6597')
assert r['split'] == 'train'
data = ROOT / 'work/finetune_formal_20261015/data/6597'
assert hashlib.sha256((data / 'RGB.jpg').read_bytes()).hexdigest() == r['rgb_sha256']
assert hashlib.sha256((data / 'labels.png').read_bytes()).hexdigest() == r['label_sha256']
rgb = np.array(Image.open(data / 'RGB.jpg').convert('RGB'))
y = np.array(Image.open(data / 'labels.png'))
assert rgb.shape[:2] == y.shape
mask = y == 3
overlay = rgb.copy()
overlay[mask] = (rgb[mask] * .25 + np.array([96, 166, 140]) * .75).astype('uint8')

plt.rcParams.update({'font.family': ['Songti SC', 'Times New Roman'], 'font.size': 12,
                     'axes.unicode_minus': False, 'text.color': '#253D36'})
fig = plt.figure(figsize=(16, 9), facecolor='white')
green = '#518875'; blue = '#658CA7'; ink = '#253D36'; gray = '#EEF2F0'; edge = '#A7B9AF'
fig.text(.035, .963, '从训练充分性到 IoU 导向优化', fontsize=24, fontweight='bold', va='top')
fig.text(.965, .956, 'TerraScope · 受淹道路分割', fontsize=14, ha='right', color=green)

def panel(rect, title, color):
    ax = fig.add_axes(rect); ax.set(xlim=(0,100), ylim=(0,100)); ax.axis('off')
    ax.add_patch(FancyBboxPatch((.3,.3),99.4,99.4,boxstyle='round,pad=0,rounding_size=2',
                              facecolor='white', edgecolor=edge, linewidth=1))
    ax.plot([3,3],[89,96],lw=3.2,color=color,solid_capstyle='round')
    ax.text(5,93,title,fontsize=16,fontweight='bold',va='center')
    return ax

def box(ax,x,y,w,h,title,subtitle='',color=green,fill='#EAF3ED',size=13):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.2,rounding_size=1.8',
                              facecolor=fill,edgecolor=color,linewidth=1.1))
    ax.text(x+w/2,y+h*.64 if subtitle else y+h/2,title,ha='center',va='center',fontsize=size,fontweight='bold')
    if subtitle:ax.text(x+w/2,y+h*.26,subtitle,ha='center',va='center',fontsize=10.5,color='#587168')

def arrow(ax,start,end,color='#6D8378',style='-',rad=0):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=13,
                                linewidth=1.25,color=color,linestyle=style,connectionstyle=f'arc3,rad={rad}'))

a = panel([.03,.51,.46,.38], '(a) 同一任务与训练数据', green)
for x,im,label in [(4,rgb,'RGB 影像'),(36,mask,'受淹道路标签'),(68,overlay,'同位置叠加')]:
    inset = a.inset_axes([x/100,.36,.28,.43])
    inset.imshow(im, cmap='gray', interpolation='nearest');inset.axis('off')
    a.text(x+14,32,label,ha='center',fontsize=12)
a.text(50,23,'“分割这幅航空影像中的受淹道路”',ha='center',fontsize=14,fontweight='bold')
a.text(50,14,'训练样本 6597 · 绿色为类别 3 的真实标签',ha='center',fontsize=11,color='#63796E')
a.text(50,6,'300 幅训练影像　｜　正负样本按 1∶1 交替抽样',ha='center',fontsize=11)

b = panel([.51,.51,.46,.38], '(b) 冻结主干，更新分割输出', blue)
box(b,5,63,28,19,'视觉编码器＋语言模型','影像与固定 [SEG] 提示',color=edge,fill=gray,size=12)
box(b,43,63,22,19,'文本投影层','可训练',color=green,size=13)
box(b,5,27,28,19,'SAM2 图像编码器','固定视觉特征',color=edge,fill=gray,size=12)
box(b,71,39,24,25,'SAM2 分割头','可训练',color=green,size=13)
arrow(b,(33,72.5),(42,72.5));arrow(b,(65,72.5),(82,65))
arrow(b,(33,36.5),(70,47));b.text(49,32,'多尺度特征',fontsize=10,ha='center',color='#63796E')
arrow(b,(83,39),(83,23));b.text(83,17,'道路掩膜',ha='center',fontsize=13,fontweight='bold')
b.text(5,15,'灰色：冻结　绿色：更新',fontsize=11,color='#63796E')
b.text(5,6,'共约 1,798 万个可训练参数',fontsize=11)

c = panel([.03,.065,.46,.39], '(c) 成对比较：损失改变，预算相同', green)
box(c,5,62,28,20,'BCE ＋ Dice','原损失 · 延长训练',color=green,fill='#E9F2EC')
box(c,5,27,28,20,'BCE ＋ Lovász','IoU 导向的替代损失',color=blue,fill='#EBF1F6')
for i,x in enumerate([44,64,84]):
    c.plot([x,x],[47,62],color='#B5C4BB',lw=1,ls='--')
    for y0,color,fill in [(72,green,'#E9F2EC'),(37,blue,'#EBF1F6')]:
        c.add_patch(Circle((x,y0),7.7,facecolor=fill,edgecolor=color,lw=1.2))
        c.text(x,y0,str(i+1),ha='center',va='center',fontsize=17,fontweight='bold',color=color)
    c.text(x,54.5,'同种子',ha='center',va='center',fontsize=10,color='#657A70')
arrow(c,(33,72),(35.5,72),green);arrow(c,(33,37),(35.5,37),blue)
c.text(63,18,'3 个种子 × 2 种损失 = 6 组训练',ha='center',fontsize=13,fontweight='bold')
c.text(50,7,'每组 4800 微步 / 1200 次更新 · 相同样本顺序、增强、学习率',ha='center',fontsize=11)

d = panel([.51,.065,.46,.39], '(d) 验证集选模型，测试集看效果', blue)
d.text(5,79,'验证节点',fontsize=11)
d.plot([26,92],[80,80],color='#A8BCAF',lw=1.4)
for j,step in enumerate([800,1600,2400,3200,4000,4800]):
    x=26+j*13.2;d.plot(x,80,'o',ms=5,color=blue);d.text(x,72,str(step),ha='center',fontsize=9.5)
d.plot([65.6,92],[65,65],color=green,lw=2);d.text(78.8,59,'后三个检查点再做权重平均',ha='center',fontsize=10,color=green)
box(d,4,25,28,23,'80 幅验证','选择单模型或平均权重',color=blue,fill='#EBF1F6',size=14)
box(d,38,25,25,23,'448 幅测试','固定阈值 · 全量评测',color=green,fill='#E9F2EC',size=14)
box(d,70,25,26,23,'370 幅核验','额外保留样本',color=green,fill='#F1F5E9',size=14)
arrow(d,(32,36.5),(37,36.5));arrow(d,(63,36.5),(69,36.5))
d.text(50,14,'同一模型分别评价两组影像，结果分开报告',ha='center',fontsize=11)
d.text(50,6,'空间 IoU　覆盖率误差　命中 / 误报　随机种子波动',ha='center',fontsize=11,fontweight='bold')
fig.savefig(OUT/'05_夜间优化实验设计.png',dpi=220)
fig.savefig(OUT/'05_夜间优化实验设计.svg')
print(OUT/'05_夜间优化实验设计.png')
