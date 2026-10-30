import fs from 'node:fs/promises';
import { PresentationFile,FileBlob } from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('/Users/chenxi/Desktop/TerraScope_课堂汇报.pptx'));
const ins=await p.inspect({select:'$.slides[7,8,9,10,11,12,13]',include:['id','index','layout','elements.id','elements.kind','elements.name','elements.text','elements.position','elements.alt']});
await fs.writeFile(new URL('source_inspection.ndjson',import.meta.url),ins.ndjson);
console.log('slides',p.slides.items.length,'masters',p.masters.items.length);
console.log('slides:',p.slides.items.slice(7).map(s=>({id:s.id,frame:s.frame,images:s.images.items.length,shapes:s.shapes.items.length})));
console.log('layouts',p.slides.items[7].placeholders.summary());
await fs.writeFile(new URL('source.proto.json',import.meta.url),JSON.stringify(p.toProto()));
