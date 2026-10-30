import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {PresentationFile, FileBlob} from '@oai/artifact-tool';

const D=path.dirname(fileURLToPath(import.meta.url));
const SOURCE='/Users/chenxi/Desktop/商用时空信息软件平台/outputs/TerraScope_重组8至14页_20261019/TerraScope_第8至14页_实验与系统展示_重组版.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(SOURCE));
const manifest=JSON.parse(await fs.readFile(path.join(D,'asset_manifest.json'),'utf8'));
const NAVY='#15344E', INK='#1D2B36', GREY='#435565', GREEN='#245B50', GOLD='#8F6326', LINE='#99ACB8';
const FONT='微软雅黑', HEAD='微软雅黑';
const pos=(x,y,w,h)=>({left:x,top:y,width:w,height:h});
const names=[];
function rect(s,x,y,w,h,fill,stroke='none',sw=0){return s.shapes.add({geometry:'rect',name:'区域底色',position:pos(x,y,w,h),fill,line:{fill:stroke,width:sw}});}
function text(s,str,x,y,w,h,size=22,color=INK,bold=false,align='left',font=FONT){
 const e=s.shapes.add({geometry:'textbox',name:str.replace(/\n/g,' ').slice(0,70),position:pos(x,y,w,h),fill:'none',line:{fill:'none',width:0}});
 e.text=str;e.text.style={fontSize:size,typeface:font,color,bold,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:0};return e;
}
function rule(s,x,y,w,color=LINE){rect(s,x,y,w,1,color);}
function section(s,str,x,y,w){text(s,str,x,y,w,28,23,NAVY,true);rule(s,x,y+33,w);}
function head(s,n,title,conclusion=false){
 rect(s,conclusion?1028:771,0,conclusion?252:257,70,'#15344E');
 text(s,conclusion?'结论':'实验与应用',conclusion?1028:771,0,conclusion?252:257,70,27,'#FFFFFF',true,'center',HEAD);
 text(s,title,38,83,1204,44,30,NAVY,true,'left',HEAD);
 text(s,String(n),1237,688,32,26,18,'#555555',false,'right',HEAD);
}
function footer(s,str){rule(s,38,656,1204);text(s,str,42,662,1180,43,19,INK);}
async function pic(s,file,x,y,w,h,alt){const b=await fs.readFile(file);s.images.add({blob:new Uint8Array(b),contentType:file.endsWith('.jpg')?'image/jpeg':'image/png',alt,fit:'contain',position:pos(x,y,w,h)});names.push({file,slide:s.id,alt});}
async function old(s,n,i,x,y,w,h,alt){const a=manifest.find(a=>a.slide===n&&a.index===i);await pic(s,a.asset,x,y,w,h,alt||`原第${n}页配图${i+1}`);}
function table(s,values,x,y,w,h,widths,size=19){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 t.borders.assign({fill:LINE,width:.65,style:'solid'});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const ce=t.getCell(r,c);ce.fill=r===0?NAVY:r%2?'#FFFFFF':'#EDF1F3';
  ce.text.style={typeface:FONT,fontSize:size,bold:r===0,color:r===0?'#FFFFFF':INK,alignment:c===0?'left':'center',verticalAlignment:'middle',insets:{left:9,right:6,top:3,bottom:3},autoFit:'none'};
 }
 return t;
}
// Keep six source slides and their template layouts. Charts remain native.

for(const [idx,s] of p.slides.items.entries()){
 const ins=await p.inspect({select:`$.slides[${idx}]`,include:['id','elements.id','elements.kind']});
 const obj=JSON.parse(ins.ndjson.split('\n').filter(Boolean)[0]);
 p.delete((obj.elements||[]).filter(e=>e.kind!=='chart').map(e=>e.id));
}

const [s8,s9,s10,s11,s12,s13,s14]=p.slides.items;

