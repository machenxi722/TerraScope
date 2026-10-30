from pathlib import Path,PurePosixPath
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import posixpath,json,hashlib,re
D=Path(__file__).resolve().parent
A=Path('/Users/chenxi/Desktop/TerraScope_课堂汇报_14页_v14_第四页左下布局舒展(1).pptx')
B=Path('/Users/chenxi/Desktop/商用时空信息软件平台/outputs/TerraScope_重组8至14页_20261019/TerraScope_第8至14页_深色专业版_v2.pptx')
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','rel':'http://schemas.openxmlformats.org/package/2006/relationships','ct':'http://schemas.openxmlformats.org/package/2006/content-types'}
def load(path):
 with ZipFile(path) as z:return {n:z.read(n) for n in z.namelist() if not n.endswith('/')}
def xml(b):return E.fromstring(b)
def dump(r):return E.tostring(r,xml_declaration=True,encoding='UTF-8',standalone=True)
def relpath(n):return posixpath.join(posixpath.dirname(n),'_rels',posixpath.basename(n)+'.rels')
def resolve(owner,target):return posixpath.normpath(posixpath.join(posixpath.dirname(owner),target)).lstrip('/')
front=load(A);back_original=load(B);back=dict(back_original);authored=load(D/'notes_authored.pptx')
notes=json.loads((D/'notes.json').read_text())
color_changes=[]
for i,n in enumerate(notes,1):
 name=f'ppt/slides/slide{i}.xml';r=xml(back[name])
 title=r.xpath('//p:sp[p:nvSpPr/p:cNvPr[@id="'+n['titleShapeId']+'"]]',namespaces=NS)[0]
 changed=0
 for c in title.xpath('./p:txBody//a:srgbClr[@val="15344E"]',namespaces=NS):
  c.set('val','294F82');changed+=1
 assert changed>0
 bars=[]
 for shape in r.xpath('//p:sp',namespaces=NS):
  y=shape.xpath('./p:spPr/a:xfrm/a:off/@y',namespaces=NS)
  txt=''.join(shape.xpath('.//a:t/text()',namespaces=NS))
  cs=shape.xpath('./p:spPr/a:solidFill/a:srgbClr[@val="15344E"]',namespaces=NS)
  if y==['0'] and not txt and cs:
   for c in cs:c.set('val','2F5597')
   bars.append(shape.find('p:nvSpPr/p:cNvPr',NS).get('id'))
 assert len(bars)==1,bars
 back[name]=dump(r)
 color_changes.append({'page':i+7,'titleShapeId':n['titleShapeId'],'titleColor':'294F82','navbarShapeIds':bars,'navbarColor':'2F5597'})
 name=f'ppt/notesSlides/notesSlide{i}.xml'
 r=xml(back[name]);ar=xml(authored[name])
 dest=r.xpath('//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody',namespaces=NS)[0]
 source=ar.xpath('//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody',namespaces=NS)[0]
 dest.getparent().replace(dest,deepcopy(source))
 back[name]=dump(r)

out=dict(front)
ct=xml(front['[Content_Types].xml']);backct=xml(back['[Content_Types].xml'])
ct_by_name={x.get('PartName'):x for x in ct if x.tag.endswith('Override')}
back_ct_by_name={x.get('PartName'):x.get('ContentType') for x in backct if x.tag.endswith('Override')}
ct_default={x.get('Extension'):x.get('ContentType') for x in ct if x.tag.endswith('Default')}
for x in backct:
 if x.tag.endswith('Default'):
  ext=x.get('Extension');typ=x.get('ContentType')
  if ext in ct_default:assert ct_default[ext]==typ,(ext,typ,ct_default[ext])
  else:ct.append(deepcopy(x));ct_default[ext]=typ
mapping={}
for i in range(1,8):
 mapping[f'ppt/slides/slide{i}.xml']=f'ppt/slides/slide{i+7}.xml'
 mapping[f'ppt/notesSlides/notesSlide{i}.xml']=f'ppt/notesSlides/notesSlide{i+7}.xml'
processed=set()
def import_part(old):
 assert old in back,old
 if old not in mapping:mapping[old]=posixpath.join(posixpath.dirname(old),'merged_'+posixpath.basename(old))
 new=mapping[old]
 if old in processed:return new
 processed.add(old);out[new]=back[old]
 typ=back_ct_by_name.get('/'+old)
 if typ:
  if '/'+new in ct_by_name:ct_by_name['/'+new].set('ContentType',typ)
  else:
   node=E.SubElement(ct,'{'+NS['ct']+'}Override',PartName='/'+new,ContentType=typ);ct_by_name['/'+new]=node
 rp=relpath(old)
 if rp in back:
  rr=xml(back[rp])
  for rel in rr:
   if rel.get('TargetMode')=='External':continue
   oldtarget=resolve(old,rel.get('Target'))
   newtarget=import_part(oldtarget)
   rel.set('Target',posixpath.relpath(newtarget,posixpath.dirname(new)))
  out[relpath(new)]=dump(rr)
 return new
