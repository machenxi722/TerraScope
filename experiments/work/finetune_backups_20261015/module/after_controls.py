"""Complete and seal all original controls before starting an isolated module arm."""
import os,sys,time,signal,subprocess,json,zipfile,hashlib,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent;F=ROOT.parent/'finetune_formal_20261015'
MARK=F/'KEEP_GPU';TOKEN='after-all-original-controls-20261015\n'
PID=int((F/'run.pid').read_text());status={'phase':'waiting_for_all_original_controls','started':time.strftime('%Y-%m-%d %H:%M:%S'),'formal_pid':PID};child=None
# Hard cutoff leaves 40 minutes for the module before the 22:00 platform shutdown.
LATEST_START=time.mktime(time.strptime('2026-10-15 21:15:00','%Y-%m-%d %H:%M:%S'))
def log(s):print(time.strftime('%H:%M:%S'),s,flush=True)
def save():
 p=ROOT/'queue_status.tmp';p.write_text(json.dumps(status,indent=2));p.replace(ROOT/'queue_status.json')
def alive():
 try:return 'train_formal.py' in Path(f'/proc/{PID}/cmdline').read_bytes().decode(errors='replace')
 except FileNotFoundError:return False
for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda *args:sys.exit(130))
assert not MARK.exists(),'Inspect existing KEEP_GPU marker before queuing'
MARK.write_text(TOKEN);save();log('WAITING_FOR_ALL_ORIGINAL_CONTROLS '+str(PID))
try:
 while alive():
  if time.time()>LATEST_START:raise TimeoutError('No module run started: original controls exceeded latest start time')
  time.sleep(10)
 report=json.loads((F/'results/report.json').read_text())
 expected={'head_seed20261015','lora_seed20261015','lora_seed20261016','lora_seed20261017'}
 assert report['completed'] and set(report['arms'])==expected,'Original controls must all finish successfully'
 assert all(a['micro_steps']==1600 and a['test']['n']==448 for a in report['arms'].values())
 assert len(list((F/'results/predictions').glob('*/test/*.png')))==2240
 deadline=time.monotonic()+180
 while not (F/'result_sha256.json').exists() or not (F/'formal_complete.zip').exists():
  assert time.monotonic()<deadline,'Original archive not sealed';time.sleep(5)
 # Wait for the completion guard's sealing message rather than reading a partial ZIP.
 while 'RESULTS_SEALED' not in (F/'finish_guard.log').read_text():
  assert time.monotonic()<deadline,'Original archive seal timed out';time.sleep(5)
 with zipfile.ZipFile(F/'formal_complete.zip') as z:assert z.testzip() is None
 status['formal_archive_sha256']=hashlib.sha256((F/'formal_complete.zip').read_bytes()).hexdigest()
 status['formal_results_completed']=report['completed'];status['formal_arms']=sorted(report['arms'])
 assert time.time()<LATEST_START,'Not enough time left for a clean module run'
 status['phase']='module_running_after_completed_controls';save();log('ORIGINAL_CONTROLS_COMPLETE_AND_SEALED; MODULE_START')
 with open(ROOT/'run.log','w') as out:
  child=subprocess.Popen(['/root/terrascope-env/bin/python','-u',str(ROOT/'train_module.py')],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
  (ROOT/'run.pid').write_text(str(child.pid));status['module_pid']=child.pid;save()
  try:status['returncode']=child.wait(timeout=2400)
  except subprocess.TimeoutExpired:
   child.terminate()
   try:child.wait(timeout=15)
   except subprocess.TimeoutExpired:child.kill();child.wait()
   raise TimeoutError('Module hard limit reached')
 report=json.loads((ROOT/'results/report.json').read_text());assert report['completed'],'Module run failed'
 assert report['arms']['detail_seed20261015']['same_training_sample_order_as_head_control']
 assert len(list((ROOT/'results/predictions/detail_seed20261015/test').glob('*.png')))==448
 files=[p for p in (ROOT/'results').rglob('*') if p.is_file()]+[ROOT/n for n in ['protocol.json','manifest.json','train_module.py','road_detail.py','after_controls.py','run.log']]
 digests={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
 seal=ROOT/'result_sha256.json';seal.write_text(json.dumps(digests,indent=2));files.append(seal)
 archive=ROOT/'module_complete.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files:z.write(p,str(p.relative_to(ROOT)))
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in digests.items())
 status['module_archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();status['phase']='all_completed_and_sealed';save();log('ALL_RESULTS_SEALED; SHUTDOWN_IN_300_SECONDS')
 time.sleep(300)
 if MARK.exists() and MARK.read_text()==TOKEN:
  MARK.unlink();status['phase']='shutdown_requested';save();subprocess.run(['/usr/bin/shutdown'],check=True)
except BaseException as e:
 status['error']=repr(e);status['phase']='stopped_without_starting_or_failed';traceback.print_exc()
finally:
 if child is not None and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=15)
  except subprocess.TimeoutExpired:child.kill();child.wait()
 if MARK.exists() and MARK.read_text()==TOKEN:MARK.unlink()
 status['updated']=time.strftime('%Y-%m-%d %H:%M:%S');save();log(json.dumps(status))
