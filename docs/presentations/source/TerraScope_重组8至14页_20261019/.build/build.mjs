import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {PresentationFile, FileBlob} from '@oai/artifact-tool';

const D=path.dirname(fileURLToPath(import.meta.url));
const SOURCE='/Users/chenxi/Desktop/TerraScope_课堂汇报.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(SOURCE));
const manifest=JSON.parse(await fs.readFile(path.join(D,'asset_manifest.json'),'utf8'));
const NAVY='#2F568B', INK='#203852', GREY='#617488', GREEN='#5E8156', GOLD='#BB8A35', LINE='#D6E1E8';
const FONT='Songti SC', HEAD='微软雅黑';
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
 rect(s,conclusion?1028:771,0,conclusion?252:257,70,'#31568F');
 text(s,conclusion?'结论':'实验与应用',conclusion?1028:771,0,conclusion?252:257,70,27,'#FFFFFF',true,'center',HEAD);
 text(s,title,38,83,1204,44,30,NAVY,true,'left',HEAD);
 text(s,String(n),1237,688,32,26,18,'#555555',false,'right',HEAD);
}
function footer(s,str){rule(s,38,662,1204);text(s,str,42,668,1184,30,20,NAVY);}
async function pic(s,file,x,y,w,h,alt){const b=await fs.readFile(file);s.images.add({blob:new Uint8Array(b),contentType:file.endsWith('.jpg')?'image/jpeg':'image/png',alt,fit:'contain',position:pos(x,y,w,h)});names.push({file,slide:s.id,alt});}
async function old(s,n,i,x,y,w,h,alt){const a=manifest.find(a=>a.slide===n&&a.index===i);await pic(s,a.asset,x,y,w,h,alt||`原第${n}页配图${i+1}`);}
function table(s,values,x,y,w,h,widths,size=19){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 t.borders.assign({fill:LINE,width:.65,style:'solid'});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const ce=t.getCell(r,c);ce.fill=r===0?'#DEEADB':r%2?'#FFFFFF':'#F3F6F5';
  ce.text.style={typeface:FONT,fontSize:size,bold:r===0,color:INK,alignment:c===0?'left':'center',verticalAlignment:'middle',insets:{left:9,right:6,top:3,bottom:3},autoFit:'none'};
 }
 return t;
}
// Keep six source slides and their template layouts. Charts remain native.
p.slides.keep([7,8,10,11,12,13]);
for(const [idx,s] of p.slides.items.entries()){
 const ins=await p.inspect({select:`$.slides[${idx}]`,include:['id','elements.id','elements.kind']});
 const obj=JSON.parse(ins.ndjson.split('\n').filter(Boolean)[0]);
 p.delete((obj.elements||[]).filter(e=>e.kind!=='chart').map(e=>e.id));
}
const system=p.slides.items[4].duplicate();
system.moveTo(5);
const [s8,s9,s10,s11,s12,s13,s14]=p.slides.items;

