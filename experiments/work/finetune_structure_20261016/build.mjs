import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
import {art,mix} from '../editorial_v2_20261016/method_art.mjs';
const R=process.cwd(),W=path.join(R,'work/finetune_structure_20261016'),A=path.join(R,'work/final_talk_20261016/assets');
const p=Presentation.create({slideSize:{width:1600,height:900}}),s=p.slides.add();s.background.fill='#FFFFFF';
const {tx,box,shape,arrow,line,poly,freeze,learn,vec,tensor,img}=art(s);
const C={ink:'#263F48',green:'#235C49',blue:'#E7F0F6',db:'#4F80A0',lav:'#EAE3F2',purple:'#8A72A4',rose:'#F8E6E9',dr:'#BA7181',sage:'#EAF2E8',dg:'#5B8D70',gold:'#F8EBD7',orange:'#BC7D44',muted:'#6F7E7C',edge:'#BDC9C7',red:'#BF675D'};
const lab=(t,x,y,w,h=28,z=20,col=C.ink,b=false,al='center')=>tx(t,x,y,w,h,z,b,col,al);
function border(x,y,w,h,fill,col){let b=box(x,y,w,h,fill,col);b.line.width=1.35;return b;}
function node(t,x,y,w,h,fill,col,sub=''){border(x,y,w,h,fill,mix(col,'#FFFFFF',.28));lab(t,x+7,y+8,w-14,sub?h-36:h-16,21,C.ink,true);if(sub)lab(sub,x+7,y+h-28,w-14,22,17,col);}
function phase(n,t,x,y,w,col,fill){shape('ellipse',x,y,35,35,fill,col,1);lab(n,x,y,35,35,25,col,true);lab(t,x+47,y,w-47,35,27,C.ink,true,'left');}
function trainFrame(n,t,y,fill,col){border(420,y,760,284,fill,mix(col,'#FFFFFF',.18));phase(n,t,439,y+15,690,col,mix(fill,col,.10));learn(1153,y+31);}
function tokenVector(x,y,n,col,w=15,h=25,g=5){vec(x,y,n,col,w,h,g);}
function brace(x1,x2,y,col){line(x1,y,x1,y+10,col,1.3);line(x1,y+10,x2,y+10,col,1.3);line(x2,y,x2,y+10,col,1.3);}

lab('受淹道路任务适配：SEG 投影与 SAM2 解码器微调',28,17,1544,52,37,C.green,true);
lab('冻结视觉与语言主干，将任务监督集中到语言—分割接口',28,72,1544,30,22,C.muted);

// Three semantic zones; only the two central modules receive gradient arrows.
border(25,131,370,645,'#F8FBFD','#B9CEDB');
phase('1','冻结特征提取',42,146,335,C.db,C.blue);
trainFrame('2','SEG 提示投影层',131,C.rose,C.dr);
trainFrame('3','SAM2 掩膜解码器',492,C.sage,C.dg);
border(1227,131,348,645,'#FBFCFA','#BBCDBF');
phase('4','掩膜监督与更新',1243,146,314,C.dg,C.sage);

// Left: a compact, frozen language branch and frozen SAM2 image branch.
lab('航拍 RGB 影像',45,202,142,25,19,C.ink,true);
await img(path.join(A,'7301_rgb.png'),45,233,142,95);
lab('H × W × 3',45,330,142,22,17,C.muted);
node('视觉编码器',223,233,151,68,C.blue,C.db,'＋ Projector');freeze(360,244,8);
arrow([[187,277],[223,277]],C.db);
tokenVector(239,322,6,'#ACCBDC',14,21,7);
lab('视觉 token',231,347,134,21,17,C.db);
arrow([[298,301],[298,321]],C.db);
border(45,379,142,100,'#F7F2FA','#B7A3C9');lab('任务指令',51,387,130,28,21,C.ink,true);
lab('分割图中的\n受淹道路',52,420,128,48,20,C.ink);
// Compact backbone; no large decorative internals.
node('InternVL3',223,388,151,78,'#EDF2F5',C.db,'多模态语言模型');freeze(360,400,8);
arrow([[298,368],[298,388]],C.db);
arrow([[187,428],[223,428]],C.purple);
lab('文本',182,398,41,22,14,C.purple);
// h_seg leaves the frozen backbone and enters the first trainable block.
arrow([[374,427],[406,427],[406,314],[444,314]],C.dr);

