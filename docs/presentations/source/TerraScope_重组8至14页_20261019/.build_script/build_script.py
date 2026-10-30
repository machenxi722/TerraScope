from pathlib import Path
import json,re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT=Path('/Users/chenxi/Desktop/商用时空信息软件平台/outputs/TerraScope_重组8至14页_20261019')
slides=[
 {'page':8,'title':'数据与配置选择','seconds':50,'paragraphs':[
 '前面介绍了模型的任务适配方法，接下来说明实验如何展开。我们使用FloodNet航拍影像及受淹道路标签，300幅用于训练，80幅用于选择配置，另外448幅和370幅用于评估。评价同时关注道路位置、覆盖率误差和场景误报。',
 '中间的表格展示了结构与监督探索。分割头适配已带来主要收益，增加细节模块等方案没有稳定提升。因此，右侧进一步比较两种目标函数和三组随机种子，结合验证集选择权重，确定最终配置。下面看完整测试集的结果。']},
 {'page':9,'title':'完整测试集的定位与筛查效果','seconds':40,'paragraphs':[
 '在448幅测试影像上，左侧全局IoU从原始模型的8.66%提升到最终四视图配置的58.28%，增加49.62个百分点。右侧表格表明，覆盖率估算误差降至0.83个百分点；399幅未淹影像中的误报从169幅减少到2幅，受淹场景的命中也有提高。结合下方对照图，可以看到预测道路更加连续。我们再用三类场景具体说明这些变化。']},
 {'page':10,'title':'典型场景中的范围恢复与误报抑制','seconds':35,'paragraphs':[
 '这一页每一行依次展示原图、原始模型、最终配置和空间差异。上排交叉路口的受淹范围恢复得更完整；中排居民区道路更加连贯，IoU从31.32%提高到73.35%。下排是未淹道路，原始模型出现大面积误报，最终配置将误报覆盖率降为零。差异图帮助我们定位命中、遗漏和多检。我们又在额外370幅影像上，比较了两种推理方式。']},
 {'page':11,'title':'额外370幅影像上的四视图验证','seconds':40,'paragraphs':[
 '这里保持模型权重相同，对比单视图和四视图推理。左侧显示，全局IoU由52.06%提高到55.69%；未淹影像的误报从10幅降至1幅，减少90%，受淹场景仍命中23幅中的21幅。右侧两组图片展示了四视图消除误报的具体位置。左下方散点图中，23幅受淹影像有15幅得到改善，定位质量整体提高。下面把这些结果放到具体的调查判读中。']},
 {'page':12,'title':'道路定位与局部核查的调查应用','seconds':35,'paragraphs':[
 '以这幅居民区影像为例，左侧展示全幅预测，黄色窗口对应右侧的局部核查区域。全幅预测受淹道路占有效影像的21.75%，IoU为73.35%。把局部原图、预测、真实标签和差异图放在一起，可以确认主路识别比较连续，同时找到道路边缘的遗漏位置。这样，结果就能用于确定调查范围和人工核查重点。为方便完成这些操作，我们把模型接入了调查系统。']},
 {'page':13,'title':'受淹道路调查系统的操作流程','seconds':55,'paragraphs':[
 '这一页展示系统的完整流程，按中间三张截图从左向右看。先在影像库中筛选影像并导入项目，再由A800完成四视图分析，生成道路掩码和覆盖率。以7598影像为例，预测覆盖率为33.60%，IoU达到85.05%。随后对照误差图复核道路边缘，保存调查意见，并把复核版本关联到报告快照。',
 '系统支持成员按权限协作，统一查看历史实验和实时任务，导出报告、统计表与GIS点位。输入影像、模型策略和复核记录同步保存，方便回查分析依据。GPU在新影像推理时按需使用，已有结果保留在本地，减少重复计算。']},
 {'page':14,'title':'本组成果与汇报总结','seconds':25,'paragraphs':[
 '本组完成了受淹道路的轻量任务微调、四视图验证和调查系统实现。完整测试集的全局IoU比原始模型提高49.62个百分点；在额外验证中，四视图使未淹误报减少90%。这些成果共同支持道路定位、覆盖率统计和人工复核。我们的汇报到这里，谢谢大家。']},
]