// 8: dataset, evaluation, and two-stage configuration evidence.
head(s8,8,'数据与配置选择：300 幅训练，80 幅选型，818 幅评估');
const splits=[['300','训练集','162 受淹 / 138 未淹','#EACF8C'],['80','配置验证集','30 受淹 / 50 未淹','#D8CEE9'],['448','完整测试集','49 受淹 / 399 未淹','#CEE1ED'],['370','额外验证集','23 受淹 / 347 未淹','#CFE1CA']];
splits.forEach((a,i)=>{const x=38+i*306;rect(s8,x,143,286,4,a[3]);text(s8,a[0],x,153,76,44,36,NAVY,true,'left','Times New Roman');text(s8,a[1],x+84,155,202,38,23,INK,true);text(s8,a[2],x,198,286,27,18,GREY);});
rule(s8,38,237,1204);
section(s8,'数据与三类评价',38,248,308);
await old(s8,8,0,38,293,149,100,'FloodNet RGB 航拍');await old(s8,8,1,197,293,149,100,'像素级受淹道路真实标签');
text(s8,'FloodNet RGB 航拍',38,397,149,25,15,NAVY,true,'center');text(s8,'受淹道路像素标签',197,397,149,25,16,GREEN,true,'center');
text(s8,'空间定位',38,443,90,27,19,NAVY,true);text(s8,'全局 IoU / Dice',137,443,210,27,19);
text(s8,'数值估算',38,488,90,27,19,NAVY,true);text(s8,'覆盖率 MAE（百分点）',137,488,210,27,18);
text(s8,'场景筛查',38,533,90,27,19,NAVY,true);text(s8,'命中、漏检与误报数',137,533,210,27,19);
text(s8,'按官方分区组织数据\n818 = 448 + 370，不含选型用的 80 幅',38,585,308,53,17,GREY);
section(s8,'阶段一  结构与监督探索',367,248,366);
table(s8,[['配置（400 次更新）','测试 IoU'],['分割头 + 投影层','48.81%'],['再加 LoRA（三次均值）','49.73%'],['残差细节模块','47.63%'],['细节模块 + 边界监督','46.56%'],['细节模块 + 道路辅助','48.77%'],['组合方案','48.35%']],367,293,366,274,[267,99],17);
text(s8,'主要收益来自任务适配\n新增模块未稳定提升整体 IoU',367,578,366,62,20,GREEN,true,'center');
section(s8,'阶段二  训练与目标函数',759,248,483);
await old(s8,10,0,759,291,483,341,'原配置选择图：更新次数与验证 IoU、三种随机种子的测试 IoU');
text(s8,'两种目标 × 三种子，每次最多 1200 次更新',759,634,483,24,17,NAVY,false,'center');
footer(s8,'80 幅验证集选择权重，再比较单视图与四视图部署。448 幅与额外 370 幅分别报告结果。');
s8.speakerNotes.text='来源：最新主稿原第8、10页及实验辅助材料。300用于训练，80用于配置选择，818仅指448+370。LoRA为三次均值，其余模块不宜作严格统计优势判断。最终权重long_bce_lovasz_seed20261017，由80幅验证集选定。验证集单视图IoU61.29%，四视图63.92%。两目标均有种子波动，不应将Lovasz解释为普遍更优。';

// 9: original native chart, native comparison table and both scene images.
head(s9,9,'完整测试集：定位改善，同时控制场景误报');
section(s9,'448 幅测试集的全局 IoU（%）',38,147,705);
section(s9,'覆盖率估算与场景筛查',786,147,456);
const c9=s9.charts.items[0];c9.position=pos(38,197,705,320);
table(s9,[['指标','原始模型','最终配置'],['覆盖率 MAE','5.05','0.83'],['未淹场景误报','169 / 399','2 / 399'],['受淹场景命中','40 / 49','44 / 49']],786,198,456,183,[196,130,130],21);
text(s9,'MAE 单位为百分点，场景阈值为占图 ≥ 1%',786,388,456,28,17,GREY);
await old(s9,9,0,786,435,218,146,'7301 原始模型预测');await old(s9,9,1,1024,435,218,146,'7301 最终配置预测');
text(s9,'7301  原始模型',786,588,218,27,18,NAVY,false,'center');text(s9,'7301  最终配置',1024,588,218,27,18,GREEN,true,'center');
rect(s9,48,535,685,94,'#F0F5EC');text(s9,'+49.62 个百分点',62,540,657,47,37,NAVY,true,'center');
text(s9,'最终四视图 58.28%，原始模型 8.66%',62,588,657,29,21,INK,false,'center');
text(s9,'四视图的取舍：较优化单视图 IoU 低 0.35 个百分点，未淹误报由 4 幅减至 2 幅。',42,637,1200,25,18,GREY);
footer(s9,'任务微调带来主要定位收益。最终配置在完整测试集上优先降低场景误报，仍需结合逐景结果核查。');
s9.speakerNotes.text='来源：最新主稿原第9页。四组IoU分别为：原始8.66、初步适配48.81、优化单视图58.63、最终四视图58.28。+49.62指最终四视图与原始模型的差值。覆盖率MAE 0.83百分点为448幅总体，不是49幅正样本的误差。单视图和四视图分别为FP4/2，TP45/44，MAE0.810/0.833，不能表述为全部指标单调提升。';

