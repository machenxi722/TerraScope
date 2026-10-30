from pathlib import Path
import json, ast, shutil, re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle
from matplotlib.colors import to_rgb

ROOT=Path.cwd()
OUT=ROOT/'outputs/TerraScope_全部图件_清新论文版'
OLD=ROOT/'outputs/TerraScope_全部图件_课堂汇报版'
P=ROOT/'work/paper_figures'
for d in ['PNG','SVG','PDF','复现代码','本地素材']:(OUT/d).mkdir(parents=True,exist_ok=True)
INK='#303B40'; MUTED='#6D777B'; EDGE='#687579'; GRID='#E5E9E9'
BLUE='#B8D2DC'; GREEN='#BCD8C5'; LAV='#C8BEDC'; GOLD='#F3D4A0'; ROSE='#DDB3B8'; GREY='#DFE5E6'
DBLUE='#507C91'; DGREEN='#547C65'; DLAV='#7A689B'; DGOLD='#A67C3F'; DROSE='#A56372'
COLORS=[GREY,BLUE,GREEN]; ROUTES=['A  InternVL3','B  TerraScope','C  掩膜核算']
PAL=[GREY,LAV,BLUE,GOLD,GREEN]

def read(p):return json.loads((ROOT/p).read_text())
MAIN=read('outputs/TerraScope_ABC主实验/summary.json')
REV=read('outputs/TerraScope_洪灾水体/confirmation_review_simulation.json')
FLOOD=read('outputs/TerraScope_洪灾水体/flood_ABC_summary.json')['confirmation']
FNET=read('work/floodnet/simple_evaluation_exposure.json')
ABC={r['id']:r for r in read('outputs/TerraScope_洪灾水体/confirmation_ABC_complete_scores.json')}
WUHAN=read('outputs/武汉洪灾应用试验/summary.json')
PRIM=[r for r in WUHAN['regions'] if r['role']=='primary']
SCALE=read('outputs/武汉洪灾应用试验/局部放大检查/summary.json')['rows']

def txt(f,x,y,s,size=18,color=INK,bold=False,ha='left',va='center'):
    return f.text(x,y,s,fontsize=size,color=color,weight='bold' if bold else 'normal',ha=ha,va=va,linespacing=1.5)
def base(title,sub=''):
    f=plt.figure(figsize=(16,9),facecolor='white')
    txt(f,.05,.94,title,27,bold=True)
    if sub:txt(f,.05,.887,sub,16,color=MUTED)
    return f
def box(f,x,y,w,h,color='white',edge=GRID,lw=1.0,r=.012,z=-1):
    b=FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={r}',transform=f.transFigure,facecolor=color,edgecolor=edge,lw=lw,zorder=z)
    f.add_artist(b);return b
def strip(f,x,y,w,h,s,c=BLUE,size=17,bold=False):
    box(f,x,y,w,h,c,edge='none',r=.012)
    txt(f,x+.012,y+h/2,s,size,bold=bold)
def panel(f,rect,title=None):
    a=f.add_axes(rect)
    if title:a.set_title(title,loc='left',fontweight='bold',fontsize=20,pad=18,color=INK)
    return a
def clean(a,grid='y'):
    a.spines[['top','right']].set_visible(False)
    for k in ['left','bottom']:a.spines[k].set_color(INK);a.spines[k].set_linewidth(1.2)
    a.tick_params(length=5,width=1.2,color=INK,pad=7,labelsize=17)
    a.set_axisbelow(True)
    if grid:a.grid(axis=grid,color=GRID,lw=.85,ls=(0,(3,3)))
    a.yaxis.label.set_size(18);a.xaxis.label.set_size(18)
def legend(f,labels,colors,y=.823,ncol=None):
    f.legend(handles=[Patch(facecolor=c,edgecolor=EDGE,lw=.8,label=l) for l,c in zip(labels,colors)],loc='center',bbox_to_anchor=(.5,y),ncol=ncol or len(labels),frameon=False,fontsize=16,handlelength=1.6,columnspacing=2.0)
