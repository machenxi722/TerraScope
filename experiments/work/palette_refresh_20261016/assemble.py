from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import json,posixpath,re,hashlib
R=Path.cwd(); W=R/'work/palette_refresh_20261016'
SRC=R/'outputs/TerraScope_版式重构版_20261016/TerraScope_课堂汇报_14页_版式重构.pptx'
A='http://schemas.openxmlformats.org/drawingml/2006/main';P='http://schemas.openxmlformats.org/presentationml/2006/main';REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships';PKG='http://schemas.openxmlformats.org/package/2006/relationships';CT='http://schemas.openxmlformats.org/package/2006/content-types'
ns={'a':A,'p':P,'r':REL};q=lambda n:f'{{{A}}}{n}'
colors=json.loads((W/'palette.json').read_text());colors.pop('4C9B7D',None);colors['005826']='2F5597'
with ZipFile(SRC) as z: files={n:z.read(n) for n in z.namelist()}
def xml(b):return E.fromstring(b)
def out(t):return E.tostring(t,xml_declaration=True,encoding='UTF-8',standalone=True)
def recolor_tree(t):
 for c in t.iter(q('srgbClr')):
  old=c.get('val','').upper();c.set('val',colors.get(old,old))
def gradient(c1,c2):
 g=E.Element(q('gradFill'),rotWithShape='1');st=E.SubElement(g,q('gsLst'))
 for v,c in [(0,c1),(100000,c2)]:E.SubElement(E.SubElement(st,q('gs'),pos=str(v)),q('srgbClr'),val=c)
 E.SubElement(g,q('lin'),ang='5400000',scaled='1');return g
def blend(c,d,t):return ''.join(f'{round(int(c[i:i+2],16)*(1-t)+int(d[i:i+2],16)*t):02X}' for i in (0,2,4))
def pattern(bg):
 p=E.Element(q('pattFill'),prst='ltDnDiag')
 E.SubElement(E.SubElement(p,q('fgClr')),q('srgbClr'),val=blend(bg,'7086A4',.13))
 E.SubElement(E.SubElement(p,q('bgClr')),q('srgbClr'),val=bg)
 return p
for n,b in list(files.items()):
 if not n.endswith('.xml'):continue
 try:t=xml(b)
 except E.XMLSyntaxError:continue
 recolor_tree(t)
 # Scientific panel treatment stays behind content and does not touch photos or masks.
 if n.startswith(('ppt/slides/slide','ppt/slideMasters/','ppt/slideLayouts/')):
  for sp in t.findall('.//p:sp',ns):
   pr=sp.find('p:spPr',ns)
   if pr is None:continue
   c=pr.find('a:solidFill/a:srgbClr',ns);ext=pr.find('a:xfrm/a:ext',ns)
   if c is None or ext is None:continue
   w=int(ext.get('cx'))/9525;h=int(ext.get('cy'))/9525
   color=c.get('val');fill=pr.find('a:solidFill',ns)
   if color=='294F82' and w*h>20000:
    i=pr.index(fill);pr.remove(fill);pr.insert(i,gradient('3B659A','274974'))
   elif color in ['DFEBCF','DCE5F4','F6E8B8'] and w>300 and h>45:
    i=pr.index(fill);pr.remove(fill);pr.insert(i,pattern(blend(color,'FFFFFF',.35)))
 files[n]=out(t)