line(39,513,380,513,'#D5E0E6',1);
node('SAM2 图像编码器',56,540,303,66,C.blue,C.db,'同一幅 RGB 影像');freeze(344,552,9);
arrow([[45,281],[34,281],[34,573],[56,573]],C.db);
arrow([[209,606],[209,630]],C.db);
tensor(71,648,62,43,'#CCE1EC',3,5);
tensor(178,659,49,34,'#DCD5EC',3,4);
tensor(282,669,38,26,'#C2DCE9',3,3);
lab('1/4',70,699,70,23,18,C.db);lab('1/8',172,699,70,23,18,C.purple);lab('1/16',270,699,70,23,18,C.db);
lab('多尺度图像特征 F',58,738,300,25,22,C.ink,true);
line(209,630,105,630,C.db,1.4);line(209,630,309,630,C.db,1.4);
arrow([[105,630],[105,638]],C.db);arrow([[209,630],[209,649]],C.db);arrow([[309,630],[309,659]],C.db);

// Central top: one 3584-dimensional SEG hidden vector becomes one 256-d prompt.
lab('将语言侧目标映射为 SAM2 可用的分割提示',446,190,705,31,23,C.dr,true);
lab('SEG 隐藏状态',442,245,114,28,17,C.dr,true);
tokenVector(449,298,4,'#E3B3BD',15,30,5);
lab('3584 维',448,337,88,26,18,C.dr);
node('Linear',564,267,169,87,'#F3D8DF',C.dr,'3584 → 3584');
node('ReLU',768,267,105,87,'#FBF1E4',C.orange,'');
node('Linear',908,267,241,87,'#F3D8DF',C.dr,'3584 → 256');
arrow([[529,314],[564,314]],C.dr);arrow([[733,314],[768,314]],C.dr);arrow([[873,314],[908,314]],C.dr);
lab('语言语义',443,376,150,24,18,C.muted);lab('分割空间',1010,376,140,24,18,C.muted);
// The prompt takes the straight vertical route to two-way attention.
arrow([[1028,354],[1028,434]],C.dr);
tokenVector(974,438,5,'#E2B3BE',18,25,5);
lab('分割提示 P',777,437,170,29,22,C.dr,true);
lab('1 × 256',1093,439,83,27,19,C.dr);
arrow([[1028,463],[1028,567]],C.dr);

// Central bottom: decoder feature paths, attention and two mask-synthesis branches.
lab('提示定位目标，图像特征恢复道路边界',446,548,414,27,22,C.dg,true,'left');
node('双向注意力',920,567,216,72,'#DBEAD8',C.dg,'图像 token ↔ 提示 token');
// Low-resolution feature sequence enters attention directly.
lab('低分辨率图像特征',450,592,240,26,20,C.db,true,'left');
tokenVector(474,627,6,'#B4D1E1',22,25,7);
arrow([[321,684],[407,684],[407,640],[474,640]],C.db);
arrow([[644,640],[875,640],[875,603],[920,603]],C.db);
lab('图像嵌入',678,610,162,25,18,C.db);
// High-resolution path: its projections belong to the trainable mask decoder.
node('高分辨率投影',448,685,177,59,'#DEEBD9',C.dg,'1/4 与 1/8 特征');
arrow([[144,670],[155,670],[155,729],[404,729],[404,714],[448,714]],C.db);
arrow([[238,676],[252,676],[252,729]],C.db);
node('上采样与特征融合',672,685,220,59,'#DEEBD9',C.dg,'恢复空间细节');
arrow([[625,714],[672,714]],C.dg);
// Updated image features and mask tokens leave the transformer via separate lanes.
arrow([[947,639],[947,657],[782,657],[782,685]],C.dg);
lab('图像特征',795,658,116,23,16,C.dg);
node('超网络 MLP',987,665,149,47,'#DEEBD9',C.dg,'');
arrow([[1060,639],[1060,665]],C.dg);
lab('mask token',1059,640,112,23,16,C.dg);
shape('ellipse',1105,727,28,28,'#FFFFFF',C.dg,1.5);lab('×',1105,725,28,31,26,C.dg,true);
arrow([[1061,712],[1061,741],[1105,741]],C.dg);
arrow([[892,714],[932,714],[932,760],[1119,760],[1119,755]],C.dg);
lab('掩膜权重',965,716,91,22,15,C.dg);
lab('空间特征',934,738,100,22,15,C.dg);
arrow([[1133,741],[1203,741],[1203,561],[1247,561]],C.dg);

