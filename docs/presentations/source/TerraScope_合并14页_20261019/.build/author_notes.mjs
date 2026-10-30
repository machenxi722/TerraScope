import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
const D=path.dirname(fileURLToPath(import.meta.url));
const source='/Users/chenxi/Desktop/商用时空信息软件平台/outputs/TerraScope_重组8至14页_20261019/TerraScope_第8至14页_深色专业版_v2.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const groups=JSON.parse(await fs.readFile(path.join(D,'notes.json'),'utf8'));
if(p.slides.items.length!==7)throw new Error('Expected seven slides');
for(let i=0;i<7;i++){
 p.slides.items[i].speakerNotes.text=groups[i].notesText;
 p.slides.items[i].speakerNotes.setVisible(true);
}
const ins=await p.inspect({kind:'slide,notes',maxChars:24000});
await fs.writeFile(path.join(D,'authored_notes.ndjson'),ins.ndjson);
await (await PresentationFile.exportPptx(p)).save(path.join(D,'notes_authored.pptx'));
console.log('Authored seven slide notes with supplied script.');
