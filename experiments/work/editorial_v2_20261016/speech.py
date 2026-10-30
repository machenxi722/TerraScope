from pathlib import Path
import json
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

R=Path.cwd();W=R/'work/editorial_v2_20261016';talk=json.load(open(W/'talk.json'))
d=Document();sec=d.sections[0]
sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=Cm(1.7);sec.bottom_margin=Cm(1.7);sec.left_margin=Cm(2.1);sec.right_margin=Cm(2.1)
sec.header_distance=Cm(.7);sec.footer_distance=Cm(.7)
def font(style,name='Songti SC',size=12,color='203B32',bold=False):
 style.font.name=name;style.font.size=Pt(size);style.font.color.rgb=RGBColor.from_string(color);style.font.bold=bold
 style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),name)
font(d.styles['Normal']);n=d.styles['Normal'].paragraph_format;n.line_spacing=Pt(18);n.space_after=Pt(5)
font(d.styles['Title'],'微软雅黑',18,'00552B',True);d.styles['Title'].paragraph_format.space_after=Pt(5)
font(d.styles['Heading 1'],'微软雅黑',13.5,'00552B',True);d.styles['Heading 1'].paragraph_format.space_before=Pt(12);d.styles['Heading 1'].paragraph_format.space_after=Pt(3)
font(d.styles['Heading 2'],'微软雅黑',11,'476B5D',True)
for name in ['Heading 1','Heading 2']:d.styles[name].paragraph_format.keep_with_next=True
hp=sec.header.paragraphs[0];hp.text='TerraScope 洪灾道路智能解译  /  课堂汇报';hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
for r in hp.runs:r.font.name='微软雅黑';r.font.size=Pt(8);r.font.color.rgb=RGBColor.from_string('64776D')
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
rr=footer.add_run('—  ');rr.font.size=Pt(9)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field);footer.add_run('  —').font.size=Pt(9)
d.add_paragraph('TerraScope 洪灾道路智能解译',style='Title')
p=d.add_paragraph('14 页逐页演讲稿  ·  计划正文 7 分 10 秒  ·  含切页控制在 8 分钟内')
for r in p.runs:r.font.name='微软雅黑';r.font.size=Pt(9.5);r.font.color.rgb=RGBColor.from_string('5E776B')
p=d.add_paragraph('与版式重构版 PPT 对应。只朗读正文；每页末尾的指图提示供试讲时使用。')
for r in p.runs:r.font.size=Pt(9);r.font.color.rgb=RGBColor.from_string('6B7972')
fmt=lambda t:f'{t//60}:{t%60:02d}'
elapsed=0
for i,q in enumerate(talk):
 if i in [3,6,9,12]:d.add_page_break()
 d.add_paragraph(f'{i+1:02d}  {q["title"]}',style='Heading 1')
 p=d.add_paragraph(f'建议 {q["seconds"]} 秒  |  累计 {fmt(elapsed)}—{fmt(elapsed+q["seconds"])}');elapsed+=q['seconds']
 p.paragraph_format.space_after=Pt(4);p.paragraph_format.keep_with_next=True
 for r in p.runs:r.font.name='Times New Roman';r.font.size=Pt(9);r.font.color.rgb=RGBColor.from_string('708277')
 p=d.add_paragraph(q['speech']);p.paragraph_format.widow_control=True
 p=d.add_paragraph('指图提示：'+q['point']);p.paragraph_format.space_after=Pt(9)
 for r in p.runs:r.font.size=Pt(9);r.font.color.rgb=RGBColor.from_string('688174')
 # Keep a speech paragraph and its pointer on the same page.
 d.paragraphs[-2].paragraph_format.keep_with_next=True
d.core_properties.title='TerraScope 洪灾道路智能解译｜14页逐页演讲稿'
d.core_properties.subject='轻量任务微调与多视图稳健推理；课堂汇报，8分钟以内'
d.core_properties.author='TerraScope 项目组'
d.save(W/'speech_candidate.docx')
print('Saved',len(talk),'slides;',elapsed,'seconds')