// Right: real local images, prediction and target retain their original alignment.
lab('本地掩膜示例 7301',1248,202,305,28,21,C.ink,true);
await img(path.join(A,'7301_single_view.png'),1248,242,305,204);
shape('rect',1254,453,12,12,'#5297B8');lab('受淹道路预测',1276,445,240,28,18,C.db,false,'left');
lab('预测掩膜',1246,487,141,27,21,C.ink,true);lab('真实标签',1412,487,141,27,21,C.ink,true);
await img(path.join(A,'7301_single_view_mask.png'),1248,518,139,93);
await img(path.join(A,'7301_mask_gt.png'),1413,518,139,93);
lab('M̂',1248,613,139,23,20,C.dg);lab('M',1413,613,139,23,20,C.dg);
brace(1318,1482,640,C.dg);arrow([[1400,650],[1400,674]],C.dg);
border(1271,674,259,73,'#F8E4DF','#C7897D');
lab('分割监督损失',1281,680,239,29,25,C.red,true);
lab('BCE + Lovász',1281,713,239,26,22,C.ink);
// Dashed gradients use their own corridor, entering exactly the two module frames.
line(1271,710,1191,710,C.red,1.8,true);
line(1191,710,1191,239,C.red,1.8,true);
arrow([[1191,239],[1180,239]],C.red,true);
arrow([[1191,539],[1180,539]],C.red,true);

// One concise bottom legend, no duplicate panel descriptions.
line(26,806,1574,806,'#BDCDC5',1);
freeze(48,839,11);lab('冻结参数',68,822,124,33,20,C.db,false,'left');
learn(228,840);lab('微调参数',247,822,124,33,20,C.orange,false,'left');
arrow([[401,838],[453,838]],C.db);lab('前向计算',467,822,129,33,20,C.ink,false,'left');
arrow([[635,838],[687,838]],C.red,true);lab('反向更新',701,822,129,33,20,C.ink,false,'left');
lab('可训练参数  17.98 M',907,816,339,38,27,C.green,true,'left');
lab('300 幅训练 / 80 幅验证',1246,820,326,32,21,C.muted,false,'right');

s.speakerNotes.text='训练范围与方法依据本地 work/night_20261016/train_night.py：先 model.requires_grad_(False)，再启用 model.text_hidden_fcs 与 sam.sam_mask_decoder。17,981,509 个可训练参数。SEG 投影为 Linear(3584,3584)、ReLU、Linear(3584,256)，单个隐藏状态经 unsqueeze(1) 构成一个 256 维语言提示。向量小格仅为维度示意，不表示多个独立提示。最终配置 BCE + 二值 Lovasz hinge，在有效标签像素上计算，300 幅训练，80 幅验证。\nSAM2 分支依据实际训练 forward 与 SAM2 mask_decoder.py：最粗图像特征进入双向 Transformer，较高分辨率特征经解码器内的 conv_s0/conv_s1 投影后用于上采样融合，mask token 经超网络 MLP 与上采样空间特征矩阵相乘产生掩膜 logits。图中简化质量评分等辅助头。sam_prompt_encoder 独立且冻结，未并入可训练模块。冻结视觉与语言底座不画反向更新。\n影像、叠加图、单视图预测和 GT 均来自本地 work/final_talk_20261016/assets/7301_*。7301 是测试样本，这里仅以对应的真实图像展示分割输出及标签的关系，不表示该测试样本参与参数训练。分割损失由连续 logits 计算，图中二值图用于可视化。最终道路任务使用固定 SEG 前缀，不包含自由生成的 REGION 问答循环。\n按用户提供训练示意图的结构重画，两个中央训练模块等宽等高，冻结模型压缩在左，右侧监督以虚线回到投影和掩膜解码器。未修改主汇报 PPT。';
await (await PresentationFile.exportPptx(p)).save(path.join(W,'candidate.pptx'));
await fs.writeFile(path.join(W,'preview.png'),new Uint8Array(await(await s.export({format:'png',scale:1.4})).arrayBuffer()));
await fs.writeFile(path.join(W,'layout.json'),await(await s.export({format:'layout'})).text());
console.log('training diagram exported');