for i in range(1,8):import_part(f'ppt/slides/slide{i}.xml')
pres=xml(front['ppt/presentation.xml']);pr=xml(front['ppt/_rels/presentation.xml.rels'])
bpres=xml(back['ppt/presentation.xml']);bpr=xml(back['ppt/_rels/presentation.xml.rels'])
brels={x.get('Id'):x for x in bpr}
nextrel=max(int(x.get('Id')[3:]) for x in pr if re.fullmatch(r'rId\d+',x.get('Id')))+1
for tag,child,reltype in [('sldMasterIdLst','sldMasterId','slideMaster'),('notesMasterIdLst','notesMasterId','notesMaster')]:
 lst=pres.find('p:'+tag,NS);blst=bpres.find('p:'+tag,NS)
 assert lst is not None
 for bitem in blst:
  rid=bitem.get('{'+NS['r']+'}id');part=resolve('ppt/presentation.xml',brels[rid].get('Target'))
  dest=import_part(part)
  nrid=f'rId{nextrel}';nextrel+=1
  E.SubElement(pr,'{'+NS['rel']+'}Relationship',Id=nrid,Type=NS['r']+'/'+reltype,Target=posixpath.relpath(dest,'ppt'))
  item=E.SubElement(lst,'{'+NS['p']+'}'+child)
  if tag=='sldMasterIdLst':item.set('id',str(max(int(x.get('id','0')) for x in lst)+1))
  item.set('{'+NS['r']+'}id',nrid)
out['ppt/presentation.xml']=dump(pres);out['ppt/_rels/presentation.xml.rels']=dump(pr)
# Keep any non-default table styles referenced by the appended native tables.
if 'ppt/tableStyles.xml' in back:
 t=xml(out['ppt/tableStyles.xml']);bt=xml(back['ppt/tableStyles.xml'])
 known={x.get('styleId'):x for x in t}
 for b in bt:
  sid=b.get('styleId')
  if sid in known:assert E.tostring(known[sid],method='c14n')==E.tostring(b,method='c14n'),sid
  else:t.append(deepcopy(b))
 out['ppt/tableStyles.xml']=dump(t)
# Recompute reachability so the replaced old pages and their orphan assets disappear.
keep={'[Content_Types].xml','_rels/.rels'}
def walk(owner):
 if owner in keep:return
 assert owner in out,owner
 keep.add(owner)
 rp=relpath(owner)
 if rp in out:
  keep.add(rp)
  for rel in xml(out[rp]):
   if rel.get('TargetMode')!='External':walk(resolve(owner,rel.get('Target')))
for rel in xml(out['_rels/.rels']):
 if rel.get('TargetMode')!='External':walk(resolve('',rel.get('Target')))
out={n:v for n,v in out.items() if n in keep}
for x in list(ct):
 if x.tag.endswith('Override') and x.get('PartName').lstrip('/') not in out:ct.remove(x)
out['[Content_Types].xml']=dump(ct)
if 'docProps/app.xml' in out:
 ap=xml(out['docProps/app.xml'])
 for x in ap:
  if E.QName(x).localname in ['Slides','Notes']:x.text='14'
 out['docProps/app.xml']=dump(ap)

# Verify the visual source XML is unchanged except the explicitly requested colors.
for i in range(1,8):
 for n in [f'ppt/slides/slide{i}.xml',f'ppt/slides/_rels/slide{i}.xml.rels',f'ppt/notesSlides/notesSlide{i}.xml']:
  assert out[n]==front[n],n
for i,n in enumerate(notes,1):
 merged=xml(out[f'ppt/slides/slide{i+7}.xml']);original=xml(back_original[f'ppt/slides/slide{i}.xml'])
 c=color_changes[i-1]
 title=merged.xpath('//p:sp[p:nvSpPr/p:cNvPr[@id="'+c['titleShapeId']+'"]]',namespaces=NS)[0]
 for clr in title.xpath('./p:txBody//a:srgbClr[@val="294F82"]',namespaces=NS):clr.set('val','15344E')
 for bid in c['navbarShapeIds']:
  for clr in merged.xpath('//p:sp[p:nvSpPr/p:cNvPr[@id="'+bid+'"]]/p:spPr/a:solidFill/a:srgbClr',namespaces=NS):clr.set('val','15344E')
 assert E.tostring(merged,method='c14n')==E.tostring(original,method='c14n'),i
 nr=xml(out[f'ppt/notesSlides/notesSlide{i+7}.xml'])
 paras=nr.xpath('//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody/a:p',namespaces=NS)
 text='\n'.join(''.join(p.xpath('.//a:t/text()',namespaces=NS)) for p in paras)
 for par in n['paragraphs']:assert par in text,(i,par)
for old,new in mapping.items():
 if old.startswith('ppt/media/') or old.startswith('ppt/charts/') or old.startswith('ppt/embeddings/'):
  if not old.endswith('.rels'):assert out[new]==back_original[old],old
candidate=D/'candidate_preserved.pptx'
with ZipFile(candidate,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
 for name,data in out.items():z.writestr(name,data)
audit={'slides':len(pres.find('p:sldIdLst',NS)),'front7_slideXML_identical':True,'front7_notes_identical':True,'back7_only_title_colors_changed':True,'notes_docx_paragraphs_preserved':sum(len(x['paragraphs']) for x in notes),'color_changes':color_changes,'part_mapping':mapping,'total_parts':len(out)}
(D/'merge_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(candidate)
print('Slides',audit['slides'],'parts',len(out),'notes paragraphs',audit['notes_docx_paragraphs_preserved'])