talk=json.loads((R/'work/editorial_v2_20261016/talk.json').read_text())
updates={
4:('TerraScope 原理：语言引导分割与证据回注','这张图介绍 TerraScope 的核心机制。左侧影像和问题进入多模态语言模型。当模型生成 SEG 标记，隐藏状态会经过投影层，变成 SAM2 可用的分割提示。下方 SAM2 结合图像特征生成像素掩膜。右侧再利用掩膜选取区域视觉信息，回注语言模型，为回答提供区域证据。我们在这个底座上，将任务收敛到受淹道路识别，重点适配提示投影和掩膜解码这两个环节。','按语言输入、SEG 投影、SAM2 掩膜、REGION 回注顺序讲解。道路专用推理采用固定 SEG 前缀。'),
5:('本组流程：任务适配、四视图推理与调查统计','我们的工作分成训练和使用两个阶段。左侧用三百幅标注影像适配模型，由八十幅验证影像选择权重。右上把同一影像的四个视图输入同一模型，将预测恢复到原坐标后融合。右下输出受淹位置、覆盖率和逐景记录。底部的两组独立留出评估，用来检查定位能力和场景误报。','先左侧 A，再右上 B，最后右下 C。底部结果只作概括，不逐项复述。扩展集来自同一事件。'),
6:('受淹道路任务适配：SEG 投影与 SAM2 解码器微调','具体训练哪里，看中间两个模块。蓝色雪花标记的视觉和语言主干保持冻结。第一个训练模块把语言模型的目标表示，映射成二百五十六维的分割提示。第二个是 SAM2 掩膜解码器，让提示与多尺度图像特征交互，恢复受淹道路的边界。右侧用预测和标签计算分割损失，反向更新只作用于这两个模块，总计约一千八百万参数。','依次指两个中央模块和右侧损失。说明火焰、雪花含义，避免逐个读出所有内部层。7301 仅作本地输出示例，不属于训练集。')}

def set_notes(slide_n,text):
 relname=f'ppt/slides/_rels/slide{slide_n}.xml.rels';rels=xml(files[relname]);target=None
 for rel in rels:
  if rel.get('Type','').endswith('/notesSlide'):target=posixpath.normpath(posixpath.join('ppt/slides',rel.get('Target'))).lstrip('/')
 if target is None:return
 nt=xml(files[target]);body=None
 for sp in nt.findall('.//p:sp',ns):
  ph=sp.find('p:nvSpPr/p:nvPr/p:ph',ns)
  if ph is not None and ph.get('type')=='body':body=sp.find('p:txBody',ns);break
 if body is None:return
 for p in list(body):
  if p.tag==q('p'):body.remove(p)
 for line in text.splitlines():
  p=E.SubElement(body,q('p'));run=E.SubElement(p,q('r'));E.SubElement(run,q('t')).text=line
 files[target]=out(nt)

def scale_tree(t,factor):
 for el in t.iter():
  # Real coordinates and font sizes, not cropping percentages or custom path coordinates.
  loc=E.QName(el).localname
  if loc in ['off','ext','chOff','chExt'] and el.getparent() is not None and E.QName(el.getparent()).localname=='xfrm':
   for key in ['x','y','cx','cy']:
    if key in el.attrib:el.set(key,str(round(int(el.get(key))*factor)))
  if loc in ['rPr','defRPr','endParaRPr'] and 'sz' in el.attrib:el.set('sz',str(round(int(el.get('sz'))*factor)))
  if loc=='ln' and 'w' in el.attrib:el.set('w',str(round(int(el.get('w'))*factor)))
  if loc=='gridCol' and 'w' in el.attrib:el.set('w',str(round(int(el.get('w'))*factor)))
  if loc=='tr' and 'h' in el.attrib:el.set('h',str(round(int(el.get('h'))*factor)))
  if loc in ['bodyPr','tcPr']:
   for key in ['lIns','rIns','tIns','bIns','marL','marR','marT','marB']:
    if key in el.attrib:el.set(key,str(round(int(el.get(key))*factor)))
  if loc in ['spcPts','buSzPts'] and 'val' in el.attrib:el.set('val',str(round(int(el.get('val'))*factor)))

def clear_canvas(root):
 tree=root.find('p:cSld/p:spTree',ns)
 for el in list(tree):
  if E.QName(el).localname not in ['nvGrpSpPr','grpSpPr']:tree.remove(el)
 return root
