from pathlib import Path
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE = Path(__file__).resolve().parent.parent
DATA = json.loads((BASE / '.build/content.json').read_text())

def set_font(style, size, bold=False):
    style.font.name = 'Times New Roman'
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    rf = style.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in list(rf.attrib):
        if 'theme' in attr.lower(): del rf.attrib[attr]
    rf.set(qn('w:eastAsia'), 'Songti SC')
    rf.set(qn('w:ascii'), 'Times New Roman')
    rf.set(qn('w:hAnsi'), 'Times New Roman')
    cs = style.element.get_or_add_rPr().find(qn('w:szCs'))
    if cs is not None: cs.set(qn('w:val'),str(int(size*2)))

def document(title):
    d = Document()
    for node in list(d.styles.element.iter(qn('w:pBdr'))):
        node.getparent().remove(node)
    sec = d.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.top_margin, sec.bottom_margin = Inches(.72), Inches(.7)
    sec.left_margin, sec.right_margin = Inches(.8), Inches(.8)
    set_font(d.styles['Normal'], 11.5)
    d.styles['Normal'].paragraph_format.line_spacing = Pt(17)
    d.styles['Normal'].paragraph_format.space_after = Pt(6)
    set_font(d.styles['Title'], 23, True)
    d.styles['Title'].paragraph_format.space_after = Pt(12)
    d.styles['Title'].paragraph_format.line_spacing = Pt(30)
    for name, size in [('Heading 1',17), ('Heading 2',14), ('Heading 3',12)]:
        set_font(d.styles[name], size, True)
        d.styles[name].paragraph_format.space_before = Pt(12)
        d.styles[name].paragraph_format.space_after = Pt(7)
        d.styles[name].paragraph_format.line_spacing = Pt(size+5)
    set_font(d.styles['Caption'],10)
    d.styles['Caption'].font.italic = False
    d.styles['Caption'].paragraph_format.space_after = Pt(6)
    d.styles['Caption'].paragraph_format.line_spacing = Pt(14)
    d.core_properties.title = title
    d.core_properties.subject = 'TerraScope 课堂汇报'
    d.core_properties.author = ''
    d.core_properties.keywords = 'TerraScope,受淹道路,课堂汇报'
    # Page numbers aid rehearsal and cross-reference across two multi-page documents.
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(); f=OxmlElement('w:fldSimple'); f.set(qn('w:instr'),'PAGE'); r._r.addnext(f)
    p.style = d.styles['Caption']
    d.add_paragraph(title, 'Title')
    return d

def para(d, text, label=None, style=None):
    p=d.add_paragraph(style=style)
    if label:
        p.add_run(label+'  ').bold=True
    p.add_run(text)
    p.paragraph_format.keep_together=True
    if label=='指图提示':p.paragraph_format.keep_with_next=True
    return p