def bars(a,vals,labels,colors,ylim=None,fmt='.0f',suffix='',inside=True,delta=False):
    bs=a.bar(np.arange(len(vals)),vals,color=colors,width=.58,edgecolor=EDGE,lw=1.05,zorder=3)
    a.set_xticks(np.arange(len(vals)),labels)
    if ylim:a.set_ylim(*ylim)
    ymax=a.get_ylim()[1]
    for i,(b,v) in enumerate(zip(bs,vals)):
        pos=v-.16*ymax if inside and v>.34*ymax else v+.025*ymax
        a.text(b.get_x()+b.get_width()/2,pos,format(v,fmt)+suffix,ha='center',va='center' if inside and v>.34*ymax else 'bottom',fontsize=25,color=INK,fontweight='bold')
        if delta and v>.34*ymax:a.text(i,pos-.13*ymax,f'{v-vals[0]:+.1f}' if i else '基准',ha='center',va='center',fontsize=18,color=INK)
    clean(a);return bs
def takeaway(f,s,color=GREEN):strip(f,.05,.045,.9,.075,s,color,18)
def layers(f,rect,source,title,size=17):
    a=f.add_axes(rect)
    for im in source.images:a.imshow(im.get_array(),cmap=im.get_cmap(),vmin=im.norm.vmin,vmax=im.norm.vmax,interpolation='nearest')
    a.axis('off');a.set_title(title,fontsize=size,color=INK,pad=11,fontweight='bold')
    return a
def acc(route,task='all'):
    return next(r['accuracy_percent'] for r in MAIN['summary'] if r['split']=='test' and r['route']==route and r['task']==task)

