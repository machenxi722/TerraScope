import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';
process.env.RUNTIME_NODE_MODULES='/Users/zhangchunhe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';

const ROOT=process.cwd();
const OUT=path.join(ROOT,'outputs/TerraScope_全部图件_清新论文版');
const TMP=path.join(ROOT,'work/paper_figures/ppt_build');
const SKILL='/Users/zhangchunhe/.codex/plugins/cache/openai-primary-runtime/presentations/26.1011.11113/skills/presentations';
const PY='/Users/zhangchunhe/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
const C={ink:'#303B40',muted:'#6D777B',edge:'#95A3A7',grid:'#E3E9E9',blue:'#B8D2DC',green:'#BCD8C5',lav:'#C8BEDC',gold:'#F3D4A0',rose:'#DDB3B8',grey:'#DFE5E6',db:'#507C91',dg:'#547C65',dl:'#7A689B',da:'#A67C3F'};
const data=JSON.parse(await fs.readFile(path.join(OUT,'本地素材/流程图数据.json'),'utf8'));
const ex=data.example;
const presentation=Presentation.create({slideSize:{width:1920,height:1080}});
const slide=presentation.slides.add();slide.background.fill='#FFFFFF';
function shape(geometry,x,y,w,h,fill='none',stroke='none',lw=0,name=''){
 return slide.shapes.add({geometry,name,position:{left:x,top:y,width:w,height:h},fill,line:{style:'solid',fill:stroke,width:lw}});
}
function text(s,x,y,w,h,size=24,color=C.ink,bold=false,align='left'){
 const t=shape('textbox',x,y,w,h);t.text=s;
 t.text.style={fontSize:size,typeface:'Songti SC',color,bold,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'none',insets:0};
 // Each Latin or numeric run uses Times New Roman.
 t.text=s.split('\n').map(line=>({runs:(line.match(/[\x20-\x7e]+|[^\x20-\x7e]+/g)||['']).map(run=>({run,style:{typeface:/^[\x20-\x7e]+$/.test(run)?'Times New Roman':'Songti SC'}}))}));
 return t;
}
function rect(x,y,w,h,fill='white',edge=C.edge){return shape('roundRect',x,y,w,h,fill,edge,1);}
function rule(x,y,w,col=C.grid){return shape('line',x,y,w,0,'none',col,1);}
function tag(s,x,y,w,c){rect(x,y,w,44,c,'none');text(s,x+10,y,w-20,44,23,C.ink,true);}
function arrow(x,y,w=26,h=30,c=C.edge){shape('rightArrow',x,y,w,h,c,'none');}
function down(x,y){shape('downArrow',x,y,28,30,C.edge,'none');}
async function pic(name,x,y,w,h){const bytes=await fs.readFile(path.join(OUT,'本地素材',name));return slide.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',position:{left:x,top:y,width:w,height:h},fit:'contain',alt:name});}
function heading(col,y,s){const x=xs[col];text(s,x+16,y,326,40,25,C.ink,true);rule(x+16,y+44,326);}
function inner(col,y,h){const x=xs[col];return rect(x+10,y,338,h,'#FFFFFF',C.grid);}
const xs=[24,403,782,1161,1540],width=356;
text('TerraScope 遥感证据核验与洪灾调查筛查',28,24,1500,60,43,C.ink,true);
text('模型复现、数值核算、复核策略与道路应用',30,83,1400,36,24,C.muted);
const heads=[['TerraScope','回答与分割证据'],['A / B / C 对照','发现数值偏差'],['证据核验','几何核算与一致性'],['洪灾调查筛查','排序与人工复核'],['评价实际效果','命中与数值误差']];
const colors=[C.blue,C.lav,C.gold,C.rose,C.green];
for(let i=0;i<5;i++){
 const x=xs[i];rect(x,141,width,909,'#FFFFFF',C.edge);rect(x,141,width,95,colors[i],'none');
 shape('ellipse',x+14,154,53,53,[C.db,C.dl,C.da,C.da,C.dg][i],'none');text(String(i+1),x+14,154,53,53,35,'#FFFFFF',true,'center');
 text(heads[i][0],x+80,151,263,42,30,C.ink,true,'center');text(heads[i][1],x+80,190,263,38,26,C.ink,true,'center');
 if(i<4)arrow(x+359,578,18,30);
}

// 1. Model input and output.
inner(0,249,287);heading(0,258,'1.1  遥感影像输入');
await pic('FloodNet_7571_rgb.png',xs[0]+24,313,309,174);text('FloodNet 7571 灾后航拍',xs[0]+25,492,308,35,21,C.muted,false,'center');
down(xs[0]+165,538);
inner(0,578,207);heading(0,587,'1.2  TerraScope 模型');
rect(xs[0]+52,649,254,58,C.blue,'none');text('InternVL3 + SAM2',xs[0]+55,652,248,52,28,C.ink,true,'center');
text('问题：识别影像中的水面\n输出：文字回答与像素掩膜',xs[0]+24,716,307,57,23);
down(xs[0]+165,788);
inner(0,827,207);heading(0,835,'1.3  像素证据');
await pic('FloodNet_7571_road_water.png',xs[0]+25,889,181,124);
text('水面掩膜\n与道路位置\n共同核查',xs[0]+222,892,112,114,23,C.db,true);

// 2. Actual ABC numerical answers on one labeled image.
const x2=xs[1];
for(let j=0;j<3;j++){
 const y=249+j*191;inner(1,y,177);heading(1,y+9,['2.1  A 通用视觉语言模型','2.2  B TerraScope 原答','2.3  C 同一掩膜重新核算'][j]);
 await pic('Ghana_406026_rgb.png',x2+27,y+63,124,80);
 if(j>0)await pic('Ghana_406026_p1_mask.png',x2+164,y+63,124,80);
 else text('直接生成\n数值答案',x2+170,y+61,145,74,24,C.muted);
 text(['回答 11.00%','回答 5.00%','核算 1.56%'][j],x2+28,y+146,300,28,22,j===2?C.dg:C.db,true);
}
inner(1,832,202);heading(1,843,'2.4  发现证据偏差');
text('同一影像，数值存在差异\n人工参考水体覆盖率 1.64%',x2+24,901,308,66,24);
tag('Ghana_406026',x2+22,980,313,C.green);

// 3. Geometry calculation and prompt consistency on local evidence.
const x3=xs[2];inner(2,249,250);heading(2,258,'3.1  掩膜几何核算');
await pic('India_747992_p1_mask.png',x3+27,318,132,109);await pic('India_747992_p2_mask.png',x3+190,318,132,109);
text('P1 '+ex.p[0].toFixed(2)+'%',x3+28,429,130,32,23,C.db,true,'center');text('P2 '+ex.p[1].toFixed(2)+'%',x3+190,429,132,32,23,C.da,true,'center');
text('覆盖率 = 水体像元 / 有效像元',x3+22,466,312,31,21,C.ink,true,'center');
inner(2,515,251);heading(2,524,'3.2  一致性与入选检查');
text('✓  答案与掩膜数值是否一致\n✓  两种提示预测是否分歧\n✓  分歧是否改变名单入选',x3+25,594,307,120,23);
tag('把核验结果用于复核排序',x3+20,711,315,C.gold);
down(x3+165,775);
inner(2,818,216);heading(2,826,'3.3  分歧案例核验');
await pic('India_747992_reference.png',x3+24,888,155,126);
text('人工参考\n'+ex.reference_pct.toFixed(2)+'%\n复核找回遗漏',x3+192,884,139,126,24,C.dg,true);

// 4. Actual model-ranked candidate chips.
const x4=xs[3];inner(3,249,479);heading(3,259,'4.1  候选区域排序');
text('71 幅中选 Top 24 调查区域',x4+25,309,306,37,23);
for(let j=0;j<3;j++){
 const r=data.ranking[j],y=358+j*113;shape('ellipse',x4+21,y+31,37,37,C.gold,'none');text(String(j+1),x4+21,y+31,37,37,23,C.ink,true,'center');
 await pic(r.id+'_rank.png',x4+73,y+3,89,88);
 text(r.id.replace('_','\n'),x4+177,y+3,143,57,20,C.ink,true);
 text('覆盖率 '+r.p[0].toFixed(1)+'%',x4+177,y+63,148,30,21,C.db);
 rule(x4+24,y+101,305);
}
text('按入选翻转与边界分歧排序',x4+24,692,306,29,21,C.muted);
down(x4+165,737);
inner(3,782,252);heading(3,791,'4.2  固定预算复核');
tag('复核预算 16 / 71 幅',x4+21,855,315,C.rose);
text('先确定需要检查的样本\n揭示选中样本的人工参考\n未复核样本保留原预测',x4+24,914,308,88,23);
text('理想人工复核模拟',x4+24,1000,308,29,21,C.muted);

// 5. Native charts with real values.
const x5=xs[4];inner(4,249,296);heading(4,258,'5.1  调查名单命中数');
text('71 幅筛查，Top 24 命中',x5+23,308,307,30,21,C.muted);
function chart(y,vals,cats,cols,max,unit,format='0'){
 const ch=slide.charts.add('bar',{position:{left:x5+24,top:y,width:307,height:186},categories:cats,
  series:[{name:unit,values:vals,fill:cols[0],points:cols.map((fill,idx)=>({idx,fill,line:{fill:C.edge,width:1,style:'solid'}}))}],hasLegend:false,
  barOptions:{direction:'column',grouping:'clustered',gapWidth:90,varyColors:true},
  xAxis:{textStyle:{fontSize:19,fill:C.ink},line:{style:'solid',fill:C.ink,width:1},majorGridlines:null},
  yAxis:{min:0,max,majorUnit:max/4,textStyle:{fontSize:17,fill:C.ink},line:{style:'solid',fill:C.ink,width:1},majorGridlines:{style:'dash',fill:C.grid,width:1}},
  dataLabels:{showValue:true,position:format==='0'?'inEnd':'outEnd',numberFormatCode:format,textStyle:{fontSize:25,bold:true,fill:C.ink}},chartFill:'none',chartLine:{fill:'none',width:0,style:'solid'},plotAreaFill:'none',plotAreaLine:{fill:'none',width:0,style:'solid'}});
 ch.xAxis.textStyle.typeface='Songti SC';ch.yAxis.textStyle.typeface='Times New Roman';ch.dataLabels.textStyle.typeface='Times New Roman';
 return ch;
}
chart(344,[14,18,18],['不复核','提示分歧','入选边界'],[C.grey,C.blue,C.gold],24,'命中数');
inner(4,564,286);heading(4,572,'5.2  覆盖率数值误差');
text('12 幅面积对照，MAE（百分点）',x5+23,621,307,30,21,C.muted);
chart(654,[8.87,4.08,1.72],['A','B','C'],[C.grey,C.blue,C.green],12,'MAE','0.00');
inner(4,868,166);heading(4,877,'5.3  道路应用效果');
text('受淹场景检出 11 / 12\n漏检 1 张，误报 3 张',x5+24,938,308,66,27,C.dg,true);

slide.speakerNotes.text='图片均取自本地实验数据。A/B/C 例子为 Sen1Floods11 Ghana_406026，A=11.00%，B=5.00%，C=1.5647888%，人工参考=1.6422272%。P1/P2 分歧案例 India_747992 在有效标注范围内、排除 JRC 常年水体后的数值为'+ex.p.map(x=>x.toFixed(2)).join('/')+'%，人工参考'+ex.reference_pct.toFixed(2)+'%。调查名单筛查基于71幅影像，复核16幅是揭示公开标签的理想模拟。命中数为14、18、18，入选边界未优于提示词分歧。12幅面积对照MAE=8.87/4.08/1.72百分点。FloodNet道路应用24幅中TP11、FN1、FP3、TN9；道路底图由标签合并。没有新增训练权重。原始统计：outputs/TerraScope_洪灾水体/confirmation_review_simulation.json、confirmation_ABC_complete_scores.json、flood_ABC_summary.json；work/floodnet/simple_evaluation_exposure.json。';
await fs.mkdir(TMP,{recursive:true});
const png=await presentation.export({slide,format:'png',scale:1.5});await fs.writeFile(path.join(TMP,'preview.png'),new Uint8Array(await png.arrayBuffer()));
const overview=await presentation.export({slide,format:'png',scale:5/3});await fs.writeFile(path.join(OUT,'PNG/01_研究主线.png'),new Uint8Array(await overview.arrayBuffer()));
const layout=await slide.export({format:'layout'});await fs.writeFile(path.join(TMP,'layout.json'),await layout.text());
const candidatePath=path.join(TMP,'candidate.pptx');await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const finalPath=path.join(OUT,'TerraScope_五栏总流程_可编辑.pptx');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath,finalPath,pythonExecutable:PY,
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','18288000,10287000','--validate-heading-fit'],
 explicitTotalSlideCount:1,requiredNativeChartOwnerSlides:[1],materializeLiteralChartWorkbooks:true,
 fontPolicy:{basis:'design',families:['Songti SC','Times New Roman']},verifyArtifactToolImport:true,
 receiptPath:path.join(TMP,'validation.json')});
console.log(JSON.stringify(result));