# A dedicated empty layout/master prevents inherited navigation from covering full-page figures.
layout_name='ppt/slideLayouts/paletteBlank.xml';master_name='ppt/slideMasters/paletteMaster.xml'
blank=clear_canvas(xml(files['ppt/slideLayouts/slideLayout10.xml']));blank.set('type','blank');blank.set('showMasterSp','0')
lr=xml(files['ppt/slideLayouts/_rels/slideLayout10.xml.rels'])
original_master=next(x.get('Target') for x in lr if x.get('Type','').endswith('/slideMaster'))
original_master=posixpath.normpath(posixpath.join('ppt/slideLayouts',original_master)).lstrip('/')
master=clear_canvas(xml(files[original_master]));ml=master.find('p:sldLayoutIdLst',ns)
for el in list(ml):ml.remove(el)
E.SubElement(ml,f'{{{P}}}sldLayoutId',id='2147483649',attrib={f'{{{REL}}}id':'rIdBlankLayout'})
mrname=posixpath.join(posixpath.dirname(original_master),'_rels',posixpath.basename(original_master)+'.rels')
mr=xml(files[mrname])
for rel in list(mr):
 if not rel.get('Type','').endswith('/theme'):mr.remove(rel)
E.SubElement(mr,f'{{{PKG}}}Relationship',Id='rIdBlankLayout',Type=REL+'/slideLayout',Target='../slideLayouts/paletteBlank.xml')
lr=E.Element(f'{{{PKG}}}Relationships',nsmap={None:PKG});E.SubElement(lr,f'{{{PKG}}}Relationship',Id='rIdBlankMaster',Type=REL+'/slideMaster',Target='../slideMasters/paletteMaster.xml')
files[layout_name]=out(blank);files[master_name]=out(master);files['ppt/slideLayouts/_rels/paletteBlank.xml.rels']=out(lr);files['ppt/slideMasters/_rels/paletteMaster.xml.rels']=out(mr)
pres=xml(files['ppt/presentation.xml']);sl=pres.find('p:sldMasterIdLst',ns);nextid=max(int(x.get('id')) for x in sl)+1
E.SubElement(sl,f'{{{P}}}sldMasterId',id=str(nextid),attrib={f'{{{REL}}}id':'rIdPaletteMaster'});files['ppt/presentation.xml']=out(pres)
pr=xml(files['ppt/_rels/presentation.xml.rels']);E.SubElement(pr,f'{{{PKG}}}Relationship',Id='rIdPaletteMaster',Type=REL+'/slideMaster',Target='slideMasters/paletteMaster.xml');files['ppt/_rels/presentation.xml.rels']=out(pr)
ct=xml(files['[Content_Types].xml'])
for n,kind in [(layout_name,'slideLayout'),(master_name,'slideMaster')]:E.SubElement(ct,f'{{{CT}}}Override',PartName='/'+n,ContentType=f'application/vnd.openxmlformats-officedocument.presentationml.{kind}+xml')
files['[Content_Types].xml']=out(ct)
report=[]
for slide_n,name,factor in [(4,'principle',1),(5,'workflow',.8),(6,'training',.8)]:
 src=W/'figures'/name/'candidate.pptx'
 with ZipFile(src) as z:sf={n:z.read(n) for n in z.namelist()}
 st=xml(sf['ppt/slides/slide1.xml']);tree=deepcopy(st.find('p:cSld/p:spTree',ns));scale_tree(tree,factor)
 dest=xml(files[f'ppt/slides/slide{slide_n}.xml']);parent=dest.find('p:cSld',ns);parent.replace(parent.find('p:spTree',ns),tree)
 # Full-page method figures: the retained notes and blanked master do not overlay them.
 dest.set('showMasterSp','0')
 relpath=f'ppt/slides/_rels/slide{slide_n}.xml.rels';dr=xml(files[relpath])
 for rel in list(dr):
  if not rel.get('Type','').endswith(('/slideLayout','/notesSlide')):dr.remove(rel)
  elif rel.get('Type','').endswith('/slideLayout'):rel.set('Target','../slideLayouts/paletteBlank.xml')
 sr=xml(sf['ppt/slides/_rels/slide1.xml.rels']);mapping={};count=0
 for rel in sr:
  if rel.get('Type','').endswith('/image'):
   count+=1;old=posixpath.normpath(posixpath.join('ppt/slides',rel.get('Target'))).lstrip('/')
   ext=Path(old).suffix;new=f'ppt/media/palette_{name}_{count}{ext}';files[new]=sf[old]
   newid=f'rIdFigure{count}';mapping[rel.get('Id')]=newid
   E.SubElement(dr,f'{{{PKG}}}Relationship',Id=newid,Type=rel.get('Type'),Target='../media/'+Path(new).name)
 for el in tree.iter():
  for key in [f'{{{REL}}}embed',f'{{{REL}}}link',f'{{{REL}}}id']:
   if el.get(key) in mapping:el.set(key,mapping[el.get(key)])
 files[relpath]=out(dr);files[f'ppt/slides/slide{slide_n}.xml']=out(dest)
 title,speech,point=updates[slide_n];talk[slide_n-1].update(title=title,speech=speech,point=point)
 sn=xml(sf['ppt/notesSlides/notesSlide1.xml']);refs='\n'.join(sn.xpath('//a:t/text()',namespaces=ns))
 set_notes(slide_n,f'第 {slide_n} 页｜{title}\n目标 {talk[slide_n-1]["seconds"]} 秒\n\n【演讲正文】\n{speech}\n\n【指图提示，不朗读】\n{point}\n\n【图示依据，不朗读】\n{refs}')
 report.append({'slide':slide_n,'native_shapes':len(tree.findall('.//p:sp',ns)),'images':count,'scale':factor})

