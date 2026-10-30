from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parent
entries=json.loads((root/'SHA256_MANIFEST.json').read_text(encoding='utf-8'))
errors=[]
for rel,expected in entries.items():
    p=root/rel
    if not p.is_file():errors.append([rel,'missing']);continue
    actual=hashlib.sha256(p.read_bytes()).hexdigest()
    if actual!=expected:errors.append([rel,'hash mismatch'])
print(json.dumps({'status':'PASS' if not errors else 'FAIL','checked_files':len(entries),'errors':errors},ensure_ascii=False,indent=2))
sys.exit(bool(errors))