def statistical(name):
    if name=='04_主实验100题_ABC对照':
        f=base('TerraScope 回答与掩膜核算的对照','固定 100 题，比较选择题正确率与改答效果')
        legend(f,ROUTES,COLORS)
        a=panel(f,[.09,.24,.43,.5],'(a) 选择题正确率')
        bars(a,[acc(k) for k in 'ABC'],['A','B','C'],COLORS,(0,100),suffix='%');a.set_ylabel('正确率（%）');a.set_yticks([0,25,50,75,100])
        b=panel(f,[.64,.24,.29,.5],'(b) B 改为 C 后的答案变化')
        paired=next(r for r in MAIN['paired'] if r['split']=='test' and r['left']=='B' and r['right']=='C')
        bars(b,[paired['right_only_correct'],paired['left_only_correct']],['改对','改错'],[GREEN,ROSE],(0,40));b.set_ylabel('题目数')
        takeaway(f,'掩膜核算改对 10 题，同时改错 32 题。先核验证据，再决定是否替换答案。')
        return f
    if name=='05_主实验100题_分任务表现':
        f=base('两类面积任务的表现','每类任务各 50 题，柱内第二行为相对 A 的正确率变化（百分点）')
        legend(f,ROUTES,COLORS)
        for i,(task,title) in enumerate([('coverage_percentage','(a) 覆盖率问题'),('absolute_area','(b) 绝对面积问题')]):
            a=panel(f,[.09+i*.47,.22,.37,.52],title);vals=[acc(k,task) for k in 'ABC']
            bars(a,vals,['A','B','C'],COLORS,(0,100),suffix='%',delta=True);a.set_yticks([0,25,50,75,100]);a.set_ylabel('正确率（%）')
        takeaway(f,'TerraScope 在两类任务上均优于通用模型，掩膜核算在覆盖率题中保留了更多正确答案。')
        return f
    if name=='06_追加200题_一致性核验':
        f=base('答案与掩膜的一致性核验','追加 200 题，检查格式、掩膜与数值答案是否一致')
        a=panel(f,[.16,.27,.46,.47],'(a) 核验分组中的正确与错误')
        gs=[('全部 200 题',140,60),('保留 99 题',83,16),('标记 101 题',57,44)]
        for i,(label,c,e) in enumerate(gs):
            y=2-i;a.barh(y,c,color=BLUE,edgecolor=EDGE,lw=.85,height=.55);a.barh(y,e,left=c,color=ROSE,edgecolor=EDGE,lw=.85,height=.55)
            a.text(c/2,y,str(c),ha='center',va='center',fontsize=23,weight='bold');a.text(c+e/2,y,str(e),ha='center',va='center',fontsize=21,weight='bold')
        a.set_yticks([2,1,0],[g[0] for g in gs]);a.set_xlim(0,210);a.set_xlabel('题目数');clean(a,'x')
        for i,(v,t,c) in enumerate([('83.8%','保留部分正确率',BLUE),('49.5%','题目保留比例',GREEN),('73.3%','错误检出比例',GOLD)]):
            box(f,.7,.60-i*.185,.23,.135,c,edge='none');txt(f,.815,.688-i*.185,v,32,bold=True,ha='center');txt(f,.815,.637-i*.185,t,16,ha='center')
        legend(f,['原答正确','原答错误'],[BLUE,ROSE],y=.18)
        takeaway(f,'一致性检查把 44 / 60 个错误标记为待复核，保留部分的正确率为 83 / 99。')
        return f
    if name=='08_洪灾12幅_覆盖率ABC':
        f=base('洪灾影像的水体覆盖率核算','12 幅完整标注影像，覆盖率平均绝对误差（MAE），越低越好')
        legend(f,ROUTES,COLORS)
        a=panel(f,[.1,.25,.51,.49],'(a) 三条路线的覆盖率误差');v=[FLOOD['paired_mae_pp'][k] for k in 'ABC']
        bars(a,v,['A','B','C'],COLORS,(0,12),fmt='.2f',inside=False);a.set_ylabel('MAE（百分点）');a.set_yticks([0,3,6,9,12])
        a.axhline(FLOOD['zero_baseline_mae_pp'],color=MUTED,lw=1.3,ls=(0,(4,3)));a.text(2.35,10.55,'恒报 0% 基线  10.29',ha='right',fontsize=14,color=MUTED)
        ratio=(v[1]-v[2])/v[1]*100
        box(f,.7,.48,.235,.23,GREEN,edge='none');txt(f,.8175,.628,f'降低 {ratio:.1f}%',30,bold=True,ha='center');txt(f,.8175,.555,'相对 TerraScope 原答的 MAE',15,ha='center')
        txt(f,.7,.345,'4.08 → 1.72',28,color=DGREEN,bold=True);txt(f,.7,.275,'同一掩膜，重新核算覆盖率',17)
        takeaway(f,'在洪灾覆盖率任务中，确定性像元核算能减少生成答案中的数值误差。')
        return f
    if name in ['10_洪灾71幅_调查名单命中','11_洪灾71幅_复核后覆盖率误差']:
        hits=name.startswith('10_');metric='top_k_hits' if hits else 'mae_pp';res=REV['results']
        keys=['no_review','random_review','prompt_disagreement','decision_boundary','spectral_disagreement']
        labels=['不复核','随机复核','提示词分歧','入选边界\n我们的扩展','光谱分歧']
        vals=[res[k][metric]['mean'] if k=='random_review' else res[k][metric] for k in keys]
        f=base('有限复核预算下的调查名单命中' if hits else '复核后水体覆盖率的数值误差','71 幅影像，Top 24 调查名单，固定复核预算 16 幅，理想人工复核模拟')
        a=panel(f,[.1,.24,.83,.54])
        bs=bars(a,vals,labels,PAL,(0,26 if hits else 10.5),fmt='.1f' if hits else '.2f',inside=True)
        if hits:
            for i,t in enumerate(a.texts):
                if i!=1:t.set_text(str(int(vals[i])))
        rr=res['random_review'][metric];a.errorbar(1,rr['mean'],yerr=[[rr['mean']-rr['p025']],[rr['p975']-rr['mean']]],color=EDGE,fmt='none',capsize=6,lw=1.5,zorder=4)
        # Avoid placing the random-review value inside its range line.
        a.texts[1].set_position((1,rr['p025']-(2.1 if hits else 1.0)))
        a.set_ylabel('参考 Top 24 命中数' if hits else '覆盖率 MAE（百分点）');a.set_yticks([0,6,12,18,24] if hits else [0,2,4,6,8,10])
        a.axhline(vals[0],color=MUTED,lw=1.2,ls=(0,(4,3)),zorder=2)
        takeaway(f,'入选边界与提示词分歧均命中 18 / 24，相比不复核多找回 4 个区域。' if hits else '入选边界 MAE 为 5.02，提示词分歧 MAE 为 4.68。名单命中与数值误差反映不同表现。',GOLD)
        txt(f,.91,.145,'随机复核：10,000 次分配的 2.5%—97.5% 范围',13,color=MUTED,ha='right')
        return f
    if name=='14_能力边界_分割质量':
        sm=read('outputs/TerraScope_洪灾水体/confirmation_summary.json')
        vals=[sm['p1']['positive_mean_iou']*100,REV['spectral_mean_iou']*100]
        f=base('水体分割质量与后续核算','71 幅可评价影像中的有水样本，比较平均 IoU')
        a=panel(f,[.12,.25,.43,.52],'(a) 水体分割 IoU');bars(a,vals,['TerraScope\nRGB','MNDWI\n绿色 + SWIR'],[BLUE,GREY],(0,65),fmt='.1f',suffix='%');a.set_ylabel('平均 IoU（%）');a.set_yticks([0,20,40,60])
        box(f,.64,.30,.30,.44,'#F3F6F4',edge='none');txt(f,.66,.655,'分割影响核算',23,bold=True);txt(f,.66,.53,'掩膜决定数值计算的输入\n漏分水体需要进一步复核',19);txt(f,.66,.38,'证据核验与复核预算\n共同支持调查筛查',19,color=DGREEN)
        takeaway(f,'分割精度是后续面积计算和名单筛选的基础。')
        return f
    if name=='15_全部71幅_预测与参考散点':
        f=base('模型覆盖率与人工参考的对照','71 幅影像，JRC 常年水体以外的水体覆盖率')
        r=REV['rows'];x=np.array([z['reference_pct'] for z in r]);y=np.array([z['p'][0] for z in r]);sel=set(REV['results']['decision_boundary']['reviewed_ids'])
        a=panel(f,[.09,.28,.47,.48],'(a) 覆盖率对应关系')
        a.scatter(x,y,c=[GOLD if z['id'] in sel else BLUE for z in r],s=75,alpha=.95,edgecolors=EDGE,linewidths=.65)
        a.plot([0,100],[0,100],color=MUTED,lw=1.2,ls=(0,(4,3)));a.set(xlim=(-2,102),ylim=(-2,102),xlabel='人工参考（%）',ylabel='模型掩膜核算（%）');a.set_aspect('equal');clean(a,'both')
        b=panel(f,[.67,.31,.26,.4],'(b) 绝对误差分布');err=np.abs(x-y);v=np.histogram(err,[0,5,10,20,np.inf])[0]
        bars(b,v,['0–5','5–10','10–20','≥20'],[GREEN,BLUE,LAV,ROSE],(0,max(v)*1.25),inside=False);b.set_xlabel('误差（百分点）');b.set_ylabel('影像数')
        legend(f,['本轮未复核','入选边界选择复核'],[BLUE,GOLD],y=.16)
        takeaway(f,'覆盖率偏差既包含漏估也包含高估。入选边界策略优先检查可能改变名单的样本。')
        return f
    if name=='01_留出样本道路筛查':
        f=base('洪灾道路调查筛查的应用结果','FloodNet 留出 24 张影像，12 张道路受淹、12 张未受淹，阈值为道路覆水 10%')
        rr=sorted(FNET['rows'],key=lambda r:r.get('road_water_share',-1),reverse=True);s=FNET['summary']
        a=panel(f,[.08,.27,.57,.47],'(a) 按模型道路覆水比例排序')
        vals=[r.get('road_water_share',0)*100 for r in rr]
        a.bar(range(24),vals,color=[BLUE if r['true_priority'] else GOLD for r in rr],edgecolor=EDGE,lw=.55,width=.8)
        a.axhline(10,color=DROSE,lw=1.4,ls=(0,(4,3)));a.text(23,13,'10% 筛查阈值',fontsize=13,ha='right',color=DROSE)
        a.set_xticks(range(24),[r['id'] for r in rr],rotation=60);a.tick_params(axis='x',labelsize=11);a.set_ylim(0,100);a.set_yticks([0,25,50,75,100]);a.set_ylabel('道路覆水（%）');clean(a);a.tick_params(axis='x',labelsize=11)
        b=panel(f,[.735,.30,.19,.40],'(b) 场景筛查结果')
        mat=np.array([[s['TN'],s['FP']],[s['FN'],s['TP']]])
        b.imshow(np.array([[.25,.55],[.55,.25]]),cmap=plt.matplotlib.colors.ListedColormap([GREEN,ROSE]),vmin=.2,vmax=.6)
        for (i,j),v in np.ndenumerate(mat):b.text(j,i,str(v),ha='center',va='center',fontsize=32,weight='bold')
        b.set_xticks([0,1],['未受淹','受淹']);b.set_yticks([0,1],['未受淹','受淹']);b.set_xlabel('模型筛查');b.set_ylabel('人工参考');b.tick_params(length=0,labelsize=15)
        for spine in b.spines.values():spine.set_visible(False)
        legend(f,['参考道路受淹','参考道路未受淹'],[BLUE,GOLD],y=.17)
        takeaway(f,'14 张进入优先核查清单，其中 11 张确有道路受淹，漏检 1 张、误报 3 张。')
        return f
    if name in ['19_武汉_模型与光谱交叉检查','20_武汉_局部放大敏感性']:
        scale=name.startswith('20_')
        f=base('武汉水面变化的尺度检查' if scale else '武汉水面变化的模型与光谱比较','两个主要区域，2016 年 6 月 29 日至 7 月 9 日，共同有效范围内的面积净变化')
        labels=['整幅推理 P1','局部放大拼接','MNDWI 参照'] if scale else ['TerraScope P1','TerraScope P2','MNDWI 参照']
        colors=[BLUE,GOLD,GREEN] if scale else [BLUE,LAV,GREEN];legend(f,labels,colors)
        for i,r in enumerate(PRIM):
            a=panel(f,[.09+i*.47,.24,.37,.49],f'({"ab"[i]}) {r["chip"]}')
            vv=[r['model']['p1']['net_km2'], next(z['net_km2'] for z in SCALE if z['chip']==r['chip'] and z['variant']=='p1') if scale else r['model']['p2']['net_km2'],r['spectral_reference']['0']['net_km2']]
            bars(a,vv,['整幅','放大拼接','光谱参照'] if scale else ['P1','P2','光谱参照'],colors,(0,5),fmt='.2f',inside=True);a.set_ylabel('水体净变化（km²）');a.set_yticks([0,1,2,3,4,5])
            if not scale:
                lo=vv[2]-min(r['spectral_reference'][k]['net_km2'] for k in ['-0.1','0','0.1']);hi=max(r['spectral_reference'][k]['net_km2'] for k in ['-0.1','0','0.1'])-vv[2]
                a.errorbar(2,vv[2],yerr=[[lo],[hi]],fmt='none',color=EDGE,lw=1.2,capsize=5,zorder=4)
                a.texts[2].set_position((2,vv[2]+hi+.12));a.texts[2].set_va('bottom')
        if not scale:txt(f,.94,.15,'MNDWI 线段：阈值 −0.1、0、0.1 对应的变化范围',13,color=MUTED,ha='right')
        takeaway(f,'局部放大后，R3C1 净变化由 3.39 降至 2.45 km²，R3C2 由 4.13 降至 3.16 km²。' if scale else '两个区域的模型与光谱方法均显示水面扩张，TerraScope 估计的扩张幅度更大。')
        return f
    return None