// 10: all 12 original scene images in an aligned comparison matrix.
head(s10,10,'典型场景：受淹范围恢复与未淹误报抑制');
const xs=[145,363,581,799];
['原始 RGB','原始 TerraScope','本组最终配置','空间差异'].forEach((t,i)=>{text(s10,t,xs[i],149,201,29,22,i===3?GREEN:NAVY,true,'center');rule(s10,xs[i],183,201);});
text(s10,'逐景发现',1030,149,212,29,22,NAVY,true);rule(s10,1030,183,212);
const rr=[{y:201,id:'7595',label:'交叉路口',metric:'空间 IoU',value:'26.66% 至 60.85%',desc:'恢复受淹范围\n保留道路结构'},{y:352,id:'7301',label:'居民区道路',metric:'空间 IoU',value:'31.32% 至 73.35%',desc:'主路识别连贯\n边缘仍有遗漏'},{y:503,id:'7986',label:'未淹道路',metric:'误报覆盖率',value:'83.16% 至 0.00%',desc:'抑制整片误报\n保留未淹道路'}];
for(let r=0;r<3;r++){
 const q=rr[r];text(s10,q.id,38,q.y+32,93,35,26,NAVY,true,'center','Times New Roman');text(s10,q.label,38,q.y+74,93,40,18,GREY,false,'center');
 for(let c=0;c<4;c++)await old(s10,11,r*4+c,xs[c],q.y,201,134,`${q.id} ${['原始RGB','原始模型','最终配置','空间差异'][c]}`);
 text(s10,q.metric,1030,q.y,212,25,18,GREY);text(s10,q.value,1030,q.y+29,212,30,21,r===2?GOLD:GREEN,true);text(s10,q.desc,1030,q.y+76,212,52,21,INK);
 if(r<2)rule(s10,38,q.y+142,1204);
}
text(s10,'差异图图例：命中（绿）  遗漏（金）  多检（粉）',702,639,540,23,17,GREY,false,'right');
footer(s10,'典型场景显示：适配后能恢复主要受淹区域，并抑制未淹道路上的错误响应。');
s10.speakerNotes.text='来源：最新主稿原第11页。空间差异颜色按原图：绿色为TP、金色为FN、粉色为FP。逐景指标不能替代测试集总体指标。';

// 11: native aggregate charts + full 23-scene plot + both three-image case rows.
head(s11,11,'额外 370 幅验证：四视图减少误报，定位整体改善');
section(s11,'同一权重的单视图与四视图比较',38,147,623);
section(s11,'两处未淹场景的误报消除',699,147,543);
text(s11,'全局 IoU（%）',62,193,270,28,22,NAVY,true,'center');text(s11,'347 幅未淹影像的误报数',350,193,305,28,20,NAVY,true,'center');
s11.charts.items[0].position=pos(44,223,291,211);s11.charts.items[1].position=pos(350,223,307,211);
await old(s11,12,0,64,452,585,223,'23幅受淹影像的单视图和四视图逐景IoU排序散点图');
// Move complete scatter upward enough to leave room for its interpretation.
s11.images.items[0].position=pos(64,444,585,195);
text(s11,'23 幅受淹影像：15 幅提高，7 幅降低，1 幅不变',38,637,623,25,19,GREEN,true,'center');
['原始影像','单视图','四视图'].forEach((t,i)=>text(s11,t,699+i*184,193,174,28,20,NAVY,true,'center'));
for(let i=0;i<3;i++)await old(s11,12,1+i,699+i*184,231,174,130.5,`7679 ${['RGB','单视图','四视图'][i]}`);
text(s11,'7679  误报覆盖率由 20.76% 降为 0.00%',699,366,543,31,21,GOLD,true,'center');
for(let i=0;i<3;i++)await old(s11,12,4+i,699+i*184,414,174,130.5,`6480 ${['RGB','单视图','四视图'][i]}`);
text(s11,'6480  误报覆盖率由 14.08% 降为 0.00%',699,549,543,31,21,GOLD,true,'center');
rect(s11,699,594,543,61,'#F0F5EC');text(s11,'误报数减少 90%',713,600,238,43,25,NAVY,true);text(s11,'命中保持 21 / 23',968,600,260,43,25,NAVY,true);
footer(s11,'全局 IoU 增加 3.63 个百分点，误报由 10 幅减至 1 幅。额外样本仍属于同一洪灾事件。');
s11.speakerNotes.text='来源：最新主稿原第12页。IoU52.06%至55.69%，误报10至1，减幅90%，命中21/23不变。这里比较同一权重下single与tta4，不能将90%解释为所有测试集或跨灾害泛化结论。';