# Repeated real images share a byte-identical media part, with no resampling.
by_hash={};duplicates={}
for n,b in files.items():
 if n.startswith('ppt/media/'):
  k=hashlib.sha256(b).hexdigest()
  if k in by_hash:duplicates[n]=by_hash[k]
  else:by_hash[k]=n
for n,b in list(files.items()):
 if not n.endswith('.rels'):continue
 root=xml(b);changed=False
 owner=posixpath.join(posixpath.dirname(posixpath.dirname(n)),posixpath.basename(n)[:-5]) if n!='_rels/.rels' else ''
 for rel in root:
  if rel.get('TargetMode')=='External':continue
  target=rel.get('Target','');full=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner),target))
  if full in duplicates:rel.set('Target',posixpath.relpath(duplicates[full],posixpath.dirname(owner)));changed=True
 if changed:files[n]=out(root)

# Keep only the actual presentation graph; obsolete figures are removed from the package.
def rel_path(part):
 return posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels') if part else '_rels/.rels'
seen=set();todo=['']
while todo:
 part=todo.pop();rp=rel_path(part)
 if part:seen.add(part)
 if rp in seen or rp not in files:continue
 seen.add(rp)
 for rel in xml(files[rp]):
  if rel.get('TargetMode')=='External':continue
  target=rel.get('Target','');full=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part),target))
  if full in files and full not in seen:todo.append(full)
seen.add('[Content_Types].xml');ct=xml(files['[Content_Types].xml'])
for el in list(ct):
 if el.tag==f'{{{CT}}}Override' and el.get('PartName','').lstrip('/') not in seen:ct.remove(el)
for ext,mime in [('png','image/png'),('jpg','image/jpeg'),('jpeg','image/jpeg')]:
 if not any(el.get('Extension')==ext for el in ct):E.SubElement(ct,f'{{{CT}}}Default',Extension=ext,ContentType=mime)
files['[Content_Types].xml']=out(ct)
dest=W/'candidate.pptx'
with ZipFile(dest,'w',ZIP_DEFLATED,compresslevel=6) as z:
 for n,b in files.items():
  if n in seen:z.writestr(n,b)
(W/'talk.json').write_text(json.dumps(talk,ensure_ascii=False,indent=2))
(W/'assembly.json').write_text(json.dumps({'figures':report,'total_slides':14,'seconds':sum(x['seconds'] for x in talk),'bytes':dest.stat().st_size,'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest()},indent=2))
print(json.dumps({'candidate':str(dest),'MiB':round(dest.stat().st_size/2**20,2),'figures':report},ensure_ascii=False))
