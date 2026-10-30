process.on('uncaughtException',e=>{console.error(e.message);process.exit(1)});
import fs from 'node:fs/promises';import path from 'node:path';import {PresentationFile,FileBlob}from'@oai/artifact-tool';
const R=process.cwd(),T=path.join(R,'work/palette_refresh_20261016'),O=path.join(R,'outputs/TerraScope_新版配色与主图整合_20261016');
const p=await PresentationFile.importPptx(await FileBlob.load(path.join(O,'TerraScope_课堂汇报_14页_新版配色与主图整合_v2.pptx')));await fs.mkdir(path.join(T,'final_renders'),{recursive:true});
for(const[i,s]of p.slides.items.entries()){await fs.writeFile(path.join(T,'final_renders',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await(await s.export({format:'png',scale:1.25})).arrayBuffer()));console.log(`Final ${i+1}/${p.slides.items.length}`);}

await fs.writeFile(path.join(T,'montage.webp'),new Uint8Array(await(await p.export({format:'webp',montage:true})).arrayBuffer()));