// 12: whole image and four aligned crops, metrics explicitly whole-image.
head(s12,12,'调查应用：道路定位、覆盖率与局部核查');
section(s12,'7301  先定位主要受淹路段，再核对边缘遗漏',38,147,1204);
await old(s12,13,0,38,204,598,400,'7301整幅预测及局部核查框');
await old(s12,13,1,695,204,225,185.3,'7301同一窗口局部原图');await old(s12,13,2,992,204,225,185.3,'7301同一窗口最终预测');
text(s12,'局部原图',695,391,225,26,21,NAVY,true,'center');text(s12,'最终预测',992,391,225,26,21,NAVY,true,'center');
await old(s12,13,3,695,427,225,185.3,'7301同一窗口真实标签');await old(s12,13,4,992,427,225,185.3,'7301同一窗口空间差异图');
text(s12,'真实标签',695,613,225,27,21,NAVY,true,'center');text(s12,'空间差异',992,613,225,27,21,NAVY,true,'center');
text(s12,'整幅指标',38,613,94,29,18,GREY);text(s12,'覆盖率 21.75%     IoU 73.35%',137,609,499,35,24,NAVY,true);
text(s12,'精确率 92.18%   召回率 78.22%',38,642,598,21,17,GREY);
text(s12,'差异图：绿为命中，金为遗漏，粉为多检',679,641,563,22,17,GREY,false,'center');
footer(s12,'覆盖率为预测受淹道路像素占有效图像的比例。真实标签与差异图用于有标注样本的局部核查。');
s12.speakerNotes.text='来源：最新主稿原第13页及原始结果。局部配图采用相同裁切窗口(60,100,655,590)。IoU73.35%、Precision92.18%、Recall78.22%和覆盖率21.75%均为整幅7301影像，不是右侧局部窗口指标。覆盖率=152585/701440。并非道路面积受淹比例，也不直接表示积水深度或可通行性。新影像没有GT时只能输出预测、覆盖率与人工复核结果。';