def qualitative(old,name):
    if name=='07_真实案例_核算有效与失效':
        f=base('掩膜核算的两种结果','同样的数值核算方法，在不同分割质量下产生不同效果')
        for i,id in enumerate(['Ghana_406026','Paraguay_232281']):
            y=.48-i*.35;col=GREEN if i==0 else ROSE;box(f,.045,y,.91,.32,'white',edge=EDGE)
            txt(f,.062,y+.294,f'({"ab"[i]}) {id}',18,bold=True)
            for j,t in enumerate(['原始影像','TerraScope 水体','人工水体标注']):layers(f,[.058+j*.182,y+.026,.163,.203],old.axes[i*3+j],t,14)
            r=ABC[id];strip(f,.62,y+.204,.313,.062,'问题：水体覆盖率是多少？',BLUE,16)
            strip(f,.62,y+.114,.313,.076,f'原答 {r["B"]:.2f}%   核算 {r["C"]:.2f}%\n人工参考 {r["gt"]:.2f}%',col,16)
            txt(f,.63,y+.055,'核算纠正生成数字' if i==0 else '过分割导致核算偏大',17,color=DGREEN if i==0 else DROSE,bold=True)
        return f
    if name in ['12_真实案例_分歧触发复核','13_真实案例_低分歧仍会出错']:
        good=name.startswith('12_');id='India_747992' if good else 'India_952728';r=next(z for z in REV['rows'] if z['id']==id)
        f=base('提示词分歧触发复核的案例' if good else '低分歧预测中的漏检案例',id+'，同一影像的模型预测与人工参考')
        n=4 if good else 3;w=.21 if good else .28;gap=.022;start=.05
        titles=['原始影像','提示词 P1','提示词 P2','人工参考'] if good else ['原始影像','两次预测均为空','人工参考水体']
        for j,t in enumerate(titles):
            x=start+j*(w+gap);box(f,x,.36,w,.45,'white',edge=EDGE)
            layers(f,[x+.01,.38,w-.02,.37],old.axes[j],t,17)
        strip(f,.05,.252,.9,.072,'问题：该区域是否应进入优先调查名单？',BLUE,18)
        desc=f'P1 {r["p"][0]:.2f}%   P2 {r["p"][1]:.2f}%   人工参考 {r["reference_pct"]:.2f}%'
        strip(f,.05,.15,.9,.075,desc,GREEN if good else ROSE,22,True)
        takeaway(f,'两种提示改变入选状态，触发复核后找回调查名单中的遗漏。' if good else '两次预测一致，却同时漏掉水体。低分歧样本仍需补充证据。',GOLD)
        txt(f,.94,.343,'灰色区域：无有效标注',12,color=MUTED,ha='right')
        return f
    if '应用案例_' in name:
        id=name.rsplit('_',1)[-1];r=next(z for z in FNET['rows'] if z['id']==id)
        good=r['pred_priority'] and r['true_priority']
        f=base(f'洪灾道路核查案例 {id}', '哈维飓风灾后航拍，影像、模型水面与道路建筑标签的空间对照')
        titles=['(a) 原始航拍影像','(b) 模型水面与道路覆水','(c) 人工道路与建筑标注']
        for j,t in enumerate(titles):
            x=.05+j*.307;box(f,x,.365,.288,.45,'white',edge=EDGE);layers(f,[x+.008,.38,.272,.37],old.axes[j],t,16)
        strip(f,.05,.27,.9,.062,'问题：哪些道路覆水位置值得优先现场核查？',BLUE,18)
        from PIL import Image
        lab=np.asarray(Image.open(ROOT/'work/floodnet/raw'/(id+'_lab.png')))
        road=np.isin(lab,[3,4]);build=np.isin(lab,[1,2]);rf=(lab==3).sum()/max(road.sum(),1)*100;bf=(lab==1).sum()/max(build.sum(),1)*100
        for j,(t,v,c) in enumerate([('模型道路覆水',r['road_water_share']*100,BLUE),('参考道路受淹',rf,LAV),('参考受淹建筑轮廓',bf,GOLD)]):
            x=.05+j*.307;box(f,x,.135,.288,.11,c,edge='none');txt(f,x+.014,.19,t,16);txt(f,x+.269,.19,f'{v:.1f}%',25,bold=True,ha='right')
        takeaway(f,'水面与道路相交，形成可定位的优先核查线索。' if good else '邻近积水被扩展到道路，产生误报，需要人工排除。',GREEN if good else ROSE)
        txt(f,.94,.344,'蓝：模型水面   紫：道路覆水 / 受淹道路   杏：受淹建筑   白：道路轮廓',12,color=MUTED,ha='right')
        return f
    if name.startswith('18_'):
        chip=name.split('_')[1];r=next(z for z in PRIM if z['chip']==chip);v=r['model']['p1']
        f=base(f'武汉 {chip} 的两期水面变化',f'2016 年 6 月 29 日与 7 月 9 日，共同有效范围 {r["valid_km2"]:.2f} km²')
        for j,t in enumerate(['(a) 6 月 29 日前期影像','(b) 7 月 9 日灾时影像','(c) 模型水面变化']):
            x=.05+j*.307;box(f,x,.36,.288,.46,'white',edge=EDGE);layers(f,[x+.009,.375,.27,.38],old.axes[j],t,16)
        strip(f,.05,.26,.9,.064,'问题：同一地区的水面范围发生了什么变化？',BLUE,18)
        strip(f,.05,.155,.9,.08,f'覆盖率 {v["before_pct"]:.1f}% → {v["after_pct"]:.1f}%        预测净增加 {v["net_km2"]:.2f} km²',GREEN,24,True)
        legend(f,['两期均有水','新增候选','减少候选','无效像元'],[BLUE,GOLD,ROSE,GREY],y=.09)
        return f
    if name=='21_武汉_前期水面尺度检查':
        f=base('同一影像的不同观察尺度','武汉 R3C1，2016 年 6 月 29 日，固定提示 P1')
        for j,t in enumerate(['(a) 原始影像','(b) 整幅推理','(c) 局部放大后拼接']):
            x=.05+j*.307;box(f,x,.36,.288,.46,'white',edge=EDGE);layers(f,[x+.009,.375,.27,.38],old.axes[j],t,16)
        strip(f,.05,.26,.9,.065,'问题：同一影像放大观察后，识别的水面范围是否稳定？',BLUE,18)
        strip(f,.05,.153,.9,.085,'共同有效范围内覆盖率        整幅 5.87%        局部放大 13.17%',GOLD,23,True)
        takeaway(f,'放大观察改变了水面分割，尺度检查为人工复核提供更多线索。')
        return f
    return None

