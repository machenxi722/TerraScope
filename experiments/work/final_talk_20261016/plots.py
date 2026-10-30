from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
R=Path.cwd();D=json.load(open(R/'work/final_talk_20261016/assets/data.json'))
plt.rcParams.update({'font.family':['Songti SC','Times New Roman'],'font.size':14,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#61746C','text.color':'#253C36','axes.labelcolor':'#253C36','xtick.color':'#61746C','ytick.color':'#61746C','axes.axisbelow':True})
fig,axs=plt.subplots(2,1,figsize=(6.3,4.45),gridspec_kw={'height_ratios':[1.25,1]},layout='constrained')
arms=D['night']['arms']; cols=['#568699','#BA8F50']; labs=['BCE + Dice','BCE + Lovasz']
for k,col,lab in zip(['long_bce_dice_seed20261017','long_bce_lovasz_seed20261017'],cols,labs):
 h=arms[k]['validation_history'];axs[0].plot([v['micro_step']/4 for v in h],[v['global_iou']*100 for v in h],marker='o',ms=4,color=col,lw=1.7,label=lab)
axs[0].set_ylabel('验证 IoU（%）');axs[0].set_xlabel('参数更新次数');axs[0].set_xticks([200,600,1000,1200]);axs[0].set_ylim(35,67);axs[0].grid(axis='y',color='#DDE6E1',linestyle='--',linewidth=.7);axs[0].legend(loc='lower right',fontsize=11,frameon=False,ncol=2)
for i,(kind,col,lab) in enumerate(zip(['long_bce_dice','long_bce_lovasz'],cols,labs)):
 vals=[arms[f'{kind}_seed{s}']['test']['global_iou']*100 for s in [20261015,20261016,20261017]]
 axs[1].plot([1,2,3],vals,marker='s' if i else 'o',ms=5,color=col,lw=1.4,label=lab)
 for x,y in zip([1,2,3],vals):axs[1].text(x+(.04 if i else -.04),y+(.8 if i else -2.2),f'{y:.2f}',ha='left' if i else 'right',fontsize=11,color=col)
axs[1].set_ylabel('测试 IoU（%）');axs[1].set_xticks([1,2,3],['种子 1','种子 2','种子 3']);axs[1].set_xlim(.6,3.45);axs[1].set_ylim(39,63);axs[1].grid(axis='y',color='#DDE6E1',linestyle='--',linewidth=.7)
fig.savefig(R/'work/final_talk_20261016/assets/training_choices.png',dpi=240,facecolor='white');plt.close(fig)
