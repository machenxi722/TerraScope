import fs from 'node:fs/promises';import path from 'node:path';import {art,mix} from './method_art.mjs';
import{paper}from'../alignment_revision/diagram_utils.mjs';import{design,C as DC}from'../final_talk_20261016/design.mjs';
const C={ink:'#213B38',muted:'#647B73',blue:'#DCECF5',db:'#477D99',sage:'#DDEBDA',dg:'#4D846B',gold:'#F6E5C3',orange:'#B77A46',lav:'#E7DFF0',purple:'#8872A3',rose:'#DDB0B8',grid:'#DCE6E0',white:'#FFFFFF',green:'#00552B'};
function u(s){const p=paper(s);const tx=(str,x,y,w,h,size=22,bold=false,col=C.ink,align='left')=>p.text(str,x,y,w,h,size,bold,align,col);
const ln=(x,y,w,col=C.grid,lw=1)=>p.shape('line',x,y,w,0,'none',col,lw);
const mod=(str,x,y,w,h,fill=C.blue,col=C.db,size=21)=>{p.box(x,y,w,h,fill,col);tx(str,x+8,y+3,w-16,h-6,size,true,C.ink,'center');};
const cap=str=>{ln(43,660,1193,'#B7CAC3');tx(str,47,667,1186,28,22,true,'#335B4A');};
const heading=(str,x,y,w,col=C.green)=>{tx(str,x,y,w,34,24,true,col);ln(x,y+39,w);};
const tensor=(x,y,w,h,n=3,col=C.blue)=>{for(let i=n-1;i>=0;i--)p.shape('rect',x+i*5,y-i*5,w,h,col,C.db,.75);for(let j=1;j<5;j++){p.shape('line',x+j*w/5,y,0,h,'none','#A6C5D5',.5);ln(x,y+j*h/5,w,'#A6C5D5',.5);}};
function table(values,x,y,w,h,widths,size=20){const tb=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});tb.borders.assign({fill:'#D5E1DB',width:.7,style:'solid'});for(let i=0;i<values.length;i++)for(let j=0;j<values[0].length;j++){const c=tb.getCell(i,j);c.fill=i===0?C.sage:(i%2?'#FFFFFF':'#F4F7F5');c.text.style={fontSize:size,typeface:i===0||j===0?'Songti SC':'Times New Roman',color:C.ink,bold:i===0,alignment:'center',verticalAlignment:'middle'};}return tb;}
return{...p,tx,ln,mod,cap,heading,tensor,table};}
export async function redesigned(R){const A=path.join(R,'work/final_talk_20261016/assets'),E=path.join(R,'work/editorial_v2_20261016/assets');const pic=(id,k)=>path.join(A,`${id}_${k}.png`),ex=k=>path.join(E,k);const D=JSON.parse(await fs.readFile(path.join(A,'data.json'),'utf8'));const {bar}=design();
async function background(s){const a=u(s),{tx,shape,img,heading,arrow,ln,cap}=a;
heading('灾后调查首先需要及时掌握现场',43,149,586);
await img(path.join(R,'work/wuhan_flood/scenes/2016-07-09/rgb.png'),44,209,258,190);
await img(pic('7301','rgb'),324,209,302,190);
tx('卫星观测',44,404,258,30,23,true,C.db,'center');tx('无人机航拍',325,404,300,30,23,true,C.dg,'center');
tx('覆盖大范围\n受重访时机与光学云层影响',45,446,260,63,21,false,C.ink,'center');tx('面向重点区域灵活采集\n呈现道路与建筑的局部细节',326,446,300,63,21,false,C.ink,'center');
ln(43,530,583);tx('本项目选择 RGB 航拍',46,548,580,37,28,true,C.green);tx('匹配局部灾区的精细调查需求',46,594,580,31,23,false,C.muted);
heading('拿到影像之后，如何尽快完成判读？',678,149,558);
for(let i=0;i<3;i++){const k=['7595','7301','7986'][i];await img(pic(k,'rgb'),690+i*20,229+i*15,193,129);}
tx('大量航拍影像',683,407,244,30,22,true,C.db,'center');
arrow([[942,318],[981,318]],C.orange);tx('逐张判读\n逐处圈绘\n逐幅统计',994,260,219,112,25,true,C.orange,'center');
ln(681,456,553);tx('处理瓶颈',683,476,150,36,28,true,C.orange);tx('拍得快，还需要解译跟得上',836,476,399,36,25,true,C.ink);
shape('rect',682,542,554,89,'#EFF5F0');tx('我们的目标',700,550,180,28,21,true,C.green);tx('RGB 影像自动定位受淹道路\n输出掩膜与覆盖率，支持快速核查',701,580,514,47,23,true,C.ink);
cap('应用需求：让航拍获得的现场信息，及时转化为可定位、可统计的受淹道路证据。');}
async function capability(s){const a=u(s),{tx,img,shape,heading,arrow,ln,mod,cap}=a;const sc=path.join(R,'outputs/TerraScope_洪灾对齐修正版_20261015/逐景证据/evaluation/7571');
heading('像素级证据，使遥感问答可以核查',43,149,744);
tx('问题：影像中的水面覆盖了多少比例？',47,200,733,36,26,true,C.db);
await img(path.join(sc,'RGB.png'),47,252,343,230);await img(path.join(sc,'P1.png'),431,252,343,230);arrow([[394,364],[427,364]],C.db);
tx('输入遥感影像',47,487,343,29,22,true,C.db,'center');tx('与回答关联的分割掩膜',431,487,343,29,22,true,C.dg,'center');
shape('rect',47,536,727,53,C.sage);tx('本地实际回答：约 16%',66,538,689,49,29,true,C.green);tx('语言说明目标与结论，掩膜保留对应位置',48,605,729,34,24,true,C.ink);
heading('TerraScope 的地理空间任务',836,149,400);
const abilities=[['覆盖率','目标占影像的比例'],['绝对面积','结合空间分辨率核算'],['面积比较','判断不同地物的大小'],['边界关系','判断相邻与接触'],['距离测量','估计目标间距'],['建筑变化','比较灾前后的变化']];
for(let i=0;i<abilities.length;i++){const y=207+i*53;tx(String(i+1).padStart(2,'0'),836,y,40,30,22,true,i<2?C.orange:C.db);tx(abilities[i][0],885,y,151,30,23,true);tx(abilities[i][1],885,y+27,350,24,18,false,C.muted);if(i<5)ln(884,y+51,352);}
shape('rect',836,558,399,78,C.gold);tx('本组聚焦：洪灾道路',851,562,370,32,26,true,C.orange);tx('在通用模型基础上做任务化适配',851,600,370,27,21,false,C.ink);
cap('选择模型的原因：自然语言定义目标，同时获得回答和可核查的像素位置。');}
async function workflow(s){const a=u(s),{tx,img,shape,box,heading,arrow,ln,mod,tensor,cap}=a;
// Unequal two-stage composition with a single checkpoint linking training to inference.
shape('rect',42,154,1196,226,'#F8F4ED');tx('(a) 离线适配',57,162,195,33,26,true,C.orange);tx('训练一次，验证集选择权重',248,164,395,30,21,false,C.muted);
for(let i=2;i>=0;i--)await img(ex(`train_${['6597','6601','6701'][i]}_rgb.png`),64+i*10,214+i*8,148,99);
await img(ex('train_6597_gt.png'),234,230,133,89);tx('300 幅 RGB ＋ 道路标签',65,338,305,28,21,true,C.ink);
arrow([[375,268],[409,268]],C.orange);
mod('TerraScope 任务适配',414,216,358,59,C.gold,C.orange,25);art(s).freeze(437,298,10);tx('冻结视觉与语言底座',458,285,293,28,21,false,C.db,'center');art(s).learn(438,334);tx('SEG 投影与 SAM2 掩膜头',458,319,294,29,21,true,C.orange,'center');
arrow([[778,267],[818,267]],C.orange);mod('80 幅验证集选配置',823,217,382,55,C.sage,C.dg,24);tx('双目标 × 三种子\n保存最佳任务权重 θ*',833,291,362,62,23,true,C.dg,'center');
shape('rect',42,409,1196,229,'#F2F6F7');tx('(b) 批量解译',56,416,210,33,26,true,C.db);tx('同一组权重，四视图稳健推理',542,417,650,31,22,false,C.muted);
await img(pic('6598','rgb'),60,486,176,117);tx('待调查航拍影像',60,606,176,26,20,true,C.db,'center');arrow([[240,541],[273,541]],C.db);
mod('任务模型 θ*',277,479,246,66,C.gold,C.orange,26);tx('原图与三种翻转共同推理',280,557,241,27,19,false,C.ink,'center');tx('共享权重',326,596,145,25,19,true,C.orange,'center');
arrow([[1012,355],[1012,393],[400,393],[400,479]],C.orange,true);
arrow([[526,513],[560,513]],C.db);
for(let i=0;i<4;i++)await img(ex(`tta_raw_${i}.png`),564+i*49,477,45,45);
arrow([[679,522],[679,535]],C.purple);mod('逆变换对齐＋分数融合',558,535,245,53,C.lav,C.purple,21);tx('四次前向，无新增参数',558,602,245,26,19,true,C.purple,'center');arrow([[803,562],[831,562]],C.dg);
await img(pic('6598','tta4'),837,477,195,130);tx('像素级道路掩膜',838,609,193,23,18,true,C.dg,'center');arrow([[1036,541],[1060,541]],C.dg);
tx('调查输出',1071,478,150,33,24,true,C.green);tx('位置叠加图\n覆盖率统计\n逐景筛查记录',1071,522,155,98,22,false,C.ink);
cap('训练与现场使用分开：用任务数据完成适配，再将模型用于批量航拍调查。');}
async function train(s){
const a=art(s),{tx,shape,box,line,arrow,img,module,vec,tensor,freeze,learn,cap}=a;
// Frozen backbone and trainable interfaces are explicitly separated by color and boundary.
a.region('(a) 冻结表征提取',40,167,581,360,C.db,'#F7FAFD');
a.region('(b) 轻量可训练接口',648,167,357,360,C.orange,'#FFFBF5');
tx('监督与输出',1040,172,197,31,23,true,C.dg,'center');
await img(pic('7301','rgb'),56,228,170,114);tx('RGB 航拍',57,349,168,26,20,true,C.db,'center');
module('视觉编码 / Projector',279,223,319,53,C.blue,C.db);freeze(578,238,11);
box(279,318,319,87,C.lav,mix(C.purple,'#FFFFFF',.4));tx('语言模型 InternVL3',288,325,300,31,23,true,C.ink,'center');
vec(298,369,9,'#C9BDDC',15,22,6);tx('SEG',507,365,75,29,20,true,C.purple,'center');freeze(578,337,11);
box(56,427,171,71,'#FFFFFF',C.edge);tx('固定分割提示\n＋ SEG 输出前缀',62,435,159,54,20,true,C.ink,'center');
module('SAM2 图像编码',279,442,163,56,C.blue,C.db);freeze(424,455,10);
tensor(473,448,40,40,C.blue,3,4);tensor(527,458,30,30,C.blue,3,3);tensor(571,467,21,21,C.blue,3,3);
tx('多尺度视觉特征',456,497,147,22,17,false,C.db,'center');
// Projection has real architecture from the loaded model, not a placeholder module.
box(665,224,323,140,C.gold,mix(C.orange,'#FFFFFF',.4));tx('SEG 提示投影 MLP',677,231,299,30,23,true,C.orange,'center');learn(967,245);
const xx=[681,788,875],ww=[86,67,97];const ls=['Linear','ReLU','Linear'];
for(let i=0;i<3;i++){module(ls[i],xx[i],283,ww[i],39,'#FFF9EA',C.orange);if(i<2)arrow([[xx[i]+ww[i],303],[xx[i+1],303]],C.orange);}
tx('3584 → 3584 → 256 维提示',680,329,291,25,20,true,C.orange,'center');
box(665,411,323,96,C.gold,mix(C.orange,'#FFFFFF',.4));tx('SAM2 掩膜解码器',679,417,296,31,24,true,C.orange,'center');learn(967,432);
module('提示 / 图像融合',680,460,152,33,'#FFFAEF',C.orange);module('掩膜预测',855,460,116,33,'#FFFAEF',C.orange);arrow([[832,476],[855,476]],C.orange);
await img(pic('7301','mask_gt'),1051,223,179,120);tx('真实受淹道路标签',1040,349,198,28,19,true,C.dg,'center');
await img(pic('7301','single_view_mask'),1051,411,179,120);tx('预测掩膜',1053,534,176,26,20,true,C.db,'center');
// Bottom: actual two supervised objectives and a clearly routed backward branch.
box(653,580,579,61,C.sage,mix(C.dg,'#FFFFFF',.35));tx('训练目标',669,591,103,37,22,true,C.dg,'center');
module('BCE',793,592,95,35,'#FFFFFF',C.dg);tx('＋',894,592,29,35,25,true,C.dg,'center');module('Dice / Lovasz',929,592,282,35,'#FFFFFF',C.dg);
tx('同步翻转与亮度、对比度增强',45,552,558,30,22,true,C.db,'center');
tx('约 17.98 M 参数，最多 1200 次更新',45,600,558,32,24,true,C.orange,'center');
arrow([[226,285],[249,285],[249,249],[279,249]],C.db);arrow([[439,276],[439,318]],C.db);arrow([[227,462],[251,462],[251,361],[279,361]],C.purple);
arrow([[141,379],[141,394],[263,394],[263,471],[279,471]],C.db);arrow([[442,470],[467,470]],C.db);arrow([[598,362],[628,362],[628,303],[665,303]],C.orange);
arrow([[827,364],[827,411]],C.orange);arrow([[604,470],[665,470]],C.db);arrow([[988,477],[1051,477]],C.orange);
arrow([[1230,284],[1245,284],[1245,610],[1232,610]],C.dg);arrow([[1141,563],[1141,580]],C.dg);
arrow([[652,609],[632,609],[632,385],[665,385],[665,364]],C.orange,true);tx('反向更新',666,375,146,26,18,true,C.orange);arrow([[632,530],[827,530],[827,507]],C.orange,true);
freeze(55,143,10);tx('冻结参数',72,130,112,28,20,true,C.db);learn(219,143);tx('参与训练',237,130,121,28,20,true,C.orange);
cap('模型底座保持冻结；监督信号通过分割损失，只更新提示投影和掩膜解码器。');
}
async function tta(s){const a=u(s),{tx,img,shape,box,ln,mod,arrow,cap}=a;
const cols=[[47,168,'输入视图'],[251,160,'共享模型'],[471,178,'翻转坐标下的预测'],[719,178,'恢复原坐标']];cols.forEach(([x,w,t])=>{tx(t,x,153,w,32,23,true,C.db,'center');ln(x,189,w);});
const names=['原图','水平翻转','垂直翻转','双向翻转'];const yy=[211,313,415,517];
shape('rect',256,209,155,402,'#FBF4E8');tx('同一权重 θ*',264,230,139,31,23,true,C.orange,'center');
mod('冻结表征',268,296,130,55,C.blue,C.db,20);mod('SEG 投影',268,386,130,55,C.gold,C.orange,20);mod('SAM2\n掩膜头',268,477,130,71,C.gold,C.orange,20);arrow([[333,351],[333,386]],C.orange);arrow([[333,441],[333,477]],C.orange);
for(let i=0;i<4;i++){const y=yy[i];await img(path.join(A,`tta_input_${i}.png`),47,y,135,90);tx(i===0?names[i]:names[i].replace('翻转','\n翻转'),187,y+19,53,53,18,true,C.ink,'center');arrow([[249,y+47],[256,y+47]],C.db);await img(ex(`tta_raw_${i}.png`),492,y,89,89);arrow([[412,y+47],[490,y+47]],C.db);tx('预测',421,y+15,63,23,17,false,C.muted,'center');await img(ex(`tta_aligned_${i}.png`),751,y,89,89);arrow([[582,y+47],[746,y+47]],C.purple);tx(i===0?'保持原方向':i===1?'水平翻回':i===2?'垂直翻回':'双向翻回',593,y+8,145,29,21,true,C.purple,'center');arrow([[842,y+47],[889,y+47]],C.dg);}
shape('line',889,258,0,306,'none',C.dg,1.5);arrow([[889,411],[930,411]],C.dg);
shape('rect',933,201,303,421,'#F1F7F2');tx('同坐标融合',945,213,278,34,27,true,C.dg,'center');
mod('平均四路 logits',952,268,264,48,C.sage,C.dg,23);tx('每个像素汇总四次判断',949,327,267,27,19,false,C.ink,'center');arrow([[1084,357],[1084,380]],C.dg);mod('恢复原尺寸＋阈值化',952,383,264,48,C.sage,C.dg,22);arrow([[1084,431],[1084,454]],C.dg);
await img(pic('6598','tta4'),954,456,260,145);tx('最终道路定位',954,600,260,25,20,true,C.dg,'center');
cap('关键：翻转会改变预测坐标，先把四路结果翻回原方向，再逐像素平均融合。');}
async function qualitative(s){const a=u(s),{tx,img,shape,ln,cap}=a;
const xs=[154,381,608,835],ww=214,heads=['原始 RGB','原始 TerraScope','本组最终配置','空间差异'];heads.forEach((h,i)=>{tx(h,xs[i],151,ww,30,22,true,i===3?C.dg:C.db,'center');ln(xs[i],187,ww);});tx('逐景发现',1071,151,163,30,23,true,C.green);ln(1071,187,163);
const rows=[['7595','交叉路口','26.66%','60.85%','恢复受淹范围\n保留道路结构'],['7301','居民区道路','31.32%','73.35%','主路识别连贯\n边缘仍有遗漏'],['7986','未淹道路','83.16%','0.00%','抑制整片误报\n未淹道路保留']];
for(let r=0;r<3;r++){const[id,desc,b,f,note]=rows[r],y=203+r*145;tx(id,40,y+29,98,32,26,true,C.green,'center');tx(desc,29,y+65,121,45,18,true,C.muted,'center');for(let c=0;c<4;c++)await img(pic(id,['rgb','baseline','tta4','difference'][c]),xs[c],y,ww,134);tx(r<2?'空间 IoU':'误报覆盖率',1072,y+3,163,25,18,false,C.muted);tx(`${b} → ${f}`,1072,y+31,163,34,20,true,r<2?C.dg:C.orange);tx(note,1072,y+81,164,48,19,true,C.ink);if(r<2)ln(40,y+139,1195);}
const ly=644;for(const[i,col,lab]of[[0,'#4C9B7D','命中'],[1,'#E1B659','遗漏'],[2,'#C67086','多检']]){shape('rect',841+i*133,ly,15,12,col);tx(lab,862+i*133,ly-7,90,25,17,false,C.muted);}
cap('典型场景显示：适配后既能恢复受淹区域，也能抑制未淹道路上的错误响应。');}
async function holdout(s){const a=u(s),{tx,img,shape,ln,heading,table,cap}=a;
heading('整体结果与逐景变化',43,148,633);heading('两处未淹场景的误报消除',718,148,519);
bar(s,['单视图','四视图'],[52.0563969,55.6850615],[DC.blue,DC.sage],47,220,290,207,65,'0.00');tx('全局 IoU（%）',58,195,270,25,20,true,C.db,'center');
bar(s,['单视图','四视图'],[10,1],[DC.blue,DC.sage],365,220,290,207,12,'0');tx('未淹影像误报数',374,195,270,25,20,true,C.db,'center');
await img(ex('holdout_per_image.png'),45,439,625,184);tx('23 幅受淹影像中，15 幅的逐景 IoU 提高',52,628,615,28,21,true,C.dg,'center');
const keys=['rgb','single_view','tta4'],hdr=['原始影像','单视图','四视图'];for(let c=0;c<3;c++)tx(hdr[c],721+c*174,195,165,26,19,true,C.db,'center');
for(let r=0;r<2;r++){const id=['7679','6480'][r],y=228+r*162;for(let c=0;c<3;c++)await img(pic(id,keys[c]),721+c*174,y,165,118);tx(`${id}：误报覆盖率 ${r?'14.08':'20.76'}% → 0.00%`,722,y+121,511,29,21,true,C.orange,'center');}
shape('rect',722,568,513,79,'#F4F7F2');tx('90%',735,570,145,41,37,true,C.green,'center');tx('21 / 23',967,570,200,41,37,true,C.green,'center');tx('误报数量减少',735,614,145,25,19,false,C.ink,'center');tx('受淹场景命中保持不变',918,614,306,25,19,false,C.ink,'center');
cap('同权重比较：四视图全局 IoU 增加 3.63 个百分点，同时将 10 幅误报降至 1 幅。');}
async function application(s){const a=u(s),{tx,img,shape,ln,heading,table,cap}=a;
heading('7301：定位调查区域，并核对局部遗漏',43,147,1193);
await img(pic('7301','boxed'),44,208,598,400);
const cols=[['zoom_rgb','局部原图'],['zoom_tta4','最终预测'],['zoom_gt','真实标签'],['zoom_difference','命中、遗漏与多检']];
for(let i=0;i<4;i++){let x=681+i%2*280,y=209+Math.floor(i/2)*202;await img(pic('7301',cols[i][0]),x,y,259,162);if(i<3)tx(cols[i][1],x,y+165,259,29,22,true,C.db,'center');else for(const [j,color,label] of [[0,'#4C9B7D','命中'],[1,'#E1B659','遗漏'],[2,'#C67086','多检']]){shape('rect',x+j*86,y+174,12,12,color);tx(label,x+j*86+17,y+165,65,29,20,true,C.ink);}}
// Localized interpretation beneath the main image, with actual measurements.
tx('预测覆盖率',46,613,135,27,19,false,C.muted);tx('21.75%',183,609,145,35,29,true,C.green);tx('空间 IoU',354,613,110,27,19,false,C.muted);tx('73.35%',471,609,164,35,29,true,C.green);
tx('精确率 92.18%   召回率 78.22%',685,620,543,29,22,true,C.dg,'center');
cap('调查价值：先定位主要受淹路段，再通过局部差异图确定需要重点核查的边缘位置。');}
async function summary(s){const a=u(s),{tx,img,shape,ln}=a;
shape('rect',42,155,1196,486,'#EFF4F0');
await img(pic('7301','tta4'),42,155,663,444);
shape('rect',42,599,663,42,C.green);tx('受淹道路定位与覆盖率统计',56,602,635,35,25,true,'#FFFFFF','center');
shape('rect',705,155,533,486,C.green);
tx('本组完成',737,179,468,35,25,true,'#C4DACA');tx('轻量任务微调\n四视图稳健推理\n洪灾道路应用验证',737,229,466,123,30,true,'#FFFFFF');
ln(738,378,465,'#7FA48A',1);tx('+49.62',735,396,278,68,61,true,'#FFFFFF');tx('个百分点',1016,427,183,35,24,true,'#DCE9DE');tx('448 幅测试集的全局 IoU 提升',739,469,461,30,22,false,'#FFFFFF');
tx('90%',735,513,220,60,54,true,'#F4DCAA');tx('额外 370 幅验证\n误报数量减少',953,517,257,58,22,true,'#FFFFFF');
tx('让航拍影像成为可定位、可统计的灾后调查依据',44,660,921,35,27,true,C.green);tx('谢谢聆听',1008,654,229,43,32,true,C.green,'right');}
return{background,capability,workflow,train,tta,qualitative,holdout,application,summary};}
