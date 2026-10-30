from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,re,hashlib
D=Path(__file__).resolve().parent
SOURCE=Path('/Users/chenxi/Desktop/商用时空信息软件平台/outputs/TerraScope_重组8至14页_20261019/TerraScope_第8至14页_深色专业版_v2.pptx')
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile('/Users/chenxi/Desktop/讲稿.docx') as z:
 root=E.fromstring(z.read('word/document.xml'))
 paras=[''.join(p.xpath('.//w:t/text()',namespaces=ns)) for p in root.xpath('//w:p',namespaces=ns)]
 groups=[]
 for t in paras:
  if re.fullmatch(r'\s*\d{2}\s*',t): groups.append({'sourceLabel':t,'paragraphs':[]})
  elif t.strip(): groups[-1]['paragraphs'].append(t)
assert len(groups)==7,len(groups)
titles=[]
with ZipFile(SOURCE) as z:
 for i,g in enumerate(groups,1):
  r=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
  # The requested main title is the upper, left-aligned dark-blue text shape.
  candidates=[]
  for s in r.xpath('//p:sp',namespaces=ns):
   t=''.join(s.xpath('.//a:t/text()',namespaces=ns))
   y=s.xpath('./p:spPr/a:xfrm/a:off/@y',namespaces=ns)
   colors=s.xpath('./p:txBody//a:srgbClr/@val',namespaces=ns)
   if t and y and 650000<int(y[0])<1100000 and '15344E' in colors:
    candidates.append(s)
  assert len(candidates)==1,[E.tostring(s) for s in candidates]
  s=candidates[0]; title=''.join(s.xpath('.//a:t/text()',namespaces=ns))
  g.update(page=i+7,title=title,titleShapeId=s.find('./p:nvSpPr/p:cNvPr',ns).get('id'))
  r=E.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml'))
  existing=r.xpath('//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]/p:txBody/a:p',namespaces=ns)
  original='\n'.join(''.join(p.xpath('.//a:t/text()',namespaces=ns)) for p in existing).strip()
  g['notesText']=f'第{i+7}页  {title}\n\n'+'\n\n'.join(g['paragraphs'])+'\n\n资料来源（备查）\n'+original
  print(i+7,title,'source label',g['sourceLabel'],'paragraphs',len(g['paragraphs']))
(D/'notes.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2),encoding='utf-8')
paths=[SOURCE,Path('/Users/chenxi/Desktop/TerraScope_课堂汇报_14页_v14_第四页左下布局舒展(1).pptx'),Path('/Users/chenxi/Desktop/讲稿.docx')]
(D/'source_hashes.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2),encoding='utf-8')
