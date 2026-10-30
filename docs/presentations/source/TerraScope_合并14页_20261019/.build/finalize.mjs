import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {finalizePresentation} from '/Users/chenxi/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations/container_tools/artifact_tool_utils.mjs';
const D=path.dirname(fileURLToPath(import.meta.url));
const S='/Users/chenxi/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations';
const receiptDir='/Users/chenxi/Desktop/商用时空信息软件平台/outputs/.terrascope-merge-validation';
await fs.mkdir(receiptDir,{recursive:true});
try{
const result=await finalizePresentation({
 workspaceDir:'/Users/chenxi/Desktop/商用时空信息软件平台',
 candidatePath:path.join(D,'candidate_preserved.pptx'),
 finalPath:path.join(D,'..','TerraScope_课堂汇报_14页_合并含讲稿备注版.pptx'),
 pythonExecutable:'/Users/chenxi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',
 integrityValidatorPath:path.join(S,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(S,'container_tools/inspect_presentation_layout_geometry.py'),
 explicitTotalSlideCount:14,
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','8','--require-native-table-slide','9'],
 requiredNativeTableOwnerSlides:[8,9],
 requiredNativeChartOwnerSlides:[9,11],
 requiredEmbeddedWorkbookChartOwnerSlides:[9,11],
 verifyArtifactToolImport:true,
 receiptPath:path.join(receiptDir,'merged14.validation.json')
});
await fs.writeFile(path.join(D,'finalize-result.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
}catch(e){console.error(e.stack);process.exitCode=1;}
