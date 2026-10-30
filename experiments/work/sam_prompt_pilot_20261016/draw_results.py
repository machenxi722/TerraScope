"""Plot measured paired pilot curves, with no invented results."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P = Path(__file__).resolve().parent
O = P.parents[1]/'outputs/TerraScope_SAM2空间提示小实验_20261016'
R = P/'backup/results'
report = json.loads((R/'report.json').read_text())
assert report['completed']
traces = {n:json.loads((R/f'{n}_training.json').read_text())
          for n in ['continued_control','dense_prompt']}
plt.rcParams.update({'font.family':['Songti SC','Times New Roman'], 'font.size':12,
    'axes.unicode_minus':False, 'axes.spines.top':False,'axes.spines.right':False,
    'text.color':'#273D36','axes.labelcolor':'#273D36','xtick.color':'#46594F',
    'ytick.color':'#46594F','axes.edgecolor':'#7C8F85','savefig.facecolor':'white'})
fig, axes = plt.subplots(1,2,figsize=(13,4.8),gridspec_kw={'width_ratios':[1.18,1]})
colors=['#6E91A5','#639B82']
labels=['原分割头继续训练','加入自动空间提示']
for ax in axes:
    ax.set_axisbelow(True)
    ax.grid(axis='y',ls=(0,(3,3)),lw=.65,color='#D4DED8')
for (name,t),color,label,marker in zip(traces.items(),colors,labels,['s','o']):
    xs=[r['micro_step'] for r in t['validation']]
    ys=[r['global_iou']*100 for r in t['validation']]
    axes[0].plot(xs,ys,color=color,marker=marker,lw=2,ms=6,label=label)
    axes[0].annotate(f'{ys[-1]:.2f}',(xs[-1],ys[-1]),xytext=(7,6 if name=='dense_prompt' else -12),
                     textcoords='offset points',color=color,fontsize=11)
axes[0].set(title='(a) 相同预算下的验证曲线',xlabel='新增训练微步数',ylabel='验证集 IoU（%）')
axes[0].set_xticks([0,400,800,1200]);axes[0].set_xlim(-35,1380)
axes[0].legend(frameon=False,loc='lower right',fontsize=11)
initial=report['initial_validation']['global_iou']*100
ctrl=report['arms']['continued_control']['validation']['global_iou']*100
dense=report['arms']['dense_prompt']['validation']['global_iou']*100
disabled=report['arms']['dense_prompt']['disable_prompt_validation']['global_iou']*100
vals=[initial,ctrl,dense,disabled]
bars=axes[1].bar(range(4),vals,color=['#D8E2DD',colors[0],colors[1],'#D9C6A0'],
                 edgecolor='#64776C',linewidth=.8,width=.62,hatch=['','//','..',''])
for b,v in zip(bars,vals):
    axes[1].text(b.get_x()+b.get_width()/2,v+1.0,f'{v:.2f}',ha='center',fontsize=12,fontweight='bold')
axes[1].set_xticks(range(4),['原最佳\n权重','继续训练\n所选权重','空间提示\n所选权重','同一权重\n关闭提示'])
axes[1].set(title='(b) 保留各组最佳权重后的表现',ylabel='验证集 IoU（%）',ylim=(0,max(vals)+10))
fig.suptitle('SAM2 自动空间提示：配对小实验',fontsize=19,fontweight='bold',y=.99)
fig.text(.5,.01,'300 幅训练 · 80 幅验证 · 每组新增 1,200 微步 / 300 次更新 · 初始权重可保留',
         ha='center',fontsize=11,color='#62776A')
fig.subplots_adjust(left=.065,right=.98,top=.84,bottom=.21,wspace=.28)
fig.savefig(O/'配对验证结果.png',dpi=220)
fig.savefig(O/'配对验证结果.svg')
print(O/'配对验证结果.png')
