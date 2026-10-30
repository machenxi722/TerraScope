import fs from 'node:fs/promises';import path from 'node:path';
import {paper}from'../alignment_revision/diagram_utils.mjs';
const C={ink:'#233C48',edge:'#83969D',blue:'#DCECF5',db:'#427C9C',cyan:'#B9DCEB',gold:'#F7E6C6',orange:'#BA7B48',sage:'#DDEBDA',green:'#54856B',lav:'#E7E0F2',purple:'#8971A8',soft:'#F7F9FA',grid:'#E0E8EB'};
function mix(a,b,t){const f=s=>[1,3,5].map(i=>parseInt(s.slice(i,i+2),16));const x=f(a),y=f(b);return'#'+x.map((v,i)=>Math.round(v*(1-t)+y[i]*t).toString(16).padStart(2,'0')).join('');}
function art(s){
const p=paper(s),{text,box,shape,arrow,img}=p;
const tx=(str,x,y,w,h,size=21,bold=false,col=C.ink,align='left')=>text(str,x,y,w,h,size,bold,align,col);
function line(x1,y1,x2,y2,col=C.edge,width=1.2,dash=false){const l=Math.min(x1,x2),t=Math.min(y1,y2),w=Math.max(.1,Math.abs(x2-x1)),h=Math.max(.1,Math.abs(y2-y1));return s.shapes.add({geometry:'custom',position:{left:l,top:t,width:w,height:h},fill:'none',line:{fill:col,width,style:dash?'dash':'solid'},customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-l,y:y1-t}},{lineTo:{x:x2-l,y:y2-t}}]}]});}
function poly(pts,fill,edge=C.edge,lw=.8){const xx=pts.map(p=>p[0]),yy=pts.map(p=>p[1]),x=Math.min(...xx),y=Math.min(...yy),w=Math.max(...xx)-x,h=Math.max(...yy)-y;return s.shapes.add({geometry:'custom',position:{left:x,top:y,width:w,height:h},fill,line:{fill:edge,width:lw,style:'solid'},customPaths:[{width:w,height:h,commands:[{moveTo:{x:pts[0][0]-x,y:pts[0][1]-y}},...pts.slice(1).map(p=>({lineTo:{x:p[0]-x,y:p[1]-y}})),{close:{}}]}]});}
function region(title,x,y,w,h,col=C.db,fill='#FFFFFF'){const r=box(x,y,w,h,fill,mix(col,'#FFFFFF',.35));r.line={fill:mix(col,'#FFFFFF',.28),width:1.15,style:'dash'};tx(title,x+15,y+9,w-30,29,23,true,col);return r;}
function module(title,x,y,w,h,fill=C.blue,col=C.db,sub=''){box(x+3,y+3,w,h,'#EDF1F2','none');box(x,y,w,h,fill,mix(col,'#FFFFFF',.3));tx(title,x+9,y+(sub?3:4),w-18,sub?30:h-8,w<130?18:w<190?20:22,true,C.ink,'center');if(sub)tx(sub,x+9,y+h-24,w-18,21,16,false,col,'center');}
function freeze(x,y,r=10){for(let k=0;k<3;k++){const a=k*Math.PI/3;line(x-r*Math.cos(a),y-r*Math.sin(a),x+r*Math.cos(a),y+r*Math.sin(a),C.db,1.7);}for(let k=0;k<6;k++){const a=k*Math.PI/3;let xx=x+r*.65*Math.cos(a),yy=y+r*.65*Math.sin(a);for(const d of [-.8,.8])line(xx,yy,xx-r*.32*Math.cos(a+d),yy-r*.32*Math.sin(a+d),C.db,1.3);}}
function learn(x,y){poly([[x,y-12],[x+7,y-3],[x+9,y+4],[x+5,y+11],[x-3,y+12],[x-9,y+6],[x-8,y-2],[x-4,y+2]],C.orange,'none');poly([[x,y-1],[x+4,y+5],[x+2,y+10],[x-2,y+10],[x-4,y+5]],'#F7DEAF','none');}
function vec(x,y,n,col,w=13,h=24,gap=4){for(let i=0;i<n;i++){const z=box(x+i*(w+gap),y,w,h,mix(col,'#FFFFFF',i%3===0?.05:.25),mix(col,C.ink,.2));z.line.width=.7;}}
function tensor(x,y,w,h,col=C.blue,n=3,grid=5){for(let k=n-1;k>=0;k--){let xx=x+k*5,yy=y-k*5;shape('rect',xx,yy,w,h,mix(col,'#FFFFFF',.12*k),mix(C.db,'#FFFFFF',.35),.75);}for(let i=1;i<grid;i++){line(x+i*w/grid,y,x+i*w/grid,y+h,mix(C.db,'#FFFFFF',.65),.5);line(x,y+i*h/grid,x+w,y+i*h/grid,mix(C.db,'#FFFFFF',.65),.5);}poly([[x+w,y],[x+w+10,y-10],[x+w+10,y+h-10],[x+w,y+h]],mix(col,C.db,.12),mix(C.db,'#FFFFFF',.4),.65);}
function layerStack(x,y,w,h,col=C.lav,n=3){for(let i=n-1;i>=0;i--){box(x+i*5,y-i*5,w,h,mix(col,'#FFFFFF',i*.1),C.edge);}for(let i=0;i<3;i++)box(x+12,y+12+i*(h-24)/3,w-24,(h-30)/3,mix(col,'#FFFFFF',.35),'none');}
function cap(str){line(43,655,1237,655,'#B7CAC3',1);tx(str,48,664,1184,28,22,true,'#335B4A');}
return{...p,tx,line,poly,region,module,freeze,learn,vec,tensor,layerStack,cap};
}
export async function enhanced(root){
const A=path.join(root,'work/final_talk_20261016/assets');const pic=(id,k)=>path.join(A,`${id}_${k}.png`);const sc=path.join(root,'outputs/TerraScope_洪灾对齐修正版_20261015/逐景证据/evaluation/7571');const grid=JSON.parse(await fs.readFile(path.join(A,'mask_grid.json'),'utf8'));
async function original(s){
const a=art(s),{tx,shape,box,line,arrow,img,module,vec,tensor,layerStack,cap}=a;
// Three semantic regions, with all branches routed in the gutters.
a.region('(a) 影像与自然语言',38,162,270,465,C.db,'#FBFCFD');
await img(path.join(sc,'RGB.png'),56,210,232,155);tx('遥感 RGB 影像',57,371,232,27,21,true,C.db,'center');
for(let k=0;k<4;k++)await img(pic('7571',`tile${k}`),58+k*59,412,54,40);
tx('动态切片 → 视觉输入',57,458,232,27,19,true,C.db,'center');
box(57,520,231,77,C.lav,mix(C.purple,'#FFFFFF',.4));tx('问题：水面覆盖率\n是多少？',66,529,213,58,23,true,C.ink,'center');
tx('(b) 语言引导的像素分割',335,161,588,32,24,true,C.purple);tx('(c) 空间证据回注',952,161,283,32,24,true,C.green);
module('视觉编码器',337,213,233,56,C.blue,C.db);module('Projector',337,304,233,43,C.blue,C.db);
vec(351,375,11,C.cyan,14,25,5);tx('视觉 token',355,403,218,24,18,false,C.db,'center');
box(337,445,324,112,C.lav,mix(C.purple,'#FFFFFF',.3));tx('语言模型 InternVL3',349,452,300,32,25,true,C.ink,'center');
layerStack(357,502,111,35,'#D6CBE7',3);tx('Transformer\n语言与视觉融合',483,497,162,48,18,true,C.purple,'center');
module('SAM2 图像编码器',615,212,278,56,C.blue,C.db);
tensor(635,316,67,67,C.blue,3,6);tensor(735,332,51,51,C.blue,3,5);tensor(819,349,35,35,C.blue,3,4);
tx('多尺度视觉特征',622,402,272,27,20,true,C.db,'center');
box(709,462,183,93,C.gold,mix(C.orange,'#FFFFFF',.3));tx('[SEG] → 提示投影',717,466,167,31,20,true,C.orange,'center');
vec(726,509,4,'#EBC88B',16,22,6);tx('→ 256',821,507,64,27,19,true,C.orange,'center');
box(946,212,289,111,C.sage,mix(C.green,'#FFFFFF',.3));tx('SAM2 掩膜解码器',956,219,269,32,25,true,C.ink,'center');
module('提示融合',963,266,110,39,'#F5FAF2',C.green);module('掩膜预测',1090,266,128,39,'#F5FAF2',C.green);arrow([[1074,286],[1089,286]],C.green);
await img(path.join(sc,'P1.png'),967,359,245,163);tx('像素级水面掩膜',967,524,245,26,21,true,C.green,'center');
box(946,569,289,68,'#F3F8F0',mix(C.green,'#FFFFFF',.3));
for(let r=0;r<8;r++)for(let c=0;c<12;c++){const val=grid[Math.min(15,r*2)][Math.min(15,Math.floor(c*16/12))];shape('rect',958+c*6,577+r*6,6,6,val>.25?'#8BB8A0':'#E1EBE4','#FFFFFF',.25);}
tx('掩膜映射到视觉网格',1045,575,178,26,18,true,C.green,'center');vec(1064,607,8,'#B7D3B0',12,19,5);
vec(726,601,10,'#B7D3B0',13,23,5);tx('〈REGION〉token',719,573,190,27,20,true,C.green,'center');
box(337,598,324,39,'#F4EFF8','none');tx('继续生成回答：约 16%',345,598,308,39,23,true,C.purple,'center');
arrow([[288,430],[325,430],[325,241],[337,241]],C.db);arrow([[174,399],[174,412]],C.db);arrow([[454,269],[454,304]],C.db);arrow([[454,347],[454,375]],C.db);arrow([[454,430],[454,445]],C.db);
arrow([[288,558],[321,558],[321,493],[337,493]],C.purple);arrow([[661,503],[709,503]],C.orange);arrow([[892,504],[920,504],[920,288],[946,288]],C.orange);
arrow([[288,289],[317,289],[317,197],[755,197],[755,212]],C.db);arrow([[755,268],[755,298]],C.db);
line(669,383,669,395,C.db,1.25);line(760,383,760,395,C.db,1.25);line(836,384,836,395,C.db,1.25);arrow([[669,395],[912,395],[912,241],[946,241]],C.db);
arrow([[1090,323],[1090,359]],C.green);arrow([[1090,552],[1090,569]],C.green);arrow([[946,613],[910,613]],C.green);
arrow([[718,613],[685,613],[685,575],[582,575],[582,557]],C.green);arrow([[382,557],[382,598]],C.purple);
arrow([[570,324],[594,324],[594,434],[902,434],[902,646],[1090,646],[1090,637]],C.db,true);tx('视觉特征',736,628,150,22,17,false,C.db,'center');
cap('核心机制：语言生成分割提示；像素掩膜定位证据；区域 token 支持后续回答。');
}
async function workflow(s){
const a=art(s),{tx,shape,box,line,arrow,img,module,vec,tensor,freeze,learn,cap}=a;
// A compact timeline provides the overview; detailed visual structures sit below it.
const xs=[45,354,663,972],width=267;
const titles=['数据与任务定义','轻量任务适配','四视图稳健推理','空间结果与核查'];
const cs=[C.db,C.orange,C.purple,C.green],fills=[C.blue,C.gold,C.lav,C.sage];
line(55,178,1216,178,'#69848C',2);
for(let i=0;i<4;i++){box(xs[i],153,width,51,fills[i],mix(cs[i],'#FFFFFF',.35));tx(String(i+1),xs[i]+10,160,27,32,24,true,cs[i],'center');tx(titles[i],xs[i]+39,160,width-49,32,23,true,C.ink,'center');if(i<3)arrow([[xs[i]+width,178],[xs[i+1],178]],cs[i]);}
// Data: paired imagery, an explicit task prompt and train/validation partitions.
a.region('(a) 输入与监督',44,229,269,361,C.db,'#FBFCFD');
await img(pic('7301','rgb'),57,275,116,78);await img(pic('7301','mask_gt'),185,275,115,78);
tx('RGB',59,358,111,25,18,true,C.db,'center');tx('道路标签',184,358,117,25,18,true,C.green,'center');
box(59,403,239,65,'#FFFFFF',C.edge);tx('分割航拍影像中的\n受淹道路区域',67,410,223,51,22,true,C.ink,'center');
vec(72,490,10,C.cyan,15,22,5);tx('固定提示 ＋ SEG 前缀',63,521,234,27,20,true,C.db,'center');
// Adaptation: show exactly what is frozen and what is updated.
a.region('(b) 训练接口',353,229,269,361,C.orange,'#FFFCF7');
module('视觉与语言底座',368,278,239,60,C.blue,C.db,'保留预训练表征');freeze(587,295,9);
arrow([[487,338],[487,365]],C.orange);
module('SEG 提示投影',368,365,239,58,C.gold,C.orange,'3584 → 3584 → 256');learn(588,383);
arrow([[487,423],[487,448]],C.orange);
module('SAM2 掩膜解码',368,448,239,59,C.gold,C.orange,'任务标签驱动空间适配');learn(588,466);
tx('可训练参数：约 17.98 M',366,541,243,27,22,true,C.orange,'center');
// Inference: aligned, same-scene view stack and a real-mask result.
a.region('(c) 同权重多视图',662,229,269,361,C.purple,'#FCFAFD');
for(let i=0;i<4;i++)await img(path.join(A,`overview_view${i}.png`),677+(i%2)*123,276+Math.floor(i/2)*86,112,75);
arrow([[796,447],[796,469]],C.purple);
module('逆变换 → 平均 logits',678,469,237,52,C.lav,C.purple);
tx('四次前向 · 无新增参数',677,542,239,26,21,true,C.purple,'center');
// Output: evidence rather than a generic text card.
a.region('(d) 定位、统计、筛查',971,229,269,361,C.green,'#FBFDF9');
await img(pic('7301','tta4'),987,276,237,158);
module('掩膜 ＋ 覆盖率记录',987,464,237,52,C.sage,C.green);
tx('21.75%  预测区域占图',987,541,237,27,22,true,C.green,'center');
for(let i=0;i<3;i++)arrow([[xs[i]+269,410],[xs[i+1],410]],cs[i]);
// Evidence-backed selection path, separate from prediction arrows.
box(45,610,1195,31,'#EFF4F4','none');
tx('离线训练与选择',59,611,177,29,20,true,C.orange);tx('300 训练  →  80 验证选配置',240,611,344,29,21,true,C.ink,'center');
tx('评估与应用',633,611,145,29,20,true,C.green);tx('448 测试  ＋  370 额外验证',801,611,421,29,21,true,C.ink,'center');
cap('本组贡献贯穿训练、推理与应用：将通用遥感模型转为面向受淹道路的筛查流程。');
}
async function train(s){
const a=art(s),{tx,shape,box,line,arrow,img,module,vec,tensor,freeze,learn,cap}=a;
// Frozen backbone and trainable interfaces are explicitly separated by color and boundary.
a.region('(a) 冻结表征提取',40,167,581,360,C.db,'#F7FAFD');
a.region('(b) 轻量可训练接口',648,167,357,360,C.orange,'#FFFBF5');
tx('监督与输出',1040,172,197,31,23,true,C.green,'center');
await img(pic('7301','rgb'),56,228,170,114);tx('RGB 航拍',57,349,168,26,20,true,C.db,'center');
module('视觉编码 / Projector',279,223,319,53,C.blue,C.db);freeze(577,240,9);
box(279,318,319,87,C.lav,mix(C.purple,'#FFFFFF',.4));tx('语言模型 InternVL3',288,325,300,31,23,true,C.ink,'center');
vec(298,369,9,'#C9BDDC',15,22,6);tx('SEG',507,365,75,29,20,true,C.purple,'center');freeze(577,340,9);
box(56,427,171,71,'#FFFFFF',C.edge);tx('固定分割提示\n＋ SEG 输出前缀',62,435,159,54,20,true,C.ink,'center');
module('SAM2 图像编码',279,442,163,56,C.blue,C.db);freeze(423,457,8);
tensor(473,448,40,40,C.blue,3,4);tensor(527,458,30,30,C.blue,3,3);tensor(571,467,21,21,C.blue,3,3);
tx('多尺度视觉特征',456,497,147,22,17,false,C.db,'center');
// Projection has real architecture from the loaded model, not a placeholder module.
box(665,224,323,140,C.gold,mix(C.orange,'#FFFFFF',.4));tx('SEG 提示投影 MLP',677,231,299,30,23,true,C.orange,'center');learn(967,245);
const xx=[681,788,875],ww=[86,67,97];const ls=['Linear','ReLU','Linear'];
for(let i=0;i<3;i++){module(ls[i],xx[i],283,ww[i],39,'#FFF9EA',C.orange);if(i<2)arrow([[xx[i]+ww[i],303],[xx[i+1],303]],C.orange);}
tx('3584 → 3584 → 256 维提示',680,329,291,25,20,true,C.orange,'center');
box(665,411,323,96,C.gold,mix(C.orange,'#FFFFFF',.4));tx('SAM2 掩膜解码器',679,417,296,31,24,true,C.orange,'center');learn(967,432);
module('提示 / 图像融合',680,460,152,33,'#FFFAEF',C.orange);module('掩膜预测',855,460,116,33,'#FFFAEF',C.orange);arrow([[832,476],[855,476]],C.orange);
await img(pic('7301','mask_gt'),1051,223,179,120);tx('真实受淹道路标签',1040,349,198,28,19,true,C.green,'center');
await img(pic('7301','single_view_mask'),1051,411,179,120);tx('预测掩膜',1053,534,176,26,20,true,C.db,'center');
// Bottom: actual two supervised objectives and a clearly routed backward branch.
box(653,580,579,61,C.sage,mix(C.green,'#FFFFFF',.35));tx('训练目标',669,591,103,37,22,true,C.green,'center');
module('BCE',793,592,95,35,'#FFFFFF',C.green);tx('＋',894,592,29,35,25,true,C.green,'center');module('Dice / Lovasz',929,592,282,35,'#FFFFFF',C.green);
tx('同步翻转  ·  亮度 / 对比度增强',45,552,558,30,22,true,C.db,'center');
tx('约 17.98 M 参数  ·  最多 1200 次更新',45,600,558,32,24,true,C.orange,'center');
arrow([[226,285],[249,285],[249,249],[279,249]],C.db);arrow([[439,276],[439,318]],C.db);arrow([[227,462],[251,462],[251,361],[279,361]],C.purple);
arrow([[141,379],[141,394],[263,394],[263,471],[279,471]],C.db);arrow([[442,470],[467,470]],C.db);arrow([[598,362],[628,362],[628,303],[665,303]],C.orange);
arrow([[827,364],[827,411]],C.orange);arrow([[604,470],[665,470]],C.db);arrow([[988,477],[1051,477]],C.orange);
arrow([[1230,284],[1245,284],[1245,610],[1232,610]],C.green);arrow([[1141,563],[1141,580]],C.green);
arrow([[652,609],[632,609],[632,385],[665,385],[665,364]],C.orange,true);tx('反向更新',666,375,146,26,18,true,C.orange);arrow([[632,530],[827,530],[827,507]],C.orange,true);
freeze(55,143,8);tx('冻结',68,132,62,25,18,true,C.db);learn(149,145);tx('训练',165,132,62,25,18,true,C.orange);
cap('模型底座保持冻结；监督信号通过分割损失，只更新提示投影和掩膜解码器。');
}
async function tta(s){
const a=art(s),{tx,shape,box,line,arrow,img,module,vec,tensor,freeze,learn,cap}=a;
const xs=[55,272,489,706];
tx('(a) 同一影像构建四种视图',45,155,850,32,24,true,C.db);
for(let i=0;i<4;i++){
 let x=xs[i];box(x-6,201,188,129,'#F7FAFC',mix(C.db,'#FFFFFF',.55));await img(path.join(A,`tta_input_${i}.png`),x,207,176,118);
 tx(['原图','水平翻转','垂直翻转','双向翻转'][i],x,337,176,27,21,true,C.db,'center');
 if(i===1||i===3)line(x+88,211,x+88,320,'#E9CA93',1.4,true);
 if(i===2||i===3)line(x+5,266,x+171,266,'#E9CA93',1.4,true);
 arrow([[x+88,365],[x+88,387]],C.db);
}
// Shared forward stage runs through identical modules, represented once for all four views.
box(46,387,850,70,'#FFF9ED',mix(C.orange,'#FFFFFF',.35));tx('(b) 共享模型',60,405,160,33,23,true,C.orange);
module('冻结表征',239,402,161,39,C.blue,C.db);module('SEG 投影',439,402,173,39,C.gold,C.orange);module('SAM2 分割',653,402,217,39,C.gold,C.orange);
arrow([[400,422],[439,422]],C.orange);arrow([[612,422],[653,422]],C.orange);

for(let i=0;i<4;i++){
 const x=xs[i];await img(path.join(A,`tta_aligned_${i}.png`),x+31,515,116,116);box(x+24,508,130,130,'none',mix(C.purple,'#FFFFFF',.5));
 arrow([[x+88,457],[x+88,504]],C.purple);box(x+68,476,42,25,'#FFFFFF','none');tx('T⁻¹',x+68,475,42,26,19,true,C.purple,'center');
}
// A fusion detail on the right combines four measured aligned score maps.
a.region('(c) logits 融合与输出',924,163,313,478,C.green,'#FBFDF9');
for(let i=3;i>=0;i--){box(964+i*9,231-i*8,116,116,'white',mix(C.green,'#FFFFFF',.4));await img(path.join(A,`tta_aligned_${i}.png`),968+i*9,235-i*8,108,108);}
tx('四视图\n对齐分数',1110,252,112,65,21,true,C.green,'center');
arrow([[1050,349],[1050,366]],C.green);module('平均 logits',953,368,253,39,C.sage,C.green);
arrow([[1080,407],[1080,427]],C.green);module('恢复原尺寸 → 阈值化',943,427,273,40,C.sage,C.green);
await img(pic('6598','tta4_mask'),943,492,129,86);await img(pic('6598','tta4'),1088,492,129,86);
tx('最终掩膜',943,587,129,27,19,true,C.green,'center');tx('原图叠加',1088,587,129,27,19,true,C.green,'center');
arrow([[1080,467],[1080,481],[1008,481],[1008,492]],C.green);arrow([[1080,481],[1153,481],[1153,492]],C.green);
// Collection bus stays outside every image and label.
for(let i=0;i<4;i++)line(xs[i]+157,584,xs[i]+188,584,C.purple,1.2);
line(243,584,243,649,C.purple,1.2);line(460,584,460,649,C.purple,1.2);line(677,584,677,649,C.purple,1.2);line(894,584,894,649,C.purple,1.2);
line(243,649,912,649,C.purple,1.2);arrow([[912,649],[912,289],[963,289]],C.purple);
cap('先对齐、后融合：不新增模型参数，以四次前向计算换取更稳定的空间筛查结果。');
}
return{original,workflow,train,tta};
}