def restyle(old,name):
    # The georeferenced Wuhan overview keeps its original map geometry.
    if name=='17_武汉_日期与质量筛查':
        for t in old.texts:
            if t.get_position()[1]<.08:t.set_visible(False)
            t.set_color(INK)
        for a in old.axes:
            for t in a.texts:t.set_fontfamily(['Times New Roman','Songti SC'])
        return old
    if name=='05_从像素证据到道路核查':
        f=base('水面识别与道路调查的应用流程','模型像素证据与已知道路底图结合，输出有位置的核查线索')
        blocks=[('01  提取水面','TerraScope','RGB 航拍影像\n输出水面掩膜',BLUE),('02  道路覆水核算','空间相交','水面掩膜 ∩ 道路底图\n覆水比例 = 相交面积 / 道路面积',GREEN),('03  组织核查清单','调查筛查','覆水比例 ≥ 10%\n进入优先核查清单',GOLD)]
        for j,(t,method,b,c) in enumerate(blocks):
            x=.05+j*.315;box(f,x,.30,.27,.47,'white',edge=EDGE);strip(f,x,.68,.27,.09,t,c,20,True);txt(f,x+.135,.565,method,27,bold=True,ha='center');txt(f,x+.135,.445,b,17,ha='center')
            if j<2:txt(f,x+.289,.535,'→',30,color=MUTED,ha='center')
        takeaway(f,'根据模型覆水位置生成调查清单，再用人工受淹标签检查命中和误报。')
        return f
    return old