def table(d, heads, rows, widths):
    t=d.add_table(rows=1, cols=len(heads))
    t.alignment=WD_TABLE_ALIGNMENT.CENTER
    t.autofit=False
    for col,w in zip(t.columns,widths): col.width=Inches(w)
    pr=t._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        item=OxmlElement('w:'+edge); item.set(qn('w:val'),'single');item.set(qn('w:sz'),'4');item.set(qn('w:color'),'D9D9D9');borders.append(item)
    pr.append(borders)
    for i,h in enumerate(heads): t.rows[0].cells[i].text=h
    for row in rows:
        cs=t.add_row().cells
        for i,v in enumerate(row): cs[i].text=str(v)
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for ri,row in enumerate(t.rows):
        no=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(no)
        for ci,cell in enumerate(row.cells):
            cell.width=Inches(widths[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=cell._tc.get_or_add_tcPr()
            mar=OxmlElement('w:tcMar')
            for edge, val in [('top','65'),('bottom','65'),('left','100'),('right','100')]:
                item=OxmlElement('w:'+edge);item.set(qn('w:w'),val);item.set(qn('w:type'),'dxa');mar.append(item)
            tcpr.append(mar)
            sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E6EDF4' if ri==0 else ('F6F8FA' if ri%2==0 else 'FFFFFF'));tcpr.append(sh)
            for p in cell.paragraphs:
                p.paragraph_format.space_after=Pt(0)
                p.paragraph_format.line_spacing=Pt(15)
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER if ci==0 else WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.size=Pt(10.5)
                    r.bold=ri==0
    d.add_paragraph().paragraph_format.space_after=Pt(1)
    return t

def save_clean(d, path):
    # Put page breaks on the next heading, avoiding a trailing empty break page.
    for p in list(d.paragraphs):
        if any(e.get(qn('w:type'))=='page' for e in p._p.iter(qn('w:br'))):
            nxt=p._p.getnext()
            if nxt is not None and nxt.tag==qn('w:p'):
                pr=nxt.find(qn('w:pPr'))
                if pr is None:pr=OxmlElement('w:pPr');nxt.insert(0,pr)
                flag=OxmlElement('w:pageBreakBefore');pr.append(flag)
                p._p.getparent().remove(p._p)
    d.save(path)

def review_block(d,r):
    d.add_heading(f"第{r['page']}页 {r['title']}",1)
    para(d,r['priority'],label='调整重点')
    para(d,r['finding'],label='当前页面')
    para(d,r['layout'],label='建议框架')
    para(d,r['copy'],label='可替换文案')
    para(d,r['detail'],label='美工与口径')

review=document('TerraScope 第8至14页优化建议')
para(review,'现有14页已形成完整叙事，建议保留页数与顺序。后半段的主要改进方向是减少同页的信息竞争、明确每组结果的比较对象，并让典型案例与调查应用各自承担不同任务。')
review.add_heading('优先完成的调整',1)
para(review,'第9页的“定位能力逐步提升”应改为中性比较标题，并交代四视图在448幅上存在指标取舍。第10页必须把“验证集选配置”放到视觉中心。第13页需明确覆盖率分母、整图指标以及有标签核验与新影像应用的区别。')
para(review,'版式工作优先处理第10、12页的密度，其次放大第11页的案例图。第8、13、14页主要做层级和标注调整，不需要推倒重做。')
review.add_heading('第8至14页的叙事分工',1)
table(review,['页码','本页回答的问题','观众需要记住'],[
 ['8','怎样评价','训练、调参与两批评估各司其职'],
 ['9','适配有没有用','主要定位收益来自任务微调'],
 ['10','为什么选这套配置','结构探索后按验证集选权重与推理方式'],
 ['11','具体改好了哪里','范围恢复与未淹误报抑制'],
 ['12','四视图单独带来什么','同权重下的额外留出评估'],
 ['13','调查人员怎样使用','定位、覆盖率记录与局部复核'],
 ['14','本组完成了什么','任务适配、实验选择与调查输出']
],[.48,1.62,4.8])
para(review,'维持当前页序即可。第9页先给结果，第10页解释选择依据，再用第11页展示空间证据；第12页单独隔离四视图收益，第13页回到应用。讲稿已按这一顺序连接。',label='结构建议')

for pair in [[0,1],[2,3],[4,5]]:
    review.add_page_break()
    for idx in pair:review_block(review,DATA['reviews'][idx])

review.add_page_break()
review_block(review,DATA['reviews'][6])
review.add_heading('统一的视觉规则',1)
para(review,'延续当前深蓝标题、白底和低饱和辅助色。方法比较统一用灰色表示原模型、蓝色表示优化单视图、绿色表示最终四视图。空间差异图另用绿色命中、金色遗漏、珊瑚红多检，并保留图例。')
para(review,'主标题建议28至32磅，正文20至24磅，重要数值32至40磅，投影中的辅助说明尽量不低于16磅。优先删除重复内容，再放大图表内部标注。现有导航栏、标题基线和页码位置保持一致。')
para(review,'第8至10页的绿色底栏与第11至13页的细线结论区建议统一，减少无意义的背景色变化。柱图去除密集纹理、保留少量浅网格；表格只强调关键结果，避免所有数据都同样抢眼。')
review.add_heading('核对依据',1)
para(review,'最新版 TerraScope_课堂汇报.pptx，14页；TerraScope_14页演讲大纲_详细展开版_v1.md，2026年10月18日。以下实验材料位于 TerraScope_队友Codex接续资料_20261016。',style='Caption')
para(review,'03_实验结果／指标口径与结论边界.md；当前汇报主要指标.json；7301实际像素核算与23幅变化.json；01_最终实验／最终方案选择.json、夜间实验结果说明.txt。案例数值另核对04_素材与源码／workspace／work／final_talk_20261016／assets／data.json。',style='Caption')
para(review,'解释边界：448幅测试数据此前用于过项目探索，不称为全新盲测。额外370幅属于同事件留出评价，不单独证明跨事件或跨地区泛化。',style='Caption')
save_clean(review,BASE/'TerraScope_第8至14页优化建议.docx')

speech=document('TerraScope 8分钟逐页讲稿')
para(speech,'讲稿按最新版14页PPT逐页编排，正文约1900字符。每页用时包含指图、停顿和切页，总预算8分钟。只朗读“讲述正文”；指图提示和备答内容不计入正文。具体语速以一次完整计时彩排校准。')
speech.add_heading('逐页时间表',1)
rows=[];elapsed=0
for s in DATA['slides']:
    s['start']=elapsed;elapsed+=s['seconds'];s['end']=elapsed
    fmt=lambda t:f'{t//60}:{t%60:02}'
    rows.append([s['page'],f"{s['seconds']}秒",f"{fmt(s['start'])} 至 {fmt(s['end'])}",s['title']])
table(speech,['页码','用时','时间位置','内容'],rows,[.45,.60,1.30,4.55])
para(speech,'第7页结束应约为3分45秒，第10页结束约为5分40秒，第13页结束约为7分35秒。若超时，先压缩第3页的模型能力说明、第10页的损失解释和第11页的数值，不删第9页的比较口径或第13页的覆盖率分母。',label='排练检查点')
para(speech,'术语可自然口读为“SEG提示”“SAM二”“IoU”；英文缩写不必额外解释每个字母。',style='Caption')

for group in [[0,1,2,3],[4,5,6,7],[8,9,10],[11,12,13]]:
    speech.add_page_break()
    for idx in group:
        s=DATA['slides'][idx]
        speech.add_heading(f"第{s['page']}页 {s['title']}",1)
        para(speech,f"{s['seconds']}秒  {fmt(s['start'])} 至 {fmt(s['end'])}",style='Caption')
        para(speech,s['cue'],label='指图提示',style='Caption')
        para(speech,s['speech'],label='讲述正文')

speech.add_page_break()
speech.add_heading('备答口径 不纳入8分钟正文',1)
qa=[
 ('为什么选择四视图','依据80幅验证影像，单视图IoU为61.29%，四视图为63.92%。448幅测试中，四视图IoU由58.63%略降至58.28%，误报由4降至2，命中由45降至44。额外370幅中，IoU由52.06%升至55.69%，误报10降至1，命中均为21／23。'),
 ('覆盖率误差0.83代表什么','它是全部448幅影像的覆盖率平均绝对误差，单位为百分点。其中399幅没有受淹道路。最终配置在49幅受淹影像上的覆盖率MAE约为5.77个百分点，因此不能说每幅受淹影像的误差只有0.83个百分点。'),
 ('21.75%的分母是什么','7301的预测受淹道路像素为152585，有效像素为701440，两者之比约21.75%。这一占比及IoU、精确率、召回率均是该样本整图统计，不是右侧局部窗口指标。'),
 ('场景命中与像素正确有什么区别','预测受淹道路覆盖率达到有效图像面积的1%即报出。场景命中只说明含目标影像被报出，具体像素是否圈准仍需看IoU等指标。全局IoU按全部有效像素汇总，不是逐图IoU的简单平均。'),
 ('能否证明泛化或直接指导通行','370幅来自同一洪灾事件，适合说明同事件留出影像上的表现。当前输出是影像中的道路掩膜与占比，不提供水深或通车判定，也没有充分的跨事件验证。448幅此前还用于过项目探索，不能称为完全未见的盲测。'),
 ('本组贡献与已有方法如何区分','TerraScope和SAM2是已有底座，四视图属于已有测试时增强方法。本组完成任务数据组织、投影层与解码器微调、训练与结构对照、推理配置选择，以及定位统计和核查图输出。最终方案没有使用语言LoRA或额外细节模块。')
]
for q,a in qa:
    speech.add_heading(q,2);para(speech,a)
para(speech,'核对材料：最新版14页PPT、详细展开版大纲，以及接续资料中的指标口径与结论边界、当前汇报主要指标、最终方案选择、7301像素核算与案例data.json。',style='Caption')
save_clean(speech,BASE/'TerraScope_8分钟逐页讲稿.docx')
print('Created review and speech documents')
print('Allocated seconds:',elapsed)
print('Speech characters including punctuation:',sum(len(s['speech']) for s in DATA['slides']))
