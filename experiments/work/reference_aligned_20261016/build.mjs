import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
import {art,mix} from '../editorial_v2_20261016/method_art.mjs';
const R=process.cwd(),W=path.join(R,'work/reference_aligned_20261016');
const A=path.join(R,'work/final_talk_20261016/assets');
const S=path.join(R,'outputs/TerraScope_洪灾对齐修正版_20261015/逐景证据/evaluation/7571');
const C={ink:'#233C48',green:'#00552B',blue:'#DCECF5',db:'#427C9C',purple:'#8971A8',lav:'#E7E0F2',sage:'#DDEBDA',dg:'#54856B',gold:'#F7E6C6',orange:'#BA7B48',rose:'#F1D4D8',dr:'#B56D7D',edge:'#93A49D',muted:'#647B73'};
const p=Presentation.create({slideSize:{width:1280,height:720}}),s=p.slides.add();s.background.fill='#FFFFFF';
const {tx,box,shape,arrow,line,poly,freeze,learn,vec,tensor,img}=art(s);
const label=(t,x,y,w,h=25,size=18,col=C.ink,bold=false,align='center')=>tx(t,x,y,w,h,size,bold,col,align);
function token(t,x,y,w,h,fill,col){box(x,y,w,h,fill,mix(col,'#FFFFFF',.35));label(t,x+3,y,w-6,h,17,col,true);}
function stage(n,t,x,w,fill,col){box(x,55,w,41,fill,mix(col,'#FFFFFF',.5));shape('ellipse',x+9,61,28,28,mix(fill,col,.16),mix(col,'#FFFFFF',.35),1);label(String(n),x+9,60,28,29,22,col,true);label(t,x+46,58,w-56,34,19,C.ink,true);}
function encoder(t,x,y,w,h,fill,col,ice=true){poly([[x,y],[x+w,y+18],[x+w,y+h-18],[x,y+h]],fill,col,1.35);label(t,x+6,y+25,w-12,h-49,18,C.ink,true);if(ice)freeze(x+w-12,y+30,8);}
function bubble(x,y,col){shape('ellipse',x,y,22,18,mix(col,'#FFFFFF',.8),col,.9);for(let k=0;k<3;k++)shape('ellipse',x+5+k*5,y+8,2.5,2.5,col);poly([[x+4,y+14],[x+3,y+21],[x+10,y+16]],mix(col,'#FFFFFF',.8),col,.8);}

// Match the reference's spatial structure: input left, central language model,
// lower segmentation branch, right-hand evidence/output, returning REGION path.
tx('TerraScope：语言引导分割与区域证据反馈',26,8,1010,36,28,true,C.green);
label('原模型机制与本组适配位置',1007,16,247,23,15,C.muted,false,'right');
stage(1,'语言理解：形成目标与分割提示',25,398,C.blue,C.db);
stage(2,'像素定位：生成目标分割掩膜',439,396,C.sage,C.dg);
stage(3,'证据反馈：区域信息辅助回答',851,405,C.gold,C.orange);

// Image and text inputs keep their independent paths into the center.
label('输入影像  I',28,105,153,23,20,C.ink,true);
await img(path.join(S,'RGB.png'),28,130,153,102);
label('H × W × 3',29,233,152,22,17,C.muted);
encoder('视觉编码器\n＋ Projector',220,130,122,100,C.blue,C.db);
arrow([[181,181],[218,181]],C.db);
for(let i=0;i<4;i++)await img(path.join(A,`7571_tile${i}.png`),225+i*34,250,29,25);
arrow([[342,180],[367,180],[367,283],[296,283],[296,290]],C.db);
vec(225,291,7,'#A8CADA',12,20,6);
label('视觉 token  V',218,317,153,23,18,C.db,true);
// Image-patch thumbnails show token correspondence, not a post-encoder image operation.

box(27,279,155,134,'#F8FAF9','#B6C4BE');bubble(39,291,C.db);
label('输入问题  Q',67,285,107,32,19,C.ink,true);
box(36,329,137,72,'#FFFFFF','#B6C4BE');
label('这张图中水面的\n覆盖率是多少？',42,337,125,56,18,C.ink);
vec(225,365,7,'#C6B5DD',12,22,6);
label('文本 token  T',219,392,155,25,18,C.purple,true);
arrow([[182,376],[222,376]],C.purple);

// The upper sequence is an input sequence; SEG is generated below the model.
label('视觉与文本组成多模态输入序列',423,104,414,24,19,C.ink,true);
box(420,131,419,47,'#FBFCFD','#8C9AA0');
vec(434,143,4,'#A8CADA',16,24,5);label('…',519,140,25,27,20);
vec(551,143,3,'#C6B5DD',16,24,5);token('question',625,141,121,28,C.lav,C.purple);label('…',751,140,30,29,20);vec(789,143,2,'#C6B5DD',14,24,5);
arrow([[352,301],[380,301],[380,151],[420,151]],C.db);
arrow([[352,376],[399,376],[399,168],[420,168]],C.purple);
arrow([[630,178],[630,204]],C.db);

