import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {finalizePresentation} from '/Users/chenxi/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations/container_tools/artifact_tool_utils.mjs';
const D=path.dirname(fileURLToPath(import.meta.url));
const S='/Users/chenxi/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations';
const SOURCE='/Users/chenxi/Desktop/TerraScope_课堂汇报.pptx';
const finalPath=path.join(D,'..','TerraScope_第8至14页_深色专业版_v2.pptx');
const receiptDir='/Users/chenxi/Desktop/商用时空信息软件平台/outputs/.terrascope-reorg-validation';
await fs.mkdir(receiptDir,{recursive:true});
try {
const result=await finalizePresentation({
 workspaceDir:'/Users/chenxi/Desktop/商用时空信息软件平台',candidatePath:path.join(D,'candidate_preserved.pptx'),finalPath,
 pythonExecutable:'/Users/chenxi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',
 integrityValidatorPath:path.join(S,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(S,'container_tools/inspect_presentation_layout_geometry.py'),
 explicitTotalSlideCount:7,
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','1','--require-native-table-slide','2'],
 requiredNativeTableOwnerSlides:[1,2],requiredNativeChartOwnerSlides:[2,4],requiredEmbeddedWorkbookChartOwnerSlides:[2,4],
 fontPolicy:{basis:'reference',families:['Songti SC','Times New Roman','微软雅黑','宋体','Cambria Math','Segoe UI Symbol','微软雅黑 Light'],referencePath:SOURCE,referenceSha256:createHash('sha256').update(await fs.readFile(SOURCE)).digest('hex')},
 verifyArtifactToolImport:true,receiptPath:path.join(receiptDir,'v2.validation.json')
});
console.log(JSON.stringify(result,null,2));
}catch(e){console.log(e.stack);process.exitCode=1;}