// 8: dataset, evaluation, and two-stage configuration evidence.
head(s8,8,'数据与配置选择：300 幅训练，80 幅选型，818 幅评估');
const splits=[['300','训练集','162 受淹 / 138 未淹','#8F6326'],['80','配置验证集','30 受淹 / 50 未淹','#52617B'],['448','完整测试集','49 受淹 / 399 未淹','#235572'],['370','额外验证集','23 受淹 / 347 未淹','#245B50']];
splits.forEach((a,i)=>{const x=38+i*306;rect(s8,x,143,286,4,a[3]);text(s8,a[0],x,153,76,44,36,NAVY,true,'left','Times New Roman');text(s8,a[1],x+84,155,202,38,23,INK,true);text(s8,a[2],x,198,286,27,18,GREY);});
rule(s8,38,237,1204);
section(s8,'数据与三类评价',38,248,308);
await old(s8,8,0,38,293,149,100,'FloodNet RGB 航拍');await old(s8,8,1,197,293,149,100,'像素级受淹道路真实标签');
text(s8,'RGB 航拍影像',38,397,149,25,16,NAVY,true,'center');text(s8,'受淹道路像素标签',197,397,149,25,16,GREEN,true,'center');
text(s8,'以全局 IoU 和 Dice 衡量道路定位质量，以覆盖率 MAE（百分点）衡量估算误差，并结合命中、漏检和误报数量评价场景筛查效果。',38,433,308,138,19,INK);
text(s8,'FloodNet 按官方分区组织数据，以 RGB 航拍影像和像素级受淹道路标签完成监督学习。',38,575,308,67,18,GREY);
section(s8,'阶段一  结构与监督探索',367,248,366);
table(s8,[['配置（400 次更新）','测试 IoU'],['分割头 + 投影层','48.81%'],['再加 LoRA（三次均值）','49.73%'],['残差细节模块','47.63%'],['细节模块 + 边界监督','46.56%'],['细节模块 + 道路辅助','48.77%'],['组合方案','48.35%']],367,293,366,274,[267,99],17);
text(s8,'任务适配是性能提升的主要来源。新增模块未稳定提高整体 IoU，后续优化转向训练策略与部署方式。',367,577,366,76,19,INK);
section(s8,'阶段二  训练与目标函数',759,248,483);
await old(s8,10,0,759,291,483,341,'原配置选择图：更新次数与验证 IoU、三种随机种子的测试 IoU');
text(s8,'两种目标 × 三种子，每次最多 1200 次更新',759,634,483,24,17,NAVY,false,'center');
footer(s8,'依据 80 幅验证集选择权重，结合两种目标函数与三组种子的训练结果确定最终配置。\n随后在 448 幅测试集和额外 370 幅影像上，评价单视图与四视图的定位和筛查效果。');
s8.speakerNotes.text='来源：最新主稿原第8、10页及实验辅助材料。300用于训练，80用于配置选择，818仅指448+370。LoRA为三次均值。最终权重long_bce_lovasz_seed20261017，由80幅验证集选定。验证集单视图IoU61.29%，四视图63.92%。两目标的三个种子结果见图。';

// 9: original native chart, native comparison table and both scene images.
head(s9,9,'完整测试集：定位改善，同时控制场景误报');
section(s9,'448 幅测试集的全局 IoU（%）',38,147,705);
section(s9,'覆盖率估算与场景筛查',786,147,456);
const c9=s9.charts.items[0];c9.position=pos(38,197,705,320);
table(s9,[['指标','原始模型','最终配置'],['覆盖率 MAE','5.05','0.83'],['未淹场景误报','169 / 399','2 / 399'],['受淹场景命中','40 / 49','44 / 49']],786,198,456,183,[196,130,130],19);
text(s9,'MAE 单位为百分点，场景阈值为占图 ≥ 1%。',786,387,456,39,17,GREY);
await old(s9,9,0,786,435,218,146,'7301 原始模型预测');await old(s9,9,1,1024,435,218,146,'7301 最终配置预测');
text(s9,'7301  原始模型',786,588,218,27,18,NAVY,false,'center');text(s9,'7301  最终配置',1024,588,218,27,18,GREEN,true,'center');
rect(s9,48,535,685,94,NAVY);text(s9,'+49.62 个百分点',62,540,657,47,37,'#FFFFFF',true,'center');
text(s9,'最终四视图 58.28%，原始模型 8.66%',62,588,657,29,21,'#FFFFFF',false,'center');

