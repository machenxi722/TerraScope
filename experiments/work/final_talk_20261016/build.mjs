process.on('uncaughtException',e=>{console.error(e.message);console.error((e.stack||'').split('\n').filter(x=>x.includes('work/')).join('\n'));process.exit(1);});
import fs from 'node:fs/promises';import path from 'node:path';import {PresentationFile,FileBlob}from'@oai/artifact-tool';
import{pages}from'./pages.mjs';import{enhanced}from'./enhanced_methods.mjs';import{design,C}from'./design.mjs';
const ROOT=process.cwd(),TMP=path.join(ROOT,'work/final_talk_20261016');
const SRC='/Users/zhangchunhe/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_27rfdc700gbf22_5c9e/temp/drag/samlora.pptx';
await fs.mkdir(path.join(TMP,'renders'),{recursive:true});
const talk=JSON.parse(await fs.readFile(path.join(TMP,'talk.json'),'utf8')),pg=await pages(ROOT),{sh,t}=design();
Object.assign(pg,await enhanced(ROOT));
const p=await PresentationFile.importPptx(await FileBlob.load(SRC));const old=p.slides.items.slice(),cover=old[0],base=old[12];p.slides.keep([0,12]);
const nav=['研究背景','TerraScope 模型','本组方法','实验与应用','结论'],navOld=['研究背景及现状','研究目标与内容','关键技术与创新点','已开展工作','进度安排'];
for(const l of p.layouts.items)for(const q of l.shapes.items){let j=navOld.indexOf(q.text.toString());if(j>=0){q.text=nav[j];q.text.style={fontSize:25,typeface:'微软雅黑',color:'#404040',alignment:'center',verticalAlignment:'middle',insets:3.78};}}
const ui=(s,tx,x,y,w,h,size=27,col=C.ink,bold=false,align='left')=>t(s,tx,x,y,w,h,size,col,bold,align,'微软雅黑');
const cj=JSON.parse(await fs.readFile(path.join(ROOT,'work/template_revision/source-1.json'),'utf8'));p.delete(cj.elements.filter(e=>e.id==='sh/utg3698n'||e.kind==='table').map(e=>e.id));
ui(cover,talk[0].title,55,231,1170,80,51,'#FFFFFF',true,'center');ui(cover,'轻量任务微调与多视图稳健推理',55,328,1170,50,33,'#FFFFFF',true,'center');ui(cover,'课程项目汇报',380,521,520,49,31,'#171717',false,'center');ui(cover,'2026 年 10 月',380,584,520,49,30,'#171717',false,'center');
const bj=JSON.parse(await fs.readFile(path.join(ROOT,'work/template_revision/source-13.json'),'utf8'));p.delete(bj.elements.filter(e=>!['sh/p4r6p8by','sh/o3i5w3ad'].includes(e.id)).map(e=>e.id));
const slides=[cover];function make(n,sec){const s=base.duplicate();s.moveTo(p.slides.items.length-1);const band=s.shapes.items.find(x=>x.position.top>100);band.text='';band.fill='none';band.line={fill:'none',width:0};sh(s,'rightArrow',29,94,19,16,C.green);ui(s,talk[n-1].title,58,80,1170,44,29,C.green,true);const ac=s.shapes.items.find(x=>x.position.top<10);ac.position={left:sec*257.01,top:0,width:sec===4?251.97:257.01,height:69.75};ac.text=nav[sec];ac.text.style={fontSize:25,typeface:'微软雅黑',color:'white',bold:true,alignment:'center',verticalAlignment:'middle',insets:3.78};ui(s,String(n),1247,689,25,26,16,'#404040',false,'right');slides.push(s);return s;}
const funcs=['background','capability','original','workflow','train','tta','data','results','choice','qualitative','holdout','application','summary'];const sections=[0,1,1,2,2,2,3,3,3,3,3,3,4];
for(let i=0;i<funcs.length;i++){await pg[funcs[i]](make(i+2,sections[i]));console.log('Built',i+2,funcs[i]);}
p.slides.keep(p.slides.items.map((_,i)=>i).filter(i=>p.slides.items[i]!==base));
let tm=0;const fmt=n=>`${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;
for(let i=0;i<slides.length;i++){const q=talk[i],start=tm;tm+=q.seconds;slides[i].speakerNotes.text=`第 ${i+1} 页｜${q.title}\n目标 ${q.seconds} 秒｜${fmt(start)}—${fmt(tm)}\n\n【演讲正文】\n${q.speech}\n\n【指图提示，不朗读】\n${q.point}\n\n【依据，不朗读】\n${q.sources.join('\n')}\n\n视觉参考：用户提供的21页选图中DPCache、HetCache的阶段分区；SVDCache、SenCache的对齐图像矩阵；FRDiff的同窗口局部放大。图中影像与模型结果均来自本项目本地文件。网络堆叠、特征块、token 序列是结构示意，非实测注意力；分割分数图取自已保存的 aligned_logits，颜色仅用于展示。第6页使用留出影像说明计算流程，不将该示例计入训练集。`;}
await(await PresentationFile.exportPptx(p)).save(path.join(TMP,'candidate.pptx'));
for(const[i,s]of slides.entries()){if(process.env.METHOD_ONLY&&!([3,4,5,6].includes(i)))continue;await fs.writeFile(path.join(TMP,'renders',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await(await s.export({format:'png',scale:1.25})).arrayBuffer()));console.log('Rendered',i+1);}
await fs.writeFile(path.join(TMP,'manifest.json'),JSON.stringify({slideCount:slides.length,targetSeconds:tm,referencePdf:'/Users/zhangchunhe/Documents/Codex/2026-10-13/video-model-cache-1-2-method/outputs/video_model_cache_已选图片_按类型分类_21张.pdf',talk},null,2));console.log('DONE',tm);
