from pathlib import Path
from io import BytesIO
import json,re,hashlib,zipfile,os
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from pypdf import PdfReader,PdfWriter,Transformation
ROOT=Path.cwd();CLASSROOM=True;OUT=ROOT/'outputs'/('TerraScope_全部图件_清新论文版' if CLASSROOM else 'TerraScope_全部图件_期刊字体版');entries=json.loads((OUT/'图件目录.json').read_text());TOTAL=len(entries)+2;W,H=1152,700
pdfmetrics.registerFont(TTFont('Songti',str(ROOT/'work/journal_figures/fonts/SongtiSC-Regular.ttf')))
pdfmetrics.registerFont(TTFont('SongtiBold',str(ROOT/'work/journal_figures/fonts/SongtiSC-Bold.ttf')))
for n,p in [('TNR','Times New Roman.ttf'),('TNRBold','Times New Roman Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,'/System/Library/Fonts/Supplemental/'+p))
NAVY=HexColor('#303B40');GRAY=HexColor('#6D777B');TEAL=HexColor('#547C65')
def mixed(s,bold=False):
 return ''.join('<font name="'+(('TNRBold' if bold else 'TNR') if re.fullmatch(r'[\x20-\x7e]+',x) else ('SongtiBold' if bold else 'Songti'))+'">'+escape(x)+'</font>' for x in re.findall(r'[\x20-\x7e]+|[^\x20-\x7e]+',s))
def text(c,s,x,y,size=18,bold=False,color=NAVY,width=1000):
 p=Paragraph(mixed(s,bold),ParagraphStyle('p',fontName='Songti',fontSize=size,leading=size*1.5,textColor=color));w,h=p.wrap(width,1000);p.drawOn(c,x,y-h);return h
writer=PdfWriter();writer.page_mode='/UseOutlines'
def add_canvas(fn):
 b=BytesIO();c=canvas.Canvas(b,pagesize=(W,H),initialFontName='Songti');fn(c);c.save();writer.add_page(PdfReader(b).pages[0])
def cover(c):
 text(c,'商用时空信息软件平台 · 课程项目',66,633,19,color=GRAY)
 text(c,'TerraScope 遥感实验图集',66,490,42,True)
 text(c,'模型机制、证据核验与洪灾道路应用',66,408,27)
 text(c,f'{len(entries)} 张图 · 模型机制、实验结果与洪灾应用',66,296,20,color=GRAY)
 text(c,'清新论文版' if CLASSROOM else '正式成果 21 张；武汉探索材料 5 张',66,251,20,color=GRAY)
 text(c,'一页一图，目录与书签可定位。',66,130,17,color=GRAY)
 text(c,'2026 年 10 月 13 日',66,83,16,color=GRAY)
add_canvas(cover)
def contents(c):
 text(c,'图件目录',56,657,30,True)
 text(c,f'点击左侧书签定位；图号统一为 01—{len(entries)}，页码从本文件首页计数。',56,605,16,color=GRAY)
 split=15 if CLASSROOM else 16
 for col,items in enumerate([entries[:split],entries[split:]]):
  x=56+col*550;y=554;last=None
  for e in items:
   if e['group']!=last:
    text(c,e['group'],x,y,18,True,color=TEAL,width=510);y-=31;last=e['group']
   label=e['name'].replace('_','  ',1).replace('_',' · ')
   text(c,label,x+8,y,15,width=445)
   text(c,str(e['page']),x+475,y,15,color=GRAY,width=35)
   y-=24
 if not CLASSROOM:text(c,'正文推荐：模型结构、主实验对照、一致性核验、复核流程、FloodNet 流程与住宅区案例。',56,44,14,color=GRAY)
add_canvas(contents)
group_parent=None;previous=None
for e in entries:
 src=PdfReader(OUT/'PDF'/(e['name']+'.pdf')).pages[0];sw,sh=float(src.mediabox.width),float(src.mediabox.height)
 s=min(W/sw,648/sh);x=(W-sw*s)/2;y=26+(648-sh*s)/2
 page=writer.add_blank_page(width=W,height=H)
 page.merge_transformed_page(src,Transformation().scale(s).translate(x,y))
 b=BytesIO();c=canvas.Canvas(b,pagesize=(W,H),initialFontName='Songti')
 text(c,e['group'],32,26,11,color=GRAY,width=600);c.setFillColor(GRAY);c.setFont('TNR',11);c.drawRightString(W-32,13,f"{e['page']} / {TOTAL}")
 if e['group']=='武汉探索材料':text(c,'探索性材料：无独立洪灾标注',32,697,11,color=GRAY,width=600)
 else:text(c,f"图 {e['number']:02d}",32,697,11,color=GRAY,width=200)
 c.save();page.merge_page(PdfReader(b).pages[0])
 if previous!=e['group']:
  group_parent=writer.add_outline_item(e['group'],e['page']-1);previous=e['group']
 writer.add_outline_item(e['name'].replace('_',' ',1).replace('_',' · '),e['page']-1,parent=group_parent)
writer.add_metadata({'/Title':'TerraScope 遥感实验图集 - '+('清新论文版' if CLASSROOM else '期刊字体版'),'/Author':'课程项目小组','/Subject':f'中文宋体，英文数字 Times New Roman；{len(entries)}幅图的连续总览'})
target=OUT/('TerraScope_全部图件总览_清新论文版.pdf' if CLASSROOM else 'TerraScope_全部图件总览_期刊字体版.pdf')
with target.open('wb') as f:writer.write(f)
(OUT/'使用说明.txt').write_text('26张图统一为中文简体宋体、英文和数字Times New Roman。PNG为3200×1800；PDF保持矢量文字与图表；SVG文字以路径或字体定义保存。\n总览PDF共28页：封面、目录、26张图；包含书签。图01—21为正式图，图22—26为武汉探索材料。\n结果数值、图像与掩膜未改动。原版保留在旧交接包；本版图件位于PNG、SVG、PDF目录，可替换PPT中的对应图片。\n字体与颜色修改不改变实验协议或结论；7463仍用于标签边界核查，9022仍为误报案例。\n')
if CLASSROOM:(OUT/'使用说明.txt').write_text('清新论文版：已删除原图03“训练与本项目关系”，其余25张图连续编号。\n总览PDF为27页，含封面、目录及25张图，附书签。\n图件去掉来源脚注和防御性解释，保留标题、结果、坐标、单位与图例。中文宋体，英文和数字Times New Roman。\nPNG、SVG、PDF目录为可直接替换的图件。\n')
with (OUT/'图件目录.csv').open('w',encoding='utf-8-sig') as f:
 f.write('图号,分类,图名,总览页码\n')
 for e in entries:f.write(f"{e['number']},{e['group']},{e['name']},{e['page']}\n")
print(target)