text(s9,'任务微调使受淹道路的预测更加连续，覆盖率估算也更接近真实标签。最终配置将未淹场景误报由 169 幅降至 2 幅，并将受淹场景命中由 40 幅提高到 44 幅，增强了影像筛查的有效性。',42,642,1180,62,20,INK);
s9.speakerNotes.text='来源：最新主稿原第9页。四组IoU分别为：原始8.66、初步适配48.81、优化单视图58.63、最终四视图58.28。+49.62指最终四视图与原始模型的差值。覆盖率MAE 0.83百分点为448幅总体统计。单视图和四视图分别为FP4/2，TP45/44，MAE0.810/0.833。';

// 10: all 12 original scene images in an aligned comparison matrix.
head(s10,10,'典型场景：受淹范围恢复与未淹误报抑制');
const xs=[145,363,581,799];
['原始 RGB','原始 TerraScope','本组最终配置','空间差异'].forEach((t,i)=>{text(s10,t,xs[i],149,201,29,22,i===3?GREEN:NAVY,true,'center');rule(s10,xs[i],183,201);});
text(s10,'逐景发现',1030,149,212,29,22,NAVY,true);rule(s10,1030,183,212);
const rr=[{y:201,id:'7595',label:'交叉路口',metric:'空间 IoU',value:'26.66% 至 60.85%',desc:'预测恢复了交叉路口的受淹范围，并保留清晰的道路结构。'},{y:352,id:'7301',label:'居民区道路',metric:'空间 IoU',value:'31.32% 至 73.35%',desc:'居民区主路识别更加连贯，局部遗漏主要集中在道路边缘。'},{y:503,id:'7986',label:'未淹道路',metric:'误报覆盖率',value:'83.16% 至 0.00%',desc:'原始模型的整片误报得到消除，未淹道路被准确保留。'}];
for(let r=0;r<3;r++){
 const q=rr[r];text(s10,q.id,38,q.y+32,93,35,26,NAVY,true,'center','Times New Roman');text(s10,q.label,38,q.y+74,93,40,18,GREY,false,'center');
 for(let c=0;c<4;c++)await old(s10,11,r*4+c,xs[c],q.y,201,134,`${q.id} ${['原始RGB','原始模型','最终配置','空间差异'][c]}`);
 text(s10,q.metric,1030,q.y,212,25,18,GREY);text(s10,q.value,1030,q.y+29,212,30,19,r===2?GOLD:GREEN,true);text(s10,q.desc,1030,q.y+66,212,70,18,INK);
 if(r<2)rule(s10,38,q.y+142,1204);
}
text(s10,'差异图：命中（绿）、遗漏（金）、多检（粉）',718,637,524,22,16,GREY,false,'right');
footer(s10,'三类场景的对照结果表明，任务适配能够改善受淹范围与道路连续性，并抑制未淹道路上的误报。');
s10.speakerNotes.text='来源：最新主稿原第11页。空间差异颜色按原图：绿色为TP、金色为FN、粉色为FP。';

