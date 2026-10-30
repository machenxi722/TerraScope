import path from 'node:path';
import {pathToFileURL} from 'node:url';
const ROOT=process.cwd(),TMP=path.join(ROOT,'work/final_talk_20261016');
const SKILL='/Users/zhangchunhe/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const PY='/Users/zhangchunhe/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
process.env.RUNTIME_NODE_MODULES='/Users/zhangchunhe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const{finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
try{
 const r=await finalizePresentation({workspaceDir:ROOT,candidatePath:path.join(TMP,'candidate.pptx'),finalPath:path.join(ROOT,'outputs/TerraScope_课堂汇报成果整合版_20261016/TerraScope_课堂汇报_14页.pptx'),pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--require-native-table-slide','9','--require-native-table-slide','10'],explicitTotalSlideCount:14,requiredNativeChartOwnerSlides:[9,12],requiredNativeTableOwnerSlides:[9,10],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:['微软雅黑','微软雅黑 Light','Songti SC','Times New Roman']},verifyArtifactToolImport:true,receiptPath:path.join(TMP,'validation.json')});console.log(JSON.stringify(r));
}catch(e){console.error(e.message);console.error(e.details||'');process.exit(1);}
