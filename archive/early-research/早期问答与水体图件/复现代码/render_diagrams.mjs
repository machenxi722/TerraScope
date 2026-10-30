import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from '/Users/zhangchunhe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const root=process.cwd(),out=path.join(root,'outputs/TerraScope_全部图件_清新论文版');
const entries=JSON.parse(await fs.readFile(path.join(out,'图件目录.json'),'utf8'));
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const page=await browser.newPage({viewport:{width:1600,height:900},deviceScaleFactor:2});
for(const e of entries.filter(e=>e.source==='base'&&[1,2,3,9,16].includes(Number(e.old.slice(0,2))))){
 const svg=await fs.readFile(path.join(out,'SVG',e.name+'.svg'),'utf8');
 await page.setContent(`<html><head><meta charset="utf-8"><style>html,body{margin:0;width:1600px;height:900px;background:white}svg{display:block}*{font-family:'Times New Roman','Songti SC',serif}</style></head><body>${svg}</body></html>`);
 await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:path.join(out,'PNG',e.name+'.png')});
 await page.pdf({path:path.join(out,'PDF',e.name+'.pdf'),width:'1600px',height:'900px',printBackground:true,margin:{top:0,bottom:0,left:0,right:0}});
 console.log('Rendered',e.name);
}
await browser.close();