// 11: native aggregate charts + full 23-scene plot + both three-image case rows.
head(s11,11,'额外 370 幅验证：四视图减少误报，定位整体改善');
section(s11,'同一权重的单视图与四视图比较',38,147,623);
section(s11,'两处未淹场景的误报消除',699,147,543);
text(s11,'全局 IoU（%）',62,193,270,28,22,NAVY,true,'center');text(s11,'347 幅未淹影像的误报数',350,193,305,28,20,NAVY,true,'center');
s11.charts.items[0].position=pos(44,223,291,211);s11.charts.items[1].position=pos(350,223,307,211);
await old(s11,12,0,64,452,585,223,'23幅受淹影像的单视图和四视图逐景IoU排序散点图');
// Move complete scatter upward enough to leave room for its interpretation.
s11.images.items[0].position=pos(64,438,585,183);
text(s11,'23 幅受淹影像：15 幅提高，7 幅降低，1 幅不变',38,626,623,25,18,GREEN,true,'center');
['原始影像','单视图','四视图'].forEach((t,i)=>text(s11,t,699+i*184,193,174,28,20,NAVY,true,'center'));
for(let i=0;i<3;i++)await old(s11,12,1+i,699+i*184,231,174,130.5,`7679 ${['RGB','单视图','四视图'][i]}`);
text(s11,'7679  误报覆盖率由 20.76% 降为 0.00%',699,366,543,31,21,GOLD,true,'center');
for(let i=0;i<3;i++)await old(s11,12,4+i,699+i*184,414,174,130.5,`6480 ${['RGB','单视图','四视图'][i]}`);
text(s11,'6480  误报覆盖率由 14.08% 降为 0.00%',699,549,543,31,21,GOLD,true,'center');
rect(s11,699,592,543,61,NAVY);text(s11,'误报数减少 90%',713,598,238,43,24,'#FFFFFF',true);text(s11,'命中保持 21 / 23',968,598,260,43,24,'#FFFFFF',true);
footer(s11,'四视图融合在保持受淹场景命中的同时，削弱了未淹区域的错误响应。\n在额外 370 幅影像上，全局 IoU 提升 3.63 个百分点，未淹误报由 10 幅降至 1 幅。');
s11.speakerNotes.text='来源：最新主稿原第12页。IoU52.06%至55.69%，误报10至1，减幅90%，命中21/23不变。这里比较同一权重下single与tta4。';

// 12: full prediction, aligned crops, and an integrated interpretation.
head(s12,12,'调查应用：道路定位、覆盖率与局部核查');
section(s12,'7301 居民区道路的调查判读',38,147,1204);
await old(s12,13,0,38,204,570,381.3,'7301整幅预测及局部核查框');
await old(s12,13,1,703,204,208,171.3,'7301同一窗口局部原图');
await old(s12,13,2,1000,204,208,171.3,'7301同一窗口最终预测');
text(s12,'局部原图',703,379,208,27,20,NAVY,true,'center');
text(s12,'最终预测',1000,379,208,27,20,NAVY,true,'center');
await old(s12,13,3,703,414,208,171.3,'7301同一窗口真实标签');
await old(s12,13,4,1000,414,208,171.3,'7301同一窗口空间差异图');
text(s12,'真实标签',703,589,208,27,20,NAVY,true,'center');
text(s12,'空间差异',1000,589,208,27,20,NAVY,true,'center');
text(s12,'7301 全幅预测与局部核查窗口',38,589,570,31,21,NAVY,true);
text(s12,'命中（绿）、遗漏（金）、多检（粉）',682,618,560,22,16,GREY,false,'center');
rule(s12,38,638,1204);
text(s12,'在 7301 影像中，预测受淹道路占有效影像的 21.75%，IoU 达到 73.35%，精确率与召回率分别为 92.18% 和 78.22%。\n主路识别较为连续，局部对照进一步揭示了边缘位置的遗漏，能够据此确定调查区域和核查重点。',38,648,1184,57,20,INK);
s12.speakerNotes.text='来源：最新主稿原第13页及原始结果。局部配图采用相同裁切窗口(60,100,655,590)。整幅7301影像IoU73.35%、Precision92.18%、Recall78.22%，覆盖率=152585/701440=21.75%。';

