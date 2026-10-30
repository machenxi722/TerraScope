import fs from 'node:fs/promises';import path from 'node:path';import{PresentationFile,FileBlob}from'@oai/artifact-tool';
const P='/Users/zhangchunhe/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_27rfdc700gbf22_5c9e/msg/file/2026-09/模板图(1).pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(P));const d='work/editorial_v2_20261016/reference';await fs.mkdir(d,{recursive:true});
for(const i of [2,5,8,26,32,33,34,61,67,71,73,80,86,88,92,93,94,97]){const b=await p.slides.items[i-1].export({format:'png',scale:.8});await fs.writeFile(path.join(d,`ref-${i}.png`),new Uint8Array(await b.arrayBuffer()));console.log('Rendered',i);}