// InternVL3 stays as a compact frozen backbone; the visual weight belongs to the
// language-to-mask interface, trainable decoder, and evidence feedback path.
box(475,205,310,70,'#EFF3F5','#A5B6BC');
label('语言模型 InternVL3',489,212,275,28,22,C.ink,true);
label('冻结的多模态底座',490,244,274,23,16,C.muted);
freeze(770,219,8);

// Shared layout contract: both trainable modules have identical geometry.
const moduleX=464,moduleW=360,moduleH=128,moduleCenter=moduleX+moduleW/2;
const projectionY=345,decoderY=542;
function trainedFrame(title,y){
 const frame=box(moduleX,y,moduleW,moduleH,'#FCEDF0','#B87A89');frame.line.width=1.7;
 label(title,moduleX+17,y+10,moduleW-48,31,24,C.ink,true);
 learn(moduleX+moduleW-18,y+18);
 return frame;
}
box(490,289,250,36,'#FBFCFD','#B2BCC1');vec(500,296,3,'#A8CADA',16,22,6);token('[SEG]',582,294,126,27,C.rose,C.dr);
arrow([[moduleCenter,275],[moduleCenter,289]],C.dr);
label('SEG 隐藏状态',469,326,145,18,16,C.dr);
arrow([[moduleCenter,325],[moduleCenter,projectionY]],C.dr);
trainedFrame('SEG 投影 MLP',projectionY);
box(486,398,89,31,'#F7DDE3','#C598A3');label('Linear',489,398,83,31,20,C.dr,true);
box(602,398,65,31,'#FBF5F0','#C9A394');label('ReLU',604,398,61,31,19,C.orange,true);
box(695,398,105,31,'#F7DDE3','#C598A3');label('Linear',698,398,99,31,20,C.dr,true);
arrow([[575,414],[601,414]],C.dr);arrow([[667,414],[694,414]],C.dr);
label('3584 → 3584',484,434,98,23,16,C.muted);
label('3584 → 256',695,434,105,23,16,C.muted);
arrow([[moduleCenter,473],[moduleCenter,495]],C.dr);
vec(581,495,5,'#E8B2BD',21,24,5);
label('分割提示  P',722,486,121,26,19,C.dr,true);label('256 维',723,514,120,21,16,C.muted);
arrow([[moduleCenter,519],[moduleCenter,decoderY]],C.dr);

// Parallel SAM2 image path, with three scales rather than a generic flat box.
label('同一影像  I',28,460,153,24,20,C.ink,true);
await img(path.join(S,'RGB.png'),28,491,153,102);
encoder('SAM2\n图像编码器',205,491,117,104,C.lav,C.purple);
arrow([[181,543],[203,543]],C.purple);
label('多尺度特征  F',330,458,126,23,18,C.ink,true);
tensor(365,491,44,34,C.blue,3,5);tensor(373,546,35,27,C.lav,3,4);tensor(383,593,25,22,C.blue,3,3);
line(339,510,339,607,C.purple,1.3);line(322,543,339,543,C.purple,1.3);
arrow([[339,510],[363,510]],C.purple);arrow([[339,560],[371,560]],C.purple);arrow([[339,607],[381,607]],C.purple);
// Decoder internals follow local SAM2 mask_decoder.py: two-way interaction,
// token-conditioned hypernetworks, upscaled image features, then multiplication.
trainedFrame('SAM2 掩膜解码器',decoderY);
box(479,591,92,62,'#F7DDE3','#C598A3');
label('双向注意力',483,600,84,24,17,C.ink,true);
label('图像 ↔ 提示',483,627,84,21,14,C.dr);
box(594,589,119,28,'#F7DDE3','#C598A3');label('超网络 MLP',598,590,111,26,17,C.dr,true);
box(594,633,119,29,'#F7DDE3','#C598A3');label('上采样与融合',598,634,111,27,16,C.dr,true);
arrow([[571,605],[593,605]],C.dr);
arrow([[571,640],[593,640]],C.dr);
arrow([[713,603],[766,603],[766,619]],C.dr);
arrow([[713,648],[766,648],[766,641]],C.dr);
shape('ellipse',755,619,22,22,'#FFFFFF','#C598A3',1);
label('×',755,617,22,25,22,C.dr,true);
label('掩膜合成',724,647,88,20,15,C.dr);
line(777,630,824,630,C.dr,1.5);
// The two high-resolution features enter upscaling; the coarsest feature
// enters two-way attention. A gap denotes a crossing without a junction.
arrow([[418,605],[478,605]],C.purple);
line(419,509,440,509,C.purple,1.3);line(440,509,440,594,C.purple,1.3);
const bridgePts=Array.from({length:17},(_,i)=>{const t=-Math.PI/2+i*Math.PI/16;return [440+7*Math.cos(t),605+11*Math.sin(t)];});
for(const [col,width] of [['#FFFFFF',5],[C.purple,1.3]])for(let i=1;i<bridgePts.length;i++)line(...bridgePts[i-1],...bridgePts[i],col,width);
line(440,616,440,666,C.purple,1.3);
line(418,561,440,561,C.purple,1.3);
line(440,666,580,666,C.purple,1.3);
arrow([[580,666],[580,654],[594,654]],C.purple);