// 13: three sequential screenshots, guided left to right.
head(s13,13,'系统展示：受淹道路调查的实际操作流程');
text(s13,'以 7598 居民区道路影像为例，系统完成影像导入、A800 四视图分析和人工复核，得到 33.60% 的预测覆盖率与 85.05% 的 IoU。预测与误差图同步展示，便于核对道路边缘，并将复核版本 v1 关联到报告快照。',38,139,1204,68,20,INK);
const steps=[
 ['1  影像入库','system_image2.jpg','在影像库中筛选影像并导入项目，建立统一的调查对象。'],
 ['2  模型分析','system_image1.jpg','A800 完成四视图推理，生成道路掩码、覆盖率与质量指标。'],
 ['3  复核交付','system_image3.jpg','对照误差图完成区域复核，将调查意见与报告快照一并保存。']
];
const stepHeads=[];
for(let i=0;i<3;i++){
 const x=38+i*415;
 stepHeads.push(text(s13,steps[i][0],x,226,235,31,24,NAVY,true));
 await pic(s13,path.join(D,'assets',steps[i][1]),x,270,374,210.375,steps[i][0]);
 text(s13,steps[i][2],x,491,374,48,18,INK);
}
for(let i=0;i<2;i++)s13.shapes.connect(stepHeads[i],stepHeads[i+1],{kind:'straight',fromSide:'right',toSide:'left',line:{style:'solid',fill:NAVY,width:1.8},tail:{type:'triangle',width:'sm',length:'sm'}});
rule(s13,38,551,1204);
text(s13,'调查协作与成果交付',38,565,1204,34,25,NAVY,true);
text(s13,'系统以项目组织调查工作，成员可按权限共同查看历史实验与实时任务，在工作台中对照图层、复核区域并整理报告。报告、统计表和 GIS 点位随调查结果输出，输入影像、模型策略、复核版本与审计记录同步保存，便于回查分析依据。GPU 按需承担新影像推理，已有结果和报告保留在本地继续使用，减少重复计算与跨工具传递。',38,608,1184,91,20,INK);
s13.speakerNotes.text='来源：01_展示流程与PPT配文.docx、02_系统功能与优势说明.docx。7598为holdout单景，1024×685。tta4预测235695像素/701440有效像素，覆盖率33.60%，IoU85.05%，Precision89.51%，Recall94.47%。复核v1与报告快照关联。影像库1198幅，895幅带拍摄点GPS。系统支持历史结果匹配、外部掩码、任务日志、同步缩放、多边形复核及版本、实验比较、PDF、CSV、GeoJSON、掩码和证据ZIP，含角色权限及审计。';

// 14: original summary photograph plus precise comparison denominators.
head(s14,14,'本组成果：道路识别优化与调查系统实现',true);
await old(s14,14,0,38,160,649,434.1,'7301受淹道路预测叠加图');
rect(s14,38,594,649,43,'#D8E1E7');text(s14,'受淹道路定位与覆盖率统计',51,597,623,36,25,NAVY,true,'center');
rect(s14,711,160,531,477,'#102D43');
text(s14,'本组完成',738,179,474,35,28,'#FFFFFF',true);
text(s14,'本组围绕受淹道路识别完成了轻量任务微调、四视图推理与洪灾道路应用验证，并将实验结果接入调查系统，支持影像分析、人工复核和成果输出。',738,226,474,118,23,'#FFFFFF');
rule(s14,738,359,474,'#7D96AB');
text(s14,'+49.62 个百分点',738,377,474,55,39,'#FFFFFF',true);
text(s14,'448 幅测试集的全局 IoU\n最终四视图 58.28%，原始模型 8.66%',738,438,474,54,21,'#FFFFFF');
text(s14,'误报数减少 90%',738,512,474,48,34,'#D9E6CE',true);
text(s14,'额外 370 幅，同一权重单视图与四视图比较\n347 幅未淹影像中，误报由 10 幅减至 1 幅',738,567,474,51,19,'#FFFFFF');
text(s14,'研究成果支持受淹道路的定位调查、覆盖率统计和人工复核。',38,661,979,37,23,NAVY);
text(s14,'谢谢聆听',1053,654,189,44,30,NAVY,true,'right');
s14.speakerNotes.text='来源：最新主稿原第14页和系统说明。本组成果包括轻量任务微调、四视图推理、洪灾道路应用验证与调查系统。+49.62个百分点比较448幅测试集中最终四视图与原始TerraScope。90%比较额外370幅同一权重单/四视图的负样本误报数10与1。';

await fs.writeFile(path.join(D,'placement_manifest.json'),JSON.stringify(names,null,2));
await fs.writeFile(path.join(D,'final-inspection.ndjson'),(await p.inspect({kind:'slide,table,chart',maxChars:100000})).ndjson);
await (await PresentationFile.exportPptx(p)).save(path.join(D,'candidate.pptx'));
console.log('Exported',p.slides.items.length,'slides',names.length,'images');
