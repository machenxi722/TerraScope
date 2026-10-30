import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
import {art as baseArt,mix} from './styled_art.mjs';
import {figureArt} from './figure_style.mjs';
const art=s=>figureArt(baseArt(s));
const R=process.cwd(),W=path.join(R,'work/palette_refresh_20261016/figures/workflow');
const A=path.join(R,'work/final_talk_20261016/assets'),E=path.join(R,'work/editorial_v2_20261016/assets');
const data=JSON.parse(await fs.readFile(path.join(A,'data.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1600,height:900}}),s=p.slides.add();s.background.fill='#FFFFFF';
const {tx,box,shape,arrow,line,poly,freeze,learn,vec,tensor,img,layerStack}=art(s);
const C={ink:'#203653',muted:'#667485',blue:'#DCE5F4',db:'#2F5597',sage:'#DFEBCF',dg:'#68874F',orange:'#B88C32',gold:'#F6E8B8',lav:'#E4DEEC',purple:'#846C9B',rose:'#F3CFCC',red:'#B9534F',edge:'#B3C0CD'};
const lab=(t,x,y,w,h=27,size=20,col=C.ink,bold=false,align='center')=>tx(t,x,y,w,h,size,bold,col,align);
function soft(x,y,w,h,fill,edge){const b=box(x,y,w,h,fill,edge);b.line.width=.9;return b;}
function node(t,x,y,w,h,fill,col,frozen=false,trained=false,sub=''){
 soft(x,y,w,h,fill,mix(col,'#FFFFFF',.3));
 lab(t,x+10,y+(sub?9:5),w-20,h-(sub?32:10),21,C.ink,true);
 if(sub)lab(sub,x+8,y+h-27,w-16,23,16,col);
 if(frozen)freeze(x+w-12,y+11,10);if(trained)learn(x+w-12,y+11);
}
function section(letter,t,x,y,w,col,fill){
 shape('rect',x,y,w,43,fill);lab(letter,x+7,y+5,32,33,27,col,true);lab(t,x+49,y+4,w-60,35,25,col,true,'left');
}
function imageFrame(file,x,y,w,h,col=C.edge){shape('rect',x-1,y-1,w+2,h+2,'#FFFFFF',col,.8);return img(file,x,y,w,h);}
function weightCube(x,y,w,h){poly([[x,y],[x+14,y-11],[x+w+14,y-11],[x+w,y]],'#E6E4F3','#8C8DAF',1);poly([[x+w,y],[x+w+14,y-11],[x+w+14,y+h-11],[x+w,y+h]],'#CCCEE6','#8C8DAF',1);shape('rect',x,y,w,h,'#E0E4F3','#8C8DAF',1);lab('任务权重 θ*',x+10,y+11,w-20,31,24,C.ink,true);lab('验证集选择',x+10,y+45,w-20,23,18,C.purple);}

// The reference's two-stage organization remains the main composition.
lab('受淹道路识别：任务适配与调查统计',30,14,1540,47,36,C.ink,true);
lab('TerraScope 任务微调与四视图融合',30,63,1540,27,20,C.muted);
soft(25,104,681,708,'#FAFCFD','#B6CDD9');
soft(750,104,825,431,'#FBFDFC','#B7D1C0');
soft(750,550,825,262,'#FBFDFC','#B7D1C0');
section('A','离线训练：适配受淹道路任务',35,113,661,C.db,C.blue);
section('B','模型使用：四视图推理与融合',760,113,805,C.dg,C.sage);
section('C','调查输出：空间定位与逐景统计',760,559,805,C.dg,C.sage);

// A: Actual dataset and paired labels, one forward computation graph.
lab('FloodNet 航拍数据',47,180,163,28,22,C.db,true);
await imageFrame(path.join(E,'train_6597_rgb.png'),55,229,151,101);
lab('训练影像 RGB',55,333,151,24,18,C.ink,true);
await imageFrame(path.join(E,'train_6597_gt.png'),55,433,151,101);
lab('受淹道路标注 GT',49,537,166,25,18,C.ink,true);
lab('300 幅训练影像',47,577,168,26,21,C.db,true);
lab('RGB 与标签成对输入',47,606,168,24,16,C.muted);

lab('任务指令：分割影像中的受淹道路',238,175,432,27,20,C.ink,true);
soft(232,211,441,353,'#FFFFFF','#D8E1E5');
arrow([[346,204],[346,231]],C.db);
// Image pathways.
arrow([[206,279],[220,279],[220,267],[248,267]],C.db);
line(220,279,220,390,C.db,1.5);arrow([[220,390],[248,390]],C.db);
node('视觉编码器\n＋ InternVL3',248,232,197,80,C.blue,C.db,true,false);
node('SEG 投影',480,240,175,64,C.gold,C.orange,false,true,'3584 → 256');
arrow([[445,270],[480,270]],C.orange);
lab('[SEG]',441,217,50,21,15,C.orange,true);
node('SAM2 图像编码器',248,355,197,70,C.blue,C.db,true,false,'提取多尺度特征');
node('SAM2 掩膜解码器',480,355,175,80,C.gold,C.orange,false,true);
arrow([[568,304],[568,355]],C.orange);
vec(523,320,4,'#E3A6A1',14,17,6);
lab('分割提示',601,314,64,26,16,C.orange);
arrow([[445,391],[480,391]],C.db);
lab('图像特征',383,430,93,23,15,C.db);
// Prediction enters the supervised loss, never the opposite direction.
arrow([[568,435],[568,476]],C.orange);
tensor(531,483,46,34,'#ECD4BC',3,4);
lab('预测 logits',495,524,144,25,18,C.orange,true);
soft(247,484,192,64,'#F9E7DF','#CEA18C');
lab('监督分割损失',253,490,180,24,21,C.orange,true);
lab('BCE + Lovász',253,518,180,23,20,C.ink);
arrow([[206,482],[230,482],[230,514],[247,514]],C.red);
arrow([[522,505],[439,505]],C.red);
// Gradients update precisely the projection and decoder, not the frozen backbone.
arrow([[439,531],[466,531],[466,290],[480,290]],C.red,true);
arrow([[466,419],[480,419]],C.red,true);
lab('约 1800 万可训练参数',248,575,412,26,21,C.orange,true);
lab('冻结表征，仅更新投影与掩膜解码器',240,605,428,23,18,C.muted);

// Validation and checkpoint bridge.
line(46,644,682,644,'#CDDDE4',1);
lab('验证与权重选择',47,652,210,30,23,C.db,true,'left');
await imageFrame(path.join(A,'6598_rgb.png'),50,697,105,70);
await imageFrame(path.join(A,'6598_gt.png'),167,697,105,70);
lab('80 幅验证影像与标签',48,771,228,24,18,C.muted);
arrow([[277,732],[353,732]],C.purple);
lab('比较 IoU',275,692,84,24,17,C.purple,true);
weightCube(365,694,192,84);
arrow([[668,392],[687,392],[687,674],[449,674],[449,683]],C.orange);
// Strong single connection from selected checkpoint to the model used in all four views.
arrow([[571,736],[725,736],[725,179],[1150,179],[1150,224]],C.purple);
lab('加载同一组任务权重',805,154,260,22,17,C.purple,true);

// B: Actual 6598 multi-view input and prediction thumbnails.
lab('输入影像',771,250,112,27,21,C.ink,true);
await imageFrame(path.join(A,'6598_rgb.png'),771,295,112,75);
lab('机制示例 6598',770,377,114,23,17,C.muted);
lab('四视图变换',918,194,99,27,19,C.db,true);
lab('共享权重',1034,194,101,27,19,C.purple,true);
lab('视图预测',1181,194,85,27,19,C.db,true);
lab('坐标恢复',1290,194,106,27,19,C.purple,true);
soft(1033,225,122,292,'#EEF1F8','#B2BBD1');
const names=['原图','水平翻转','垂直翻转','双向翻转'];
for(let i=0;i<4;i++){
 const y=224+i*76;
 await imageFrame(path.join(A,`tta_input_${i}.png`),924,y,84,56);
 lab(names[i],918,y+57,96,20,16,C.ink);
 const cy=y+28;
 arrow([[903,cy],[922,cy]],C.db);
 node('TerraScope',1040,y+8,108,39,'#E1E9F3',C.db,false,false);
 arrow([[1009,cy],[1037,cy]],C.db);
 await imageFrame(path.join(E,`tta_raw_${i}.png`),1187,y,56,56,'#C5D7DE');
 arrow([[1155,cy],[1185,cy]],C.db);
 await imageFrame(path.join(E,`tta_aligned_${i}.png`),1310,y,56,56,'#CCD9D0');
 arrow([[1245,cy],[1308,cy]],C.purple);
 lab(i===0?'原方向':'翻回',1245,y-1,64,21,15,C.purple);
 arrow([[1367,cy],[1392,cy]],C.dg);
}
line(903,252,903,480,C.db,1.5);arrow([[883,332],[903,332]],C.db);
line(1392,252,1392,480,C.dg,1.5);arrow([[1392,305],[1411,305]],C.dg);
lab('同坐标融合',1408,246,147,28,22,C.dg,true);
soft(1412,285,142,39,'#DFEBCF','#ACCCB7');
lab('四路 logits 均值',1416,290,134,29,18,C.ink,true);
arrow([[1483,324],[1483,341]],C.dg);
lab('恢复原图尺寸',1407,342,150,25,19,C.dg,true);
lab('阈值化 (logit > 0)',1407,371,150,23,17,C.muted);
arrow([[1483,395],[1483,413]],C.dg);
await imageFrame(path.join(A,'6598_tta4_mask.png'),1419,414,128,86);
lab('最终道路掩膜',1407,505,150,24,18,C.dg,true);
arrow([[1483,529],[1483,548]],C.dg);

// C: Real scene output and an editable evidence table.
lab('调查案例 7301：受淹道路位置',772,607,300,27,21,C.ink,true);
await imageFrame(path.join(A,'7301_tta4.png'),776,642,244,163);
shape('rect',1035,648,13,13,'#5A93AB');lab('模型掩膜',1056,639,94,29,17,C.db,false,'left');
lab('影像内覆盖率',1038,684,168,26,20,C.ink,true,'left');
lab(`${data.cases['7301'].tta4.coverage.toFixed(2)}%`,1038,716,165,44,36,C.dg,true,'left');
lab('受淹道路像素 / 有效像素',1037,767,179,25,15,C.muted,false,'left');
arrow([[1021,723],[1034,723]],C.dg);
const vals=[['逐景记录','7301'],['有效像素','701,440'],['受淹道路像素','152,585'],['影像内覆盖率','21.75%']];
const tb=s.tables.add({rows:4,columns:2,left:1231,top:629,width:316,height:158,columnWidths:[177,139],values:vals});
tb.borders.assign({fill:'#DEE5EC',width:.7,style:'solid'});
for(let i=0;i<4;i++)for(let j=0;j<2;j++){const c=tb.getCell(i,j);c.fill=i===0?'#DFEBCF':i%2?'#FFFFFF':'#F2F7F3';c.text.style={fontSize:19,typeface:j===0?'Songti SC':'Times New Roman',color:C.ink,bold:i===0||i===3,alignment:'center',verticalAlignment:'middle'};}

// D: Compact real evaluation results, separate from the illustrative pipeline scene.
shape('rect',25,830,1550,50,'#F9F5E9');
lab('D  结果验证',40,837,175,35,25,C.orange,true,'left');
lab('448 幅测试',225,840,150,30,20,C.ink,true);
lab('IoU 58.28%',374,837,191,35,25,C.orange,true);
line(594,842,594,869,'#D9C8AF',1);
lab('370 幅扩展验证',619,840,182,30,20,C.ink,true);
lab('IoU 55.69%',802,837,190,35,25,C.orange,true);
line(1015,842,1015,869,'#D9C8AF',1);
lab('扩展集场景误报',1034,840,198,30,20,C.ink,true);
lab('单视图 10  →  融合 1',1239,837,311,35,25,C.orange,true);

// Freeze/train legend is integral to the model adaptation diagram.
freeze(575,791,7);lab('冻结',585,780,51,23,15,C.db);
learn(649,791);lab('微调',658,780,40,23,15,C.orange);

s.speakerNotes.text=`参考用户提供的“离线训练—模型使用—调查记录”布局，采用原生可编辑图形重画。\n数据源：work/final_talk_20261016/assets/data.json 与 work/editorial_v2_20261016/assets/measurements.json；训练样本 6597 的 RGB/GT、验证机制示例 6598 的四视图、测试场景 7301 的叠加图均来自本地实验。6598 只演示四视图过程，不计入底部测试/扩展结果。\n训练冻结视觉编码器、语言模型及 SAM2 图像编码器，仅更新 SEG 投影和 SAM2 掩膜解码器，共 17,981,509 参数。最终选用 BCE + Lovasz 训练配置，由 80 幅验证集选择。冻结标记用于左侧训练范围，右侧推理所有参数均不更新。\n四视图是原图、水平翻转、垂直翻转、双向翻转。每路输出 logits 先逆变换到原方向，再取均值，插值恢复原图尺寸，最后以 logit > 0 阈值化。缩略图呈现对应预测形状，融合在连续 logits 上完成。代码 work/night_20261016/eval_tta.py。\n场景7301：有效像素701440，预测152585像素，覆盖率21.7531%。此处为影像有效像素中的受淹道路比例，不是道路总长度比例。C区展示输出记录的排版，数值源自实测统计。\n最终四视图测试448幅 IoU58.2768%，同事件扩展370幅 IoU55.6851%，扩展场景误报由单视图10幅降至1幅。没有将扩展集表述为跨灾害泛化。流程图底部展示整体评测，场景7301是其中的实际案例。`;
await (await PresentationFile.exportPptx(p)).save(path.join(W,'candidate.pptx'));
await fs.writeFile(path.join(W,'preview.png'),new Uint8Array(await(await s.export({format:'png',scale:1.5})).arrayBuffer()));
await fs.writeFile(path.join(W,'layout.json'),await(await s.export({format:'layout'})).text());
console.log('standalone workflow created');