def save(old,name):
    f=statistical(name)
    if f is None:f=qualitative(old,name)
    if f is None:f=restyle(old,name)
    for ext in ['png','svg','pdf']:f.savefig(OUT/ext.upper()/(name+'.'+ext),dpi=200)
    if f is not old:plt.close(old)
    plt.close(f)
    print('Rebuilt',name,flush=True)

def run():
    import sys
    sys.path.insert(0,str(ROOT/'work/journal_figures'))
    from classroom_style import transform
    from matplotlib import font_manager as fm
    for p in (ROOT/'work/journal_figures/fonts').glob('*.ttf'):fm.fontManager.addfont(str(p))
    for n in ['Times New Roman.ttf','Times New Roman Bold.ttf']:fm.fontManager.addfont('/System/Library/Fonts/Supplemental/'+n)
    fontstyle="plt.rcParams.update({'font.family':['Times New Roman','Songti SC'],'font.size':17,'axes.unicode_minus':False,'svg.fonttype':'path','pdf.fonttype':42,'mathtext.fontset':'stix'})"
    repl={'#16324F':INK,'#273847':INK,'#2469A0':DBLUE,'#337EB0':DBLUE,'#07897E':DGREEN,'#D57732':DGOLD,'#C94E67':DLAV,'#9DA9B4':MUTED,'#708496':MUTED,'#8293A3':MUTED,'#E9EDF1':GRID,'#F0F4F7':'#F2F5F4'}
    for key,rel in [('base','work/ppt_refresh/build_figures.py'),('floodnet','work/floodnet/build_results.py'),('wuhan','work/wuhan_flood/figures.py')]:
        src=ROOT/rel;code=src.read_text()
        code=re.sub(r"font=FontProperties\(fname='/System/Library/Fonts/STHeiti Medium.ttc'\).*?plt\.rcParams\.update\(\{.*?\}\)",fontstyle,code,flags=re.S)
        for a,b in repl.items():code=code.replace(a,b)
        code=transform(code)
        tree=ast.parse(code)
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name=='save':
                args=[ast.Name(a.arg,ast.Load()) for a in node.args.args[:2]]
                node.body=[ast.Expr(ast.Call(ast.Name('paper_save',ast.Load()),args,[]))]
        ast.fix_missing_locations(tree)
        exec(compile(tree,str(src),'exec'),{'__file__':str(src),'__name__':'__main__','paper_save':save})
    entries=json.loads((OLD/'图件目录.json').read_text())
    # Rename through a staging area because old and new indices overlap.
    for ext in ['PNG','SVG','PDF']:
        staged=[]
        for e in entries:
            src=OUT/ext/(e['old']+'.'+ext.lower())
            if src.exists():
                tmp=P/('stage_'+ext+'_'+e['name']+'.'+ext.lower());shutil.move(src,tmp);staged.append((tmp,OUT/ext/(e['name']+'.'+ext.lower())))
        for a,b in staged:shutil.move(a,b)
    # Remaining four flow diagrams keep their established semantics and use the same palette.
    svgmap={
        '#16324F':INK,'#273847':INK,'#2469A0':DBLUE,'#07897E':DGREEN,'#D57732':DGOLD,'#C94E67':DLAV,
        '#9DA9B4':MUTED,'#EAF2F8':'#E7F0F3','#E6F4F1':'#E9F2EB','#FFF0E2':'#FCF2DF','#F3F5F7':'#F2F5F4',
        '#526678':MUTED,'#65727D':MUTED,'#CBD5E1':GRID,'#F0F4F7':'#F2F5F4'}
    for e in entries:
        if e['source']=='base' and int(e['old'][:2]) in [1,2,9,16]:
            s=(OLD/'SVG'/(e['name']+'.svg')).read_text()
            for a,b in svgmap.items():s=s.replace(a,b)
            (OUT/'SVG'/(e['name']+'.svg')).write_text(s)
    (OUT/'图件目录.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2))
    # Unused companion view generated by the upstream source is excluded from the final set.
    for ext in ['PNG','SVG','PDF']:
        for f in (OUT/ext).glob('18_R3C2_*'):f.unlink()
    shutil.copy2(__file__,OUT/'复现代码/paper_style.py')
    (OUT/'配色与排版.txt').write_text('中文宋体，英文与数字 Times New Roman。\n雾蓝 #B8D2DC，鼠尾草绿 #BCD8C5，淡紫 #C8BEDC，杏黄 #F3D4A0，柔粉 #DDB3B8，浅灰 #DFE5E6。\nA 通用模型：浅灰；B TerraScope：雾蓝；C 掩膜核算：鼠尾草绿。\n统计图采用共享图例、紧凑子图、柱内数值、轻虚线网格。案例图采用原图、预测、参考对齐排版，分层展示问题与结论。\n')

if __name__=='__main__':run()
