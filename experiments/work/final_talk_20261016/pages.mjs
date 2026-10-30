import fs from 'node:fs/promises';import path from 'node:path';
import {design,C} from './design.mjs';import {paper} from '../alignment_revision/diagram_utils.mjs';
export async function pages(root){
const A=path.join(root,'work/final_talk_20261016/assets'),D=JSON.parse(await fs.readFile(path.join(A,'data.json'),'utf8'));
const d=design(),{sh,t,box,band,end,label,line,img,bar}=d;
const P={blue:'#DBEBF3',sage:'#DDEADB',gold:'#F7E6C6',lav:'#E8E1F3',rose:'#F0DCE0',ink:'#263944',edge:'#71858C',db:'#436F8E',dg:'#558467',orange:'#B97841',purple:'#8C76A7'};
const pic=(id,k)=>path.join(A,`${id}_${k}.png`);
function head(s,tx,x,y,w){t(s,tx,x,y,w,34,24,C.green,true);line(s,x,y+39,w);}
function txt(s,tx,x,y,w,h,size=22,bold=false,col=C.ink,align='left'){return paper(s).text(tx,x,y,w,h,size,bold,align,col);}
function arrow(s,pts,col=P.ink,dash=false){paper(s).arrow(pts,col,dash);}
function block(s,tx,x,y,w,h,fill=P.blue,col=P.ink,size=22){box(s,x,y,w,h,fill,P.edge);txt(s,tx,x+8,y+3,w-16,h-6,size,true,col,'center');}
function region(s,title,x,y,w,h,fill='white',edge=P.edge){const z=box(s,x,y,w,h,fill,edge);z.line={fill:edge,width:1.1,style:'dash'};txt(s,title,x+16,y+8,w-32,29,23,true,edge);return z;}
function badge(s,num,tx,x,y,w,fill){sh(s,'ellipse',x,y,32,32,fill);txt(s,num,x,y,32,32,22,true,'white','center');txt(s,tx,x+43,y,w-43,32,25,true);}
function tokens(s,x,y,n,col){for(let i=0;i<n;i++)box(s,x+i*24,y,18,25,col,col+'-25');}
function tile(s,tx,val,x,y,w,fill){box(s,x,y,w,90,fill,'none');txt(s,val,x+12,y+6,w-24,48,37,true,C.green,'center');txt(s,tx,x+8,y+56,w-16,27,20,false,C.ink,'center');}
async function background(s){
head(s,'洪灾现场：水面、道路与遮挡同时出现',45,147,675);
await img(s,pic('7301','rgb'),45,199,675,452);
const rows=[['人工逐张勾绘','目标清楚，但影像增多后处理负担大',P.blue],['光谱水体指数','依赖对应波段，普通 RGB 航拍缺少 SWIR',P.gold],['从水面到道路','还需理解道路语义与空间连接关系',P.lav]];
for(let i=0;i<3;i++){let y=153+i*132;block(s,rows[i][0],762,y,462,42,rows[i][2],P.ink,24);txt(s,rows[i][1],773,y+52,440,55,22);}
block(s,'本项目目标',762,558,132,55,P.sage,P.dg,23);txt(s,'RGB ＋ 语言提示\n直接定位受淹道路',918,551,310,70,26,true,C.green,'center');
end(s,'从“图上有没有水”，推进到“哪些道路需要进一步核查”。');
}
async function capability(s){
const sc=path.join(root,'outputs/TerraScope_洪灾对齐修正版_20261015/逐景证据/evaluation/7571');
region(s,'(a) 输入影像与问题',40,164,374,453,'white',P.db);
await img(s,path.join(sc,'RGB.png'),58,216,338,227);
block(s,'影像中水面覆盖了多大比例？',57,467,340,63,P.blue,P.ink,23);
txt(s,'自然语言指定目标',70,558,315,33,23,true,P.db,'center');
region(s,'(b) 模型回答与分割',447,164,374,453,'white',P.dg);
await img(s,path.join(sc,'P1.png'),465,216,338,227);
block(s,'原始文字回答：约 16%',464,467,340,63,P.sage,P.ink,24);
txt(s,'同时保留像素级水面掩膜',467,558,334,33,23,true,P.dg,'center');
region(s,'(c) 走向道路任务',854,164,383,453,'white',P.orange);
await img(s,pic('7301','gt'),873,216,344,227);
block(s,'任务目标：受淹道路',872,467,346,63,P.gold,P.ink,24);
txt(s,'本组进一步开展任务微调',873,558,344,33,23,true,P.orange,'center');
arrow(s,[[417,373],[444,373]]);arrow(s,[[824,373],[851,373]]);
end(s,'语言指定目标、像素分割和证据回注，构成面向具体洪灾任务的模型基础。');
}
async function original(s){
const sc=path.join(root,'outputs/TerraScope_洪灾对齐修正版_20261015/逐景证据/evaluation/7571');
region(s,'(a) 视觉与语言输入',40,155,252,470,'#FAFCFD',P.db);
await img(s,path.join(sc,'RGB.png'),57,209,218,147);txt(s,'RGB 影像',60,363,213,28,21,true,P.db,'center');
block(s,'问题：\n水面覆盖率是多少？',58,424,217,91,P.blue,P.ink,22);
block(s,'视觉编码器',329,199,246,53,P.blue);block(s,'Projector',329,285,246,44,P.blue);
tokens(s,357,356,8,P.blue);txt(s,'视觉 token',357,384,210,26,18,false,P.db,'center');
block(s,'语言模型 InternVL3\n生成文本与控制 token',329,428,328,83,P.lav,P.ink,25);
block(s,'SAM2 图像编码器',621,199,261,53,P.blue);
block(s,'SAM2 掩膜解码器',933,199,302,70,P.sage,P.ink,24);
block(s,'[SEG] 提示投影',706,430,177,78,P.gold,P.ink,21);
await img(s,path.join(sc,'P1.png'),972,325,227,151);txt(s,'像素级掩膜',972,481,227,29,22,true,P.dg,'center');
block(s,'掩膜内选取视觉特征',929,551,307,57,P.sage,P.ink,22);
tokens(s,703,563,8,P.sage);txt(s,'〈REGION〉token',698,599,213,25,20,true,P.dg,'center');
block(s,'继续生成回答：约 16%',329,558,328,50,P.lav,P.ink,23);
arrow(s,[[275,280],[305,280],[305,225],[329,225]]);arrow(s,[[452,252],[452,285]]);arrow(s,[[452,329],[452,356]]);arrow(s,[[452,409],[452,428]]);
arrow(s,[[275,280],[305,280],[305,146],[752,146],[752,199]]);arrow(s,[[275,470],[329,470]]);arrow(s,[[657,469],[706,469]]);arrow(s,[[882,225],[933,225]]);
arrow(s,[[883,469],[910,469],[910,250],[933,250]],P.orange);arrow(s,[[1084,269],[1084,325]]);arrow(s,[[1084,510],[1084,551]],P.dg);
arrow(s,[[929,580],[895,580]],P.dg);arrow(s,[[697,580],[697,531],[490,531],[490,511]],P.dg);
arrow(s,[[549,368],[675,368],[675,637],[1084,637],[1084,608]],P.db,true);txt(s,'区域特征通路',730,613,185,24,17,false,P.db,'center');arrow(s,[[380,511],[380,558]],P.purple);
end(s,'SEG 把语言意图转成分割提示，REGION 将对应区域的视觉证据回注语言模型。');
}
async function workflow(s){
const xs=[43,453,863],ws=374;
for(let i=0;i<3;i++)region(s,['(a) 任务适配','(b) 稳健推理','(c) 空间输出'][i],xs[i],166,ws,457,[P.gold,P.blue,P.sage][i],['#A17742',P.db,P.dg][i]);
await img(s,pic('7301','rgb'),60,224,160,109);await img(s,pic('7301','gt'),239,224,160,109);
txt(s,'RGB 航拍',62,337,158,25,18,true);txt(s,'受淹道路标签',236,337,164,25,18,true);
block(s,'冻结视觉与语言底座',72,391,316,48,'white',P.ink,22);
block(s,'训练提示投影 ＋ 分割头',72,477,316,62,'#EBCB98',P.ink,23);arrow(s,[[230,362],[230,391]]);arrow(s,[[230,439],[230,477]],P.orange);
txt(s,'300 幅训练 · 约 17.98 M 可训练参数',63,573,334,27,20,true,P.orange,'center');
for(let i=0;i<4;i++){let x=477+(i%2)*166,y=225+Math.floor(i/2)*116;await img(s,path.join(A,`tta_input_${i}.png`),x,y,149,100);}
block(s,'逆变换对齐 → 分数平均',479,477,322,62,'#BDD6E5',P.ink,23);arrow(s,[[640,453],[640,477]],P.db);
txt(s,'同一模型 · 四个视图 · 无新增参数',474,573,334,27,20,true,P.db,'center');
await img(s,pic('7301','tta4'),882,225,338,226);
block(s,'道路掩膜 → 覆盖率 → 核查清单',879,477,342,62,'#B8D5C5',P.ink,22);arrow(s,[[1050,451],[1050,477]],P.dg);
txt(s,'448 幅测试 ＋ 370 幅额外验证',878,573,344,27,20,true,P.dg,'center');
arrow(s,[[417,509],[450,509]],P.orange);arrow(s,[[827,509],[860,509]],P.db);
end(s,'本组完成：任务化微调、训练与推理方案对照，以及可定位、可统计的洪灾筛查输出。');
}
async function train(s){
region(s,'(a) 冻结视觉与语言底座',40,166,680,390,'#F5F8FB',P.db);
region(s,'(b) 训练分割接口',751,166,277,390,'#FFF9EF',P.orange);
await img(s,pic('7301','rgb'),58,220,228,153);txt(s,'RGB 影像',70,380,202,27,21,true,P.db,'center');
block(s,'固定道路分割提示\n＋ [SEG] 输出前缀',58,451,230,75,P.blue,P.ink,21);
block(s,'视觉编码器 ＋ Projector',349,213,341,57,P.blue,P.ink,23);block(s,'语言模型 InternVL3\n提取 SEG 隐藏状态',349,329,341,78,P.blue,P.ink,24);block(s,'SAM2 图像编码器',349,467,341,57,P.blue,P.ink,24);
block(s,'提示投影层',776,329,227,78,P.gold,P.orange,25);block(s,'SAM2 掩膜解码器',776,467,227,57,P.gold,P.orange,23);
await img(s,pic('7301','mask_gt'),1065,204,165,110);txt(s,'真实受淹道路标签',1055,320,185,27,19,true,P.dg,'center');
await img(s,pic('7301','single_view_mask'),1065,402,165,110);txt(s,'预测掩膜',1061,515,177,27,20,true,P.db,'center');
block(s,'训练目标：BCE ＋ Dice / Lovasz',751,583,479,49,P.sage,P.ink,23);
txt(s,'仅更新约 17.98 M 参数\n冻结编码器与语言模型',48,582,328,54,23,true,P.db,'center');
txt(s,'翻转、亮度与对比度增强\n最多 1200 次参数更新 / 每次训练',385,582,344,54,21,false,P.ink,'center');
arrow(s,[[286,283],[318,283],[318,241],[349,241]]);arrow(s,[[520,270],[520,329]]);arrow(s,[[288,486],[318,486],[318,369],[349,369]]);
arrow(s,[[690,368],[776,368]],P.orange);arrow(s,[[172,407],[172,427],[331,427],[331,496],[349,496]]);arrow(s,[[690,496],[776,496]],P.db);
arrow(s,[[889,407],[889,467]],P.orange);arrow(s,[[1003,495],[1065,495]],P.orange);
arrow(s,[[1230,261],[1245,261],[1245,607],[1230,607]],P.dg);arrow(s,[[1148,545],[1148,583]],P.dg);
arrow(s,[[861,583],[861,565],[736,565],[736,368],[776,368]],P.orange,true);txt(s,'反向更新',620,559,114,25,18,true,P.orange,'center');
end(s,'保留预训练模型的通用表征，把可训练参数集中在语言提示到道路掩膜的关键接口。');
}
async function tta(s){
const ys=[203,310,417,524];
txt(s,'(a) 四种输入视图',45,154,220,33,23,true,P.db,'center');txt(s,'(b) 共享微调模型',295,154,238,33,23,true,P.orange,'center');txt(s,'(c) 逆变换至原坐标',579,154,245,33,23,true,P.db,'center');txt(s,'(d) 融合输出',968,154,263,33,23,true,P.dg,'center');
box(s,311,218,212,387,'#FFF9EF',P.orange);block(s,'视觉与语言底座',328,257,178,70,P.blue,P.db,21);block(s,'[SEG] 提示投影',328,373,178,62,P.gold,P.orange,21);block(s,'SAM2 分割头',328,479,178,62,P.gold,P.orange,21);arrow(s,[[417,327],[417,373]],P.orange);arrow(s,[[417,435],[417,479]],P.orange);txt(s,'同一组模型参数',322,564,190,28,21,true,P.orange,'center');
const names=['原图','水平翻转','垂直翻转','双向翻转'];
for(let i=0;i<4;i++){await img(s,path.join(A,`tta_input_${i}.png`),49,ys[i],146,95);txt(s,names[i],194,ys[i]+31,98,27,18,true,P.db,'center');arrow(s,[[287,ys[i]+48],[311,ys[i]+48]]);await img(s,path.join(A,`tta_aligned_${i}.png`),601,ys[i],100,95);arrow(s,[[523,ys[i]+48],[599,ys[i]+48]],P.db);txt(s,'T⁻¹',536,ys[i]+18,50,24,18,true,P.db,'center');arrow(s,[[702,ys[i]+48],[742,ys[i]+48]],P.db);}
sh(s,'line',742,251,0,321,'none',P.db,1.5);arrow(s,[[742,411],[780,411]],P.db);
block(s,'分数平均\n↓\n阈值化',780,335,151,150,P.blue,P.ink,24);arrow(s,[[931,411],[977,411]],P.dg);
await img(s,pic('6598','tta4_mask'),979,225,246,168);await img(s,pic('6598','tta4'),979,435,246,168);
txt(s,'最终掩膜',980,394,243,28,21,true,P.dg,'center');txt(s,'叠加原图定位',979,608,244,27,21,true,P.dg,'center');
txt(s,'M = 1[ meanₖ Tₖ⁻¹( fθ(Tₖ(I)) ) > 0 ]',308,612,627,32,22,true,P.ink,'center');
end(s,'一次训练、四次前向；所有视图恢复到同一像素坐标后，再融合输出。');
}
async function data(s){
const ns=['300','80','448','370'],labs=['训练集','验证集','完整测试集','额外验证集'],sub=['162 受淹 / 138 未淹','30 受淹 / 50 未淹','49 受淹 / 399 未淹','23 受淹 / 347 未淹'];
for(let i=0;i<4;i++){let x=43+i*308;sh(s,'rect',x,160,281,6,[P.gold,P.lav,P.blue,P.sage][i]);txt(s,ns[i],x,184,281,68,54,true,C.green,'center');txt(s,labs[i],x,260,281,35,26,true,P.ink,'center');txt(s,sub[i],x,307,281,28,20,false,C.muted,'center');}
line(s,44,356,1188);
await img(s,pic('7595','rgb'),45,383,307,205);await img(s,pic('7595','gt'),370,383,307,205);txt(s,'FloodNet RGB 航拍',45,595,307,30,23,true,P.db,'center');txt(s,'像素级受淹道路标签',370,595,307,30,23,true,P.dg,'center');
head(s,'三类评价，共同衡量应用效果',720,380,512);
const rr=[['空间位置','全局 IoU / Dice'],['数值估算','覆盖率 MAE（百分点）'],['场景筛查','命中数、漏检数、误报数']];
rr.forEach((q,i)=>{const y=438+61*i;block(s,q[0],723,y,136,43,[P.blue,P.gold,P.sage][i],P.ink,21);txt(s,q[1],879,y,353,43,23);});
end(s,'按官方分区组织数据；验证集选择配置，448 幅与额外 370 幅分别评价。');
}
async function results(s){
head(s,'(a) 全局 IoU：定位能力逐步提升',44,150,707);
bar(s,['原始模型','初步微调','优化单视图','最终四视图'],[8.6566315536,48.8083393285,58.6274532996,58.276794292],[C.grey,P.gold,C.blue,C.sage],46,211,701,329,70,'0.00');
tile(s,'最终配置较原始模型提高','+49.62 个百分点',64,552,664,P.sage);
head(s,'(b) 覆盖率误差与场景误报',799,150,434);
const values=[['指标','原始模型','最终配置'],['覆盖率 MAE','5.05','0.83'],['未淹场景误报','169 / 399','2 / 399'],['受淹场景命中','40 / 49','44 / 49']];
table(s,values,798,210,435,195,[178,129,128],22);
txt(s,'误差单位：百分点；场景阈值：占图 ≥ 1%',798,417,435,27,17,false,C.muted,'center');
await img(s,pic('7301','baseline'),802,466,205,137);await img(s,pic('7301','tta4'),1027,466,205,137);
txt(s,'原始模型',801,607,207,28,21,true,P.db,'center');txt(s,'本组最终配置',1025,607,209,28,21,true,P.dg,'center');
end(s,'任务微调显著改善空间定位；最终配置同时降低覆盖率误差与未淹场景误报。');
}
function table(s,values,x,y,w,h,widths,size=21){const tb=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});tb.borders.assign({style:'solid',fill:'#D9E3E2',width:1});for(let i=0;i<values.length;i++)for(let j=0;j<values[0].length;j++){const c=tb.getCell(i,j);c.fill=i===0?P.sage:(i%2===0?'#F4F7F7':'#FFFFFF');c.text.style={fontSize:size,typeface:(j===0||i===0)?'Songti SC':'Times New Roman',color:C.ink,bold:i===0,alignment:'center',verticalAlignment:'middle'};}return tb;}
async function choice(s){
head(s,'(a) 第一阶段：结构与监督探索',45,151,554);
table(s,[['配置（400 次更新）','测试 IoU'],['分割头＋投影层','48.81%'],['再加 LoRA（三次均值）','49.73%'],['残差细节模块','47.63%'],['细节模块＋边界监督','46.56%'],['细节模块＋道路辅助','48.77%'],['组合方案','48.35%']],45,211,554,340,[398,156],21);
block(s,'主要收益来自任务适配\n新增模块未稳定提升整体 IoU',45,577,554,63,P.gold,P.ink,23);
head(s,'(b) 第二阶段：训练与目标函数',654,151,578);
await img(s,path.join(A,'training_choices.png'),654,204,578,392);
txt(s,'两种目标 × 三个种子 · 每次最多 1200 次更新',653,607,580,29,20,true,P.db,'center');
end(s,'按 80 幅验证集选择单模型，再比较单视图与四视图部署；不简单堆叠所有模块。');
}
async function qualitative(s){
const cols=['RGB 影像','原始 TerraScope','本组最终配置','真实受淹道路'];const keys=['rgb','baseline','tta4','gt'];
cols.forEach((v,i)=>{block(s,v,122+i*280,151,269,39,[P.blue,'#E9EDF0',P.gold,P.sage][i],P.ink,22);});
const ids=['7595','7301','7986'];
for(let r=0;r<3;r++){let y=201+r*146,id=ids[r];txt(s,id,37,y+29,75,32,25,true,C.green,'center');const z=D.cases[id].tta4;txt(s,r<2?`IoU\n${(z.iou*100).toFixed(1)}%`:'未淹\n场景',34,y+69,81,48,18,false,C.muted,'center');for(let c=0;c<4;c++)await img(s,pic(id,keys[c]),122+c*280,y,269,134);}
end(s,'同一影像、同一坐标并排比较：蓝色为预测区域，绿色为真实受淹道路。');
}
async function holdout(s){
head(s,'(a) 同一权重：单视图与四视图',44,150,622);
bar(s,['单视图','四视图'],[52.0563969084,55.6850615158],[C.blue,C.sage],45,219,306,283,65,'0.00');txt(s,'全局 IoU（%）',66,194,263,27,21,true,P.db,'center');
bar(s,['单视图','四视图'],[10,1],[C.blue,C.sage],365,219,295,283,12,'0');txt(s,'未淹误报数',383,194,265,27,21,true,P.db,'center');
tile(s,'误报数量减少','90%',51,535,290,P.gold);tile(s,'受淹场景命中保持不变','21 / 23',364,535,291,P.sage);
head(s,'(b) 消除水面对道路目标的干扰',713,150,519);
const names=['原始 RGB','真实标签：无受淹道路','单视图：误报 20.76%','四视图：0.00%'];
for(let i=0;i<4;i++){let x=713+(i%2)*267,y=211+Math.floor(i/2)*205;await img(s,pic('7679',['rgb','gt','single_view','tta4'][i]),x,y,252,162);txt(s,names[i],x,y+164,252,30,19,true,i===3?P.dg:P.ink,'center');}
end(s,'额外 370 幅：347 幅未淹、23 幅受淹；场景判定阈值为预测受淹区域占图 ≥ 1%。');
}
async function application(s){
head(s,'(a) 居民区 7301：定位受淹道路',43,150,693);head(s,'(b) 同窗口局部对照',783,150,451);
await img(s,pic('7301','boxed'),43,207,694,430);
await img(s,pic('7301','zoom_tta4'),782,211,218,180);await img(s,pic('7301','zoom_gt'),1018,211,218,180);
txt(s,'最终预测',783,397,218,29,22,true,P.db,'center');txt(s,'真实标签',1018,397,218,29,22,true,P.dg,'center');
tile(s,'预测区域占影像','21.75%',786,452,210,P.blue);tile(s,'空间 IoU','73.35%',1020,452,210,P.sage);
txt(s,'保存原图、像素掩膜与覆盖率记录\n形成可回看、可定位的核查材料',785,567,449,67,24,true,P.ink,'center');
end(s,'应用定位：为受淹道路调查筛查提供影像证据，辅助确定需要进一步核查的位置。');
}
async function summary(s){
const tt=[['任务化适配','300 幅标注训练\n约 17.98 M 参数微调\nRGB 直接输出道路掩膜',P.gold],['系统优化验证','LoRA、结构与监督对照\n双目标 × 三种子训练\n同权重四视图推理',P.blue],['洪灾应用输出','818 幅影像评估\n像素定位与覆盖率统计\n逐景输出核查依据',P.sage]];
for(let i=0;i<3;i++){const x=44+i*408;badge(s,String(i+1),tt[i][0],x,170,378,[P.orange,P.db,P.dg][i]);block(s,tt[i][1],x,223,375,158,tt[i][2],P.ink,25);}
txt(s,'+49.62',66,424,520,86,71,true,C.green,'center');txt(s,'完整测试集 IoU 提升（百分点）',66,515,520,34,24,true,P.ink,'center');
txt(s,'90%',695,424,520,86,71,true,C.green,'center');txt(s,'额外验证集误报数量减少',695,515,520,34,24,true,P.ink,'center');
txt(s,'从通用遥感理解，走向具体道路目标的空间定位与调查筛查',46,595,1187,44,31,true,C.green,'center');
end(s,'本组完成了“复现—适配—优化—验证—应用输出”的完整实验流程。');
}
return{background,capability,original,workflow,train,tta,data,results,choice,qualitative,holdout,application,summary};
}