def set_style(style,size,bold=False):
 style.font.name='Times New Roman'
 style.font.size=Pt(size)
 style.font.bold=bold
 style.font.color.rgb=RGBColor(0,0,0)
 rf=style.element.get_or_add_rPr().get_or_add_rFonts()
 for key in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:
  rf.attrib.pop(qn('w:'+key),None)
 for key,val in [('ascii','Times New Roman'),('hAnsi','Times New Roman'),('eastAsia','Songti SC')]:
  rf.set(qn('w:'+key),val)

def stamp(seconds):
 return f'{seconds//60}:{seconds%60:02d}'

doc=Document()
sec=doc.sections[0]
sec.page_width=Inches(8.5)
sec.page_height=Inches(11)
sec.top_margin=Inches(.7)
sec.bottom_margin=Inches(.7)
sec.left_margin=Inches(.8)
sec.right_margin=Inches(.8)
sec.header_distance=Inches(.3)
sec.footer_distance=Inches(.3)
normal=doc.styles['Normal'];set_style(normal,12)
normal.paragraph_format.line_spacing=Pt(18)
normal.paragraph_format.space_after=Pt(6)
normal.paragraph_format.widow_control=True
for style in doc.styles:
 if style.type==1:
  for elem in style.element.findall('.//'+qn('w:pBdr')):
   elem.getparent().remove(elem)
set_style(doc.styles['Title'],23,True)
doc.styles['Title'].paragraph_format.line_spacing=Pt(29)
doc.styles['Title'].paragraph_format.space_after=Pt(9)
set_style(doc.styles['Heading 1'],15.5,True)
doc.styles['Heading 1'].paragraph_format.space_before=Pt(12)
doc.styles['Heading 1'].paragraph_format.space_after=Pt(3)
doc.styles['Heading 1'].paragraph_format.line_spacing=Pt(21)
doc.styles['Heading 1'].paragraph_format.keep_with_next=True
set_style(doc.styles['Caption'],10.5)
doc.styles['Caption'].paragraph_format.line_spacing=Pt(14)
doc.styles['Caption'].paragraph_format.space_after=Pt(6)
doc.styles['Caption'].paragraph_format.keep_with_next=True
set_style(doc.styles['Footer'],9)

doc.add_paragraph('TerraScope 第8至14页逐页讲稿','Title')
p=doc.add_paragraph('对应深色专业版 v2，按第8至14页的展示顺序编排，建议用时共4分40秒。若整场控制在8分钟，前7页安排约3分20秒。各页时间已包含翻页过渡，累计时间从第8页开始计算。')
p.paragraph_format.space_after=Pt(3)
# The first three slides form the experimental setup and results on page one;
# page two follows validation, application, the system and the closing statement.
elapsed=0
for s in slides:
 p=doc.add_paragraph(f'第{s["page"]}页  {s["title"]}','Heading 1')
 if s['page']==11:
  p.paragraph_format.page_break_before=True
  p.paragraph_format.space_before=Pt(0)
 elapsed+=s['seconds']
 doc.add_paragraph(f'建议用时 {s["seconds"]} 秒　　累计 {stamp(elapsed)}','Caption')
 for text in s['paragraphs']:
  p=doc.add_paragraph(text)
  p.paragraph_format.keep_together=True

footer=sec.footer.paragraphs[0]
footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE')
footer._p.append(field)
doc.core_properties.title='TerraScope 第8至14页逐页讲稿'
doc.core_properties.subject='对应深色专业版 v2 的课堂汇报讲稿'
doc.core_properties.author='TerraScope 小组'
doc.core_properties.keywords='TerraScope 逐页讲稿 4分40秒'
path=OUT/'TerraScope_第8至14页逐页讲稿_v2.docx'
doc.save(path)
(OUT/'.build_script/content.json').write_text(json.dumps(slides,ensure_ascii=False,indent=2),encoding='utf-8')
for s in slides:
 t=''.join(s['paragraphs'])
 chars=len(re.findall(r'[\u4e00-\u9fff]',t))
 print(f'Page {s["page"]}: {s["seconds"]} sec, {chars} Chinese characters, {len(t)} text characters')
print(path)