// Output mask is a real local prediction and controls the evidence selection.
label('分割掩膜  M',843,568,126,23,18,C.ink,true);
await img(path.join(S,'P1.png'),846,589,126,84);
arrow([[824,630],[844,630]],C.dg);
box(947,452,180,82,C.sage,C.dg);label('按掩膜选取\n区域视觉 token',953,460,168,44,18,C.ink,true);label('视觉特征 V ＋ 掩膜 M',953,505,168,23,15,C.dg);
arrow([[972,636],[984,636],[984,535]],C.dg);
label('区域视觉特征',1138,443,119,23,17,C.dg,true);vec(1150,477,5,'#B8D5B0',17,24,5);label('K × D',1209,507,47,20,16,C.muted);
arrow([[1127,490],[1148,490]],C.dg);
// Selected feature tokens are injected back into the language model.
token('<REGION>',807,241,108,34,C.sage,C.dg);
arrow([[1202,501],[1202,545],[934,545],[934,258],[915,258]],C.dg);
arrow([[807,258],[785,258]],C.dg);
label('区域证据回注',806,279,138,24,17,C.dg,true);
await img(path.join(W,'water_overlay.png'),1045,559,150,94);
label('掩膜对应区域',1043,654,154,23,17,C.dg);

// Right-hand answer and geographic output keep the reference's stacked structure.
box(956,109,299,95,'#FAFCFA','#B6C4BE');bubble(969,122,C.db);label('输出回答',998,116,243,27,20,C.ink,true,'left');
box(969,151,272,42,'#FFFFFF','#B6C4BE');label('水面覆盖率约为 16%',979,155,251,34,21,C.ink);
arrow([[785,222],[918,222],[918,158],[955,158]],C.db);
box(956,222,299,210,'#FAFCFA','#B6C4BE');bubble(969,235,C.db);label('输出掩膜与空间位置',999,229,243,27,20,C.ink,true,'left');
await img(path.join(W,'water_overlay.png'),972,265,265,143);
shape('rect',977,410,12,10,'#5297B8');label('预测水面',995,401,93,24,15,C.db,false,'left');
// Small symbols carry exact task-adaptation meaning rather than decoration.
line(27,681,1255,681,'#CEDCD5',1);
freeze(39,701,9);label('本组冻结',54,687,111,27,17,C.db,false,'left');learn(184,701);label('本组微调',201,687,115,27,17,C.orange,false,'left');
vec(340,694,2,'#A8CADA',13,17,4);label('视觉 token',379,687,126,27,16,C.ink,false,'left');
vec(521,694,2,'#C6B5DD',13,17,4);label('文本 token',560,687,126,27,16,C.ink,false,'left');
token('SEG',709,691,49,24,C.rose,C.dr);label('触发分割',766,687,115,27,16,C.ink,false,'left');
token('REGION',908,691,83,24,C.sage,C.dg);label('区域证据',1000,687,113,27,16,C.ink,false,'left');
label('本地样本 7571',1128,687,126,27,15,C.muted,false,'right');

s.speakerNotes.text='本页两个微调模块使用完全相同的 360×128 尺寸，统一标题、图标和中心线。REGION token 与语言模型回注口水平对齐。SAM2 解码依据本地 third_parts/sam2/modeling/sam/mask_decoder.py：TwoWayTransformer 输出 mask token 与图像特征，超网络 MLP 生成权重，上采样分支融合高分辨率特征，最后矩阵乘法生成掩膜。图中只画主掩膜路径，省略质量评分等辅助输出。本页压缩冻结的 InternVL3 模块，突出 SEG 提示投影、SAM2 掩膜解码及区域证据回注。本页按用户提供的参考图保留空间组织：左侧图像和问题，中央多模态语言模型，上方输入序列，下方 SEG 与 SAM2 分割分支，右侧结果与区域特征回注。\n模型为 TerraScope / InternVL3，已有 SAM2。代码 work/terrascope_preflight/modeling_sa2va_chat.py 中 _extract_region_info_from_mask 和 build_region_embeds_from_indices 按掩膜选取视觉 token；不是单一均值池化向量。雪花与火焰表示本组任务微调范围，冻结视觉、语言、SAM2 图像编码，只训练 SEG 投影和 SAM2 掩膜解码器。REGION 回路表现原模型机制，本组最终道路专用推理使用固定 SEG 前缀，不执行自由生成的完整 REGION 问答循环。\n真实 RGB 和 P1 掩膜取自 outputs/TerraScope_洪灾对齐修正版_20261015/逐景证据/evaluation/7571。约16%是该样本原模型文字回答，不是由展示掩膜重新计算的覆盖率。视觉 token、Transformer 层、多尺度特征为结构示意。原论文 https://arxiv.org/abs/2603.19039 。';
await (await PresentationFile.exportPptx(p)).save(path.join(W,'candidate.pptx'));
await fs.writeFile(path.join(W,'preview.png'),new Uint8Array(await(await s.export({format:'png',scale:1.7})).arrayBuffer()));
console.log('Created refocused standalone principle diagram.');