// 13: all three UI screenshots with system-wide capabilities.
head(s13,13,'系统展示：影像入库、模型分析、人工复核与成果导出');
text(s13,'一次完整流程：创建项目，导入 7598，A800 四视图推理，对照图层，保存复核 v1，导出报告',38,137,1204,31,21,NAVY,true);
await pic(s13,path.join(D,'assets/system_image1.jpg'),38,190,739,416,'7598调查工作台：模型结果、覆盖率与人工复核范围');
text(s13,'② 分析与复核工作台',38,169,739,24,18,NAVY,true);
await pic(s13,path.join(D,'assets/system_image2.jpg'),805,190,437,246,'影像库：筛选1198幅影像、GPS标记并导入项目');
text(s13,'① 影像库与项目导入',805,169,437,24,18,NAVY,true);
await pic(s13,path.join(D,'assets/system_image3.jpg'),805,453,437,246,'误差图层：命中、误报、漏检与复核多边形');
text(s13,'③ 图层对照与误差核查',805,434,437,24,18,NAVY,true);
// Main image caption and compact, editable function overview on the left.
// Put the function overview across a white band within the main column's lower region.
rect(s13,38,515,739,183,'#FFFFFF');rule(s13,38,515,739);
text(s13,'系统功能与优势',38,519,739,27,21,NAVY,true);
text(s13,'项目协作 / 影像库 / 实时任务 / 调查工作台\n人工复核 / 实验对比 / 成果导出 / 权限与审计',38,552,739,48,19,INK);
text(s13,'可核查：原图、预测、GT、误差图同窗对照，支持像素查询。\n可追溯：输入哈希、模型与策略、复核版本、报告快照及证据包。\n按需调用 GPU：本地保留历史结果，支持 PDF、CSV 和 GIS 点位导出。',38,605,739,65,17,INK);
text(s13,'1198 幅影像，895 幅带 GPS。GPS 为拍摄点，当前结果采用像素统计。',38,677,739,22,16,GREY);
// The main screenshot uses a dedicated full-frame region above the notes.
s13.images.items[0].position=pos(38,190,562,316);
text(s13,'7598 单景',622,204,155,27,20,NAVY,true);
text(s13,'33.60%',622,247,155,43,31,NAVY,true,'left','Times New Roman');
text(s13,'预测覆盖率',622,287,155,27,18,GREY);
text(s13,'85.05%',622,331,155,43,31,GREEN,true,'left','Times New Roman');
text(s13,'空间 IoU',622,371,155,27,18,GREY);
text(s13,'复核 v1\n锁定报告快照',622,429,155,61,20,INK);
s13.speakerNotes.text='来源：01_展示流程与PPT配文.docx、02_系统功能与优势说明.docx，展示交付_20261019。展示流程覆盖影像库导入、分析工作台、误差核查与报告导出。7598为holdout单景，1024×685，无GPS。tta4预测235695像素/701440有效像素，覆盖率33.60%，IoU85.05%，Precision89.51%，Recall94.47%，覆盖率MAE1.7652百分点。这不是448幅整体结果。真实A800模型推理约1.48秒，单次任务约3.14秒，仅为此次任务记录。系统还支持历史结果匹配、外部掩码、任务日志与重试、同步缩放和透明度/卷帘、多边形复核及版本、逐景实验和CSV、PDF与掩码/JSON/证据ZIP、SHA256清单、GPS点GeoJSON、角色权限及审计。1796份历史掩码=898幅验证/测试/holdout×2策略。';

// 14: original summary photograph plus precise comparison denominators.
head(s14,14,'本组工作：任务适配、稳健推理与调查系统',true);
await old(s14,14,0,38,160,649,434.1,'7301受淹道路预测叠加图');
rect(s14,38,594,649,43,'#E9EFF0');text(s14,'受淹道路定位与覆盖率统计',51,597,623,36,25,NAVY,true,'center');
rect(s14,711,160,531,477,'#243F62');
text(s14,'本组完成',738,179,474,35,28,'#FFFFFF',true);
text(s14,'轻量任务微调与四视图推理\n洪灾道路实验和调查应用验证\n影像、复核、报告一体化系统',738,229,474,108,26,'#FFFFFF');
rule(s14,738,359,474,'#7D96AB');
text(s14,'+49.62 个百分点',738,377,474,55,39,'#FFFFFF',true);
text(s14,'448 幅测试集的全局 IoU\n最终四视图 58.28%，原始模型 8.66%',738,438,474,54,21,'#FFFFFF');
text(s14,'误报数减少 90%',738,512,474,48,34,'#D9E6CE',true);
text(s14,'额外 370 幅，同一权重单视图与四视图比较\n347 幅未淹影像中，误报由 10 幅减至 1 幅',738,567,474,51,19,'#FFFFFF');
text(s14,'让航拍影像成为可定位、可统计、可追溯的灾后调查依据',38,661,979,37,24,NAVY,true);
text(s14,'谢谢聆听',1053,654,189,44,30,NAVY,true,'right');
s14.speakerNotes.text='来源：最新主稿原第14页和系统说明。本组成果包括轻量任务微调、四视图推理、洪灾道路应用验证与调查系统。+49.62个百分点比较448幅测试集中最终四视图与原始TerraScope。90%比较额外370幅同一权重单/四视图的负样本误报数10与1。';

await fs.writeFile(path.join(D,'placement_manifest.json'),JSON.stringify(names,null,2));
await fs.writeFile(path.join(D,'final-inspection.ndjson'),(await p.inspect({kind:'slide,table,chart',maxChars:100000})).ndjson);
await (await PresentationFile.exportPptx(p)).save(path.join(D,'candidate.pptx'));
console.log('Exported',p.slides.items.length,'slides',names.length,'images');
