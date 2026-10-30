from pathlib import Path
import json, hashlib, math
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
BUILD = OUT / '_build'
BUILD.mkdir(exist_ok=True)
PKG = ROOT / 'TerraScope_队友Codex接续资料_20261016'
WORK = PKG / '04_素材与源码/workspace/work'
TTA = WORK / 'night_20261016/tta_backup/results'
FONT = '/System/Library/Fonts/STHeiti Light.ttc'
BOLD = '/System/Library/Fonts/STHeiti Medium.ttc'
BLUE = '#31568B'
INK = '#182B40'
MUTED = '#637488'

def font(size=20, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def audit():
    manifest=json.loads((PKG/'SHA256_MANIFEST.json').read_text())
    mismatches=[rel for rel,h in manifest.items() if not (PKG/rel).is_file() or hashlib.sha256((PKG/rel).read_bytes()).hexdigest()!=h]
    info={'审阅日期':'2026-10-16','清单文件数':len(manifest),'校验失败':mismatches,'汇总复算':[],'案例资产':[]}
    for mode in ['single_view','tta4']:
        for split in ['test','holdout','val']:
            d=json.loads((TTA/f'{mode}_{split}.json').read_text());rows=d['per_image']
            tp,fp,fn=[sum(r[k] for r in rows) for k in ['tp','fp','fn']]
            iou=tp/(tp+fp+fn)
            info['汇总复算'].append({'mode':mode,'split':split,'n':len(rows),'global_iou':iou,'matches':abs(iou-d['summary']['global_iou'])<1e-12})
    for dp in [WORK/'finetune_formal_20261015/data',WORK/'night_20261016/holdout/data']:
        for p in sorted(dp.glob('*/RGB.jpg')):
            sid=p.parent.name;im=Image.open(p);lab=np.array(Image.open(p.parent/'labels.png'))
            split=next((sp for sp in ['test','holdout','val'] if (TTA/'predictions/tta4'/sp/f'{sid}.png').exists()),'train')
            row={'sample_id':sid,'split':split,'width':im.width,'height':im.height,'rgb_path':str(p.relative_to(PKG)),'rgb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'label_path':str((p.parent/'labels.png').relative_to(PKG)),'has_gps_exif':bool(im.getexif().get(34853)),'has_final_prediction':split!='train'}
            if split!='train':
                maskpath=TTA/'predictions/tta4'/split/f'{sid}.png'
                m=np.array(Image.open(maskpath))>0;g=lab==3;v=lab!=255
                counts={'tp':int((m&g&v).sum()),'fp':int((m&~g&v).sum()),'fn':int((~m&g&v).sum()),'pred_pixels':int((m&v).sum()),'gt_pixels':int((g&v).sum()),'valid_pixels':int(v.sum())}
                saved=next(r for r in json.loads((TTA/f'tta4_{split}.json').read_text())['per_image'] if r['id']==sid)
                row.update(counts, pixel_counts_match=all(counts[k]==saved[k] for k in counts),prediction_path=str(maskpath.relative_to(PKG)),prediction_sha256=hashlib.sha256(maskpath.read_bytes()).hexdigest(),coverage_percent=counts['pred_pixels']/counts['valid_pixels']*100)
            info['案例资产'].append(row)
    (OUT/'资料审阅与案例资产核验.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    return info

def ui_figure():
    # A design wireframe with the existing, unmodified evidence image placed in a viewport.
    im=Image.new('RGB',(1800,1120),'#EEF2F6');d=ImageDraw.Draw(im)
    def txt(x,y,s,size=22,c=INK,b=False):d.text((x,y),s,font=font(size,b),fill=c)
    def rect(box,fill,outline=None,r=0):
        if r:d.rounded_rectangle(box,r,fill=fill,outline=outline,width=1)
        else:d.rectangle(box,fill=fill,outline=outline,width=1)
    rect((0,0,1800,70),'#172D47');txt(24,19,'TerraScope',31,'white',True);txt(225,24,'洪灾道路智能解译与调查平台',23,'#DCE7F6')
    txt(1275,25,'本地案例库  |  历史结果回放',21,'#DDE7F4');txt(1645,25,'审阅员',21,'white')
    rect((0,70,190,1120),'#FFFFFF')
    for y,s in [(105,'项目概览'),(170,'影像资料'),(235,'分析任务'),(300,'解译工作台'),(365,'人工复核'),(430,'实验评估'),(495,'报告中心'),(560,'系统设置')]:
        if s=='解译工作台':rect((12,y-10,178,y+42),'#E9F0FA',r=6)
        txt(30,y,s,24,BLUE if s=='解译工作台' else MUTED,s=='解译工作台')
    txt(216,90,'FloodNet 课程示范项目 / 影像 7301',27,INK,True)
    rect((1390,84,1568,126),'#FFFFFF','#C9D4E2',6);txt(1413,95,'保存复核',21)
    rect((1588,84,1777,126),BLUE,r=6);txt(1618,95,'生成报告',21,'white')
    rect((211,148,456,1002),'#FFFFFF')
    txt(229,170,'影像与图层',23,INK,True)
    for y,s,c in [(220,'7301  居民区道路',BLUE),(267,'7595  交叉路口',INK),(314,'7986  未淹道路',INK),(361,'7679  留出案例',INK)]:
        if y==220:rect((222,y-6,445,y+33),'#EDF3FB',r=3)
        txt(233,y,s,20,c)
    d.line((230,420,438,420),fill='#DCE3EC',width=1)
    txt(231,447,'显示图层',22,INK,True)
    for y,s,c in [(493,'原始 RGB',BLUE),(541,'四视图预测',BLUE),(589,'真实标签  评估用','#809C86'),(637,'空间差异  评估用','#C47D72'),(685,'人工复核标注','#B49450')]:
        rect((233,y+2,247,y+16),c,r=2);txt(260,y,s,18)
    txt(232,750,'叠加透明度',20,MUTED);d.line((235,798,424,798),fill='#B2C5DF',width=5);d.ellipse((327,790,343,806),fill=BLUE)
    txt(232,857,'坐标类型',19,MUTED);txt(232,889,'影像像素坐标',20,INK,True)
    txt(232,945,'无实地面积换算',18,MUTED)
    rect((474,148,1445,207),'#FFFFFF');txt(493,168,'平移   放大   卷帘   同步对比   绘制复核区',21)
    rect((474,221,1445,853),'#243547')
    asset=Image.open(WORK/'final_talk_20261016/assets/7301_tta4.png').convert('RGB')
    asset.thumbnail((941,610),Image.Resampling.LANCZOS)
    im.paste(asset,(474+(971-asset.width)//2,221+(632-asset.height)//2))
    d=ImageDraw.Draw(im)
    rect((494,238,751,278),'#172D47',r=5);txt(511,248,'四视图预测  历史结果',19,'white')
    rect((474,868,1445,1002),'#FFFFFF');txt(495,888,'任务记录',21,INK,True)
    txt(495,928,'结果版本  v1   ·   掩膜像素复算完成   ·   待人工复核',21)
    txt(495,967,'推理策略  tta4   |   阈值  logit > 0   |   影像  1024 × 685',18,MUTED)
    rect((1463,148,1780,1002),'#FFFFFF');txt(1487,171,'结果与证据',23,INK,True)
    txt(1487,230,'影像内预测覆盖率',21,MUTED);txt(1487,271,'21.75%',46,BLUE,True)
    txt(1487,345,'受淹道路像素',19,MUTED);txt(1487,378,'152,585 px',25,INK,True)
    txt(1487,430,'有效像素',19,MUTED);txt(1487,463,'701,440 px',25,INK,True)
    d.line((1488,517,1754,517),fill='#DCE3EC',width=1)
    txt(1487,544,'有标签评估',21,INK,True);txt(1487,590,'IoU                 73.35%',22);txt(1487,633,'精确率              92.18%',21);txt(1487,676,'召回率              78.22%',21)
    txt(1487,745,'复核结论',21,INK,True);rect((1487,790,1755,834),'#F6F8FB','#D1DAE5',3);txt(1501,801,'待复核',20,MUTED)
    txt(1487,877,'来源与版本',21,INK,True);txt(1487,921,'FloodNet / test / 7301',18);txt(1487,956,'long_bce_lovasz / tta4',17,MUTED)
    txt(215,1041,'界面设计示意  ·  功能与布局规划，尚未实现的软件界面',22,MUTED)
    txt(215,1080,'样例影像和数值来自已有实验；后续系统须由 API 读取并由后端核算。',19,MUTED)
    im.save(OUT/'解译工作台设计示意.png')

def architecture():
    im=Image.new('RGB',(1640,850),'white');d=ImageDraw.Draw(im)
    def box(x,y,w,h,title,sub,color='#EDF3FA'):
        d.rounded_rectangle((x,y,x+w,y+h),14,fill=color,outline='#C6D4E5',width=2)
        d.text((x+22,y+20),title,font=font(27,True),fill=INK)
        for i,s in enumerate(sub):d.text((x+22,y+64+i*32),s,font=font(21),fill=MUTED)
    def arrow(a,b):
        d.line((*a,*b),fill=BLUE,width=3)
        ang=math.atan2(b[1]-a[1],b[0]-a[0]);L=13
        pts=[b,(b[0]-L*math.cos(ang-.5),b[1]-L*math.sin(ang-.5)),(b[0]-L*math.cos(ang+.5),b[1]-L*math.sin(ang+.5))]
        d.polygon(pts,fill=BLUE)
    box(15,30,440,165,'Vue 3 + TypeScript 前端',['OpenLayers 影像工作台','Element Plus / ECharts / Pinia'])
    box(595,30,440,165,'Nginx + FastAPI 业务服务',['REST API / 认证与权限','项目 / 任务 / 复核 / 报告'])
    box(1180,30,440,165,'PostgreSQL 数据库',['业务状态 / 模型版本 / 审计','PostGIS 按地理数据能力启用'])
    arrow((455,112),(595,112));arrow((1035,112),(1180,112))
    box(595,280,440,165,'Redis 队列 + CPU Worker',['Celery 异步执行与失败恢复','统计 / 叠加 / 复核栅格化 / 报告'])
    box(1180,280,440,165,'本地资产卷',['原图 / 掩膜 / 证据 / 导出包','数据库记录资产 ID 与 SHA256'])
    arrow((815,195),(815,280));arrow((1035,362),(1180,362))
    box(15,570,440,180,'历史结果适配器',['严格匹配影像哈希和模型版本','加载真实掩膜，再执行后处理','普通笔记本可运行'],'#EFF5EF')
    box(595,570,440,180,'导入结果适配器',['接收外部生成的合规掩膜','验证网格 / 来源 / 模型清单','支持无网络交接'],'#FFF6E9')
    box(1180,570,440,180,'可选 GPU 模型服务',['独立 Linux CUDA 环境','基础权重 + 本组增量权重','对新影像执行真实推理'],'#FBEFEB')
    arrow((685,445),(235,570));arrow((815,445),(815,570));arrow((945,445),(1400,570))
    d.text((24,803),'主部署：5 个应用容器   |   GPU 服务按需接入   |   每个结果保留来源模式和版本',font=font(23),fill=MUTED)
    im.save(BUILD/'architecture.png')

def create_doc():
    doc=Document();sec=doc.sections[0]
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.top_margin=Cm(1.65);sec.bottom_margin=Cm(1.65);sec.left_margin=Cm(1.85);sec.right_margin=Cm(1.85)
    sec.footer_distance=Cm(.75)
    for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption']:
        s=doc.styles[name];s.font.name='Arial';s.font.color.rgb=RGBColor(0,0,0)
        rf=s.element.get_or_add_rPr().get_or_add_rFonts()
        for attr in list(rf.attrib):
            if 'theme' in attr.lower():del rf.attrib[attr]
        rf.set(qn('w:eastAsia'),'Songti SC')
        for b in s.element.xpath('./w:pPr/w:pBdr'):b.getparent().remove(b)
    doc.styles['Subtitle'].font.italic=False
    normal=doc.styles['Normal'];normal.font.size=Pt(10.5);normal.paragraph_format.line_spacing=1.14;normal.paragraph_format.space_after=Pt(6)
    for name,size in [('Title',24),('Subtitle',14),('Heading 1',18),('Heading 2',12)]:
        doc.styles[name].font.size=Pt(size);doc.styles[name].font.bold=name!='Subtitle'
        doc.styles[name].paragraph_format.space_before=Pt(9);doc.styles[name].paragraph_format.space_after=Pt(7)
    doc.styles['Caption'].font.size=Pt(9);doc.styles['Caption'].font.italic=False
    f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    rr=f.add_run('TerraScope 软件设计方案  ·  ');rr.font.size=Pt(8)
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');f._p.append(fld)
    doc.core_properties.title='TerraScope 洪灾道路智能解译与调查平台 功能设计与总体技术方案'
    doc.core_properties.subject='课程成果软件设计与开发验收'
    doc.core_properties.author='TerraScope 项目组'
    def p(text,bold=False,style=None):
        para=doc.add_paragraph(style=style);r=para.add_run(text);r.bold=bold
        return para
    def h(t):doc.add_heading(t,2)
    def page(n,title):
        heading=doc.add_heading(f'{n:02d}  {title}',1)
        heading.paragraph_format.page_break_before=True
    def table(headers,rows,widths=None,size=9.5):
        t=doc.add_table(rows=1, cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
        if widths:
            for c,w in zip(t.columns,widths):c.width=Cm(w)
        for i,txt in enumerate(headers):t.rows[0].cells[i].text=str(txt)
        for row in rows:
            for c,txt in zip(t.add_row().cells,row):c.text=str(txt)
        for ri,row in enumerate(t.rows):
            trpr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trpr.append(cant)
            if ri==0:
                repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
            for ci,c in enumerate(row.cells):
                if widths:c.width=Cm(widths[ci])
                c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                pr=c._tc.get_or_add_tcPr()
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E8EFF7' if ri==0 else ('F5F7FA' if ri%2==0 else 'FFFFFF'));pr.append(shade)
                borders=OxmlElement('w:tcBorders')
                for side in ['top','left','bottom','right']:
                    e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
                pr.append(borders)
                margins=OxmlElement('w:tcMar')
                for side,val in [('top',75),('bottom',75),('left',90),('right',90)]:
                    e=OxmlElement('w:'+side);e.set(qn('w:w'),str(val));e.set(qn('w:type'),'dxa');margins.append(e)
                pr.append(margins)
                for para in c.paragraphs:
                    para.paragraph_format.space_after=Pt(0);para.paragraph_format.line_spacing=1.08
                    for r in para.runs:r.font.size=Pt(size);r.bold=ri==0
        doc.add_paragraph().paragraph_format.space_after=Pt(0)
        return t
    def pic(path,width=17.2,alt=''):
        shape=doc.add_picture(str(path),width=Cm(width));shape._inline.docPr.set('descr',alt)

    doc.add_heading('TerraScope 洪灾道路\n智能解译与调查平台',0)
    p('功能设计与总体技术方案',style='Subtitle')
    p('软件规划 v1.0    2026 年 10 月 16 日    面向课程提交与课堂演示')
    h('建议建设目标')
    p('将已有受淹道路分割实验封装为一套前后端分离的调查软件，完成影像管理、任务处理、空间判读、人工复核和成果导出的业务闭环。核心成果是可运行的软件工程、可追溯的实验数据和可重复演示的操作流程。')
    p('首版采用 Vue 3 与 TypeScript 前端、FastAPI 后端、PostgreSQL 数据库和异步任务队列。普通笔记本运行完整业务系统，读取真实历史掩膜并执行统计、复核与报告生成；新影像的真实模型推理由可选 GPU 服务承担。',True)
    h('软件价值与现有研究的衔接')
    table(['已有研究成果','对应软件能力'],[
        ['受淹道路任务适配','固定任务模型注册、结果来源与模型版本展示'],
        ['单视图和四视图预测','同图同步对比、叠加判读与差异核查'],
        ['逐像素掩膜与逐景记录','后端核算覆盖率、导出掩膜和调查报告'],
        ['448 幅与 370 幅评估','实验评估中心，独立呈现两批结果与样本边界']
    ],[5.4,11.8])
    h('本次设计的交付边界')
    p('当前交付是开发方案与界面设计示意；各项软件功能按后文范围实施。课堂提交版以离线可用、数据真实、交互完整为验收基线，GPU 运行录像用于补充展示模型对新影像的实际推理。')
    p('“行业软件标准”落实到任务状态、权限、数据校验、版本追溯、异常恢复、自动化验收与可安装交付。首版使用模块化单体与独立任务进程，控制部署复杂度。')
    h('阅读顺序')
    p('第 2 页审阅结论；第 3 至 4 页功能与界面；第 5 至 10 页技术架构、模型、空间口径、数据和接口；第 11 至 14 页复核报告、部署验收、开发安排和依据。')

    page(2,'资料审阅结论与资产利用')
    p('审阅范围包括接续说明、14 页当前汇报及同步讲稿、最终实验指标、训练与四视图推理代码、样本清单、案例影像和历史材料目录。包内旧“只修改 PPT”文字属于历史任务背景，本轮软件设计范围由当前需求确定。')
    table(['核验项','结果与设计影响'],[
        ['文件完整性','SHA256 清单 13,091 个文件全部通过；全目录共 13,093 个文件，约 0.50 GB。'],
        ['指标汇总','单视图与四视图在验证、测试、留出三组数据的 6 份全局 IoU 均与逐景 TP、FP、FN 复算一致。'],
        ['可用原图','正式样例数据目录有 10 组 RGB 与语义标签；其中 9 组有对应最终四视图结果，像素统计复核一致。'],
        ['演示案例选择','7301、7461、7595、7986 为测试样例；6480、7558、7679 为留出样例；6598、6345 用于验证机制展示；6597 仅作训练示例。'],
        ['部署依赖','资料提供代码快照和预测结果；现场推理需另行配置完整底座权重、本组增量权重及相容 CUDA 环境。'],
        ['空间属性','上述 10 组 RGB 未检出 GPS EXIF；包内无可用 GeoTIFF 或地理配准配置。首版按影像坐标实现。']
    ],[3.3,13.9])
    h('基准结果应直接进入实验评估中心')
    table(['数据与方案','全局 IoU','覆盖率 MAE','命中','误报'],[
        ['448 幅 原模型','8.66%','5.05 pp','40/49','169/399'],
        ['448 幅 优化单视图','58.63%','0.81 pp','45/49','4/399'],
        ['448 幅 最终四视图','58.28%','0.83 pp','44/49','2/399'],
        ['370 幅 单视图','52.06%','0.70 pp','21/23','10/347'],
        ['370 幅 四视图','55.69%','0.60 pp','21/23','1/347']
    ],[5.2,2.6,3.3,3.0,3.1],9)
    p('四视图在 448 幅上的 IoU、覆盖率 MAE 与命中数并非全部改善；其主要优势是减少误报。370 幅来自同一灾害事件；448 幅此前用于项目探索，不能描述为全新盲测。训练、验证与评估分区必须明确标识。')
    p('818 幅可用于统计检索，但大多数未随包提供原图；缺原图时显示“仅统计记录”，不伪造可视化案例。')

    page(3,'功能范围与页面组织')
    p('主要用户为影像分析员、复核员和项目管理员。页面按业务对象组织，首页提供项目入口与任务进度，主要操作集中在解译工作台。P0 为提交必需，P1 为完成 P0 后增强，P2 为后续扩展。')
    table(['模块','P0 交付内容','可验收成果'],[
        ['项目概览','项目创建、说明、影像数、待处理与待复核任务、最近活动','项目数据刷新后保留；统计来自后端'],
        ['影像资料','JPG/PNG 导入、案例库、缩略图、哈希去重、数据分区和资产完整性','错误格式或缺配对文件得到明确提示'],
        ['分析任务','选择历史结果或真实推理；单视图/四视图；队列、取消、重试、阶段日志','任务状态持续保存，失败可定位'],
        ['解译工作台','原图与掩膜叠加、透明度、卷帘、同步视图、像素查询、同窗口缩放','各图层共用网格，无裁剪偏移'],
        ['人工复核','区域圈选、备注、确认/退回/需补充调查、复核版本和操作记录','原始预测保留，可查看历次结论'],
        ['实验评估','分区指标、单/四视图对比、逐景检索、GT 与 TP/FP/FN 差异图','无标签时不提供准确性指标'],
        ['报告中心','按结果快照生成 PDF、CSV、PNG 掩膜、JSON 元数据和证据包','导出数据与当前结果版本一致'],
        ['系统设置','用户角色、模型可用状态、软件与数据版本、日志和示范项目初始化','老师可按手册完成启动与验证']
    ],[2.9,8.7,5.6],9.4)
    h('P1 增强内容')
    p('人工增加/扣除区域并生成修订掩膜；批量报告；批量任务限流；带地理参考的 RGB GeoTIFF、真实空间面积和 GeoJSON 导出；模型服务健康监测；结果比较工作区保存。')
    h('P2 延伸方向')
    p('多事件验证、跨项目模型管理、具备真实地理数据后的路网交叉统计、多时相变化分析。自由对话助手、在线训练、三维地球与救援路线规划均不进入首版验收，避免超出已验证方法。')
    p('首版实现一条完整流程：创建项目 → 选取或导入影像 → 提交分析 → 查看结果 → 保存复核 → 导出报告。新增上传影像若无推理服务或匹配结果，应清楚显示可用操作。',True)

    page(4,'解译工作台与视觉设计')
    pic(OUT/'解译工作台设计示意.png',17.2,'解译工作台设计示意 左侧影像图层 中间航拍判读 右侧结果证据 底部任务记录')
    p('图 1  工作台设计示意。影像与数值采用真实案例 7301，页面控件为待开发设计。',style='Caption')
    h('页面布局')
    p('采用顶部项目栏、可折叠主导航、左侧影像与图层、中间判读视口、右侧结果与证据、底部任务记录。中间影像区域优先占用空间；1366×768 下默认收起导航文字和日志，右栏可折叠。')
    h('交互原则')
    p('双屏或四屏共享中心、缩放与同一像素窗口；原图采用完整视域适配，不以填满裁切改变坐标。切换方案只改变结果图层，复核标注仍绑定相同影像。透明度、图例和快捷键均在当前工作区可见。')
    p('右栏先展示覆盖率、受淹像素数、有效像素数和复核状态；有参考标签时再显示 IoU、精确率和召回率。任务来源使用持续可见的文字标签：“历史结果”“本次推理”“外部导入”。')
    h('统一视觉语言')
    p('延续现有作品的深蓝、鼠尾草绿、珊瑚红与柔金色。界面使用清晰的无衬线中文字体与浅色工作区；颜色与文字、形状共同表达状态。差异图使用固定 TP/FP/FN 图例，与任务成功/失败状态分开。')
    p('空项目、无标签、无地理参考、模型未连接、任务失败均有专门状态。演示全屏突出影像与操作，不以大面积装饰图表替代业务信息。')

    page(5,'完整技术栈与工程组织')
    table(['层次','选型','职责'],[
        ['前端工程','Vue 3 + TypeScript + Vite','单文件组件、类型检查、构建打包与代码拆分'],
        ['页面与状态','Vue Router + Pinia + Element Plus','路由、工作区状态、表格、表单、抽屉、反馈'],
        ['服务端数据','TanStack Vue Query + OpenAPI 类型生成','请求缓存与失效、任务轮询、类型一致的 API 调用'],
        ['空间视图与图表','OpenLayers + Apache ECharts','影像坐标图层、同步视图、卷帘、统计图表'],
        ['后端接口','Python 3.11 + FastAPI + Pydantic','请求校验、REST API、权限、OpenAPI 文档'],
        ['数据持久化','PostgreSQL + SQLAlchemy 2 + Alembic','事务、迁移、资产与任务版本；PostGIS 用于后续地理数据'],
        ['任务处理','Celery + Redis + CPU Worker','异步后处理、导出、重试、可恢复任务'],
        ['图像与空间处理','NumPy + Pillow；P1 加 Rasterio、Shapely','掩膜核算、缩略图、差异图、空间变换与几何计算'],
        ['模型运行','独立 PyTorch CUDA 环境','封装原有 TerraScope 推理，隔离旧模型依赖'],
        ['部署与验证','Nginx + Docker Compose；pytest、Vitest、Playwright','同源访问、多容器启动、核心计算与端到端验收']
    ],[2.7,7.2,7.3],9.1)
    h('为何这样选')
    p('Vue 的组件化与 TypeScript 适合表单、任务列表和复杂工作台。OpenLayers 支持自定义影像坐标，能够从本项目现有 JPG/PNG 逐步扩展到真实地理影像。Python 后端便于复用现有掩膜统计和推理代码。')
    p('耗时计算由队列进程执行；业务 API 只接收请求并返回任务 ID。PostgreSQL 保存业务事实，Redis 负责队列与短期缓存，文件放在挂载卷中。模型环境独立，避免其旧版依赖限制业务服务升级。')
    h('建议代码目录')
    p('frontend/src 按 projects、assets、tasks、workbench、reviews、reports 分模块；backend/app 对应 routers、services、models、schemas；worker 承担任务；model_service 独立；data/demo 保存授权案例；infra、tests、docs 保存部署、验收与说明。')
    p('建项时锁定已验证依赖版本，提交 pnpm 锁文件与 Python 锁定清单。CI 执行类型检查、核心测试和构建；不在方案阶段强行指定所有依赖的最新补丁版本。')

    page(6,'系统架构与任务生命周期')
    pic(BUILD/'architecture.png',15.4,'Vue 前端到 FastAPI 业务服务 再到数据库 队列 CPU Worker 和三种结果适配器的架构图')
    p('图 2  模块化业务服务与独立任务执行架构。GPU 服务可独立部署。',style='Caption')
    h('从请求到结果')
    p('上传时 API 检查格式、解码尺寸、大小和哈希，生成资产记录。创建任务时固化输入资产、模型版本、预处理、推理策略与来源模式，返回 HTTP 202 和任务 ID。Worker 加载数据或调用 GPU 服务，完成掩膜校验、统计和成果生成后原子提交结果。')
    p('前端以短间隔轮询获取阶段与日志；P1 可增加 SSE。进度使用已完成数量和真实阶段，模型无进度回调时显示耗时与“推理中”，不虚构完成百分比。')
    h('状态机')
    p('QUEUED → VALIDATING → LOADING_ARTIFACT 或 INFERENCING → POSTPROCESSING → SUCCEEDED。异常转入 FAILED；取消先记录 CANCEL_REQUESTED，再于安全检查点进入 CANCELED。排队任务可立即取消，GPU 运行任务允许延迟取消。')
    h('任务可靠性')
    p('数据库为状态真源。使用任务租约与心跳识别失联 Worker；恢复时校验结果目录与阶段检查点。POST 接口支持幂等键，队列至少一次投递由唯一执行键和结果唯一约束去重。产物先写临时位置，校验后提交，避免半成品被展示为成功。')
    p('批次逐图记录状态，仅重试失败项。缓存键包括影像哈希、模型摘要、预处理版本、推理策略与阈值，缓存命中须标明复用。默认 GPU 并发为 1，CPU 作业限流。')

    page(7,'模型接入与普通笔记本演示')
    table(['模式','输入与实际执行','界面与限制'],[
        ['历史结果回放\nhistorical_replay','严格匹配示例影像哈希、样本分区、模型及策略；加载真实保存的掩膜；CPU 实时计算统计与报告','标注历史结果及实验来源。任意新图不可套用案例掩膜。'],
        ['真实模型推理\nlive_inference','新影像经 API 提交到独立 GPU 模型服务，按相同协议返回二值掩膜和运行元数据','显示本次推理、设备、版本和耗时。服务缺失时禁止提交此模式。'],
        ['外部结果导入\nmanual_import','离线导入原图、掩膜、任务元数据及哈希清单，检查配对与网格一致性','明确外部来源；未经核验的模型描述不升级为已验证模型。']
    ],[4.1,7.4,5.7],9.5)
    h('真实推理的恢复步骤')
    p('取得基础模型、分词器、预处理配置与本组最终增量权重。记录基础模型版本与文件摘要，校验增量权重的键集合、张量形状及摘要。现有报告中的增量 SHA256 为 7c70b717815a39b66c052748c44256b685d17ef1513ee482084ce6419d93dfa8。')
    p('保留历史环境作为复现起点：记录显示使用 NVIDIA A800 80GB、PyTorch 2.3.1+cu121，源码依赖中含 transformers 4.42.3。该硬件是实验设备记录，不是已测出的最低显存要求。先以一个固定案例完成兼容性和资源基准。')
    p('从 eval_tta.py 提取独立的 RGB 推理函数。去除对标签、整套数据清单、旧服务器绝对路径及训练截止时间的启动依赖。标签与 valid_annotation 只由独立评估阶段读取，不进入模型前向输入。')
    h('必须保持的模型协议')
    p('固定 flooded roads 指令和 SEG 前缀；冻结底座，加载 SEG 投影及 SAM2 掩膜解码器增量。最终组合不启用 LoRA、空间提示或实验性模块。四视图为原图、水平翻转、垂直翻转、双向翻转；逆翻转 logits 后求均值，再双线性恢复原尺寸，以 logit > 0 二值化。')
    h('模型服务接口')
    p('GPU 服务以带幂等键的异步请求返回 job_id；CPU Worker 轮询状态并按资产摘要拉取结果。只通过受控 HTTPS 接口连接，不直接暴露 Redis 或数据库。超时后核对任务 ID 再重试；禁止静默切换到历史结果冒充新推理。')
    p('课堂可在 GPU 端预录“上传新图 → 实际推理 → 返回掩膜”的视频，并把真实产物导回笔记本继续复核和导出。仅提供录像不能替代本地业务系统验收。')

    page(8,'空间坐标与统计规则')
    h('影像坐标是首版空间基础')
    p('统一保存原图宽高和标准化方向，业务坐标以左上角为原点，x 向右、y 向下。OpenLayers 视图采用自定义像素投影，由适配层处理其显示坐标方向。约定像素中心为列号加 0.5、行号加 0.5，并保存裁剪、缩放和方向变换记录。')
    p('RGB、标签、预测与复核区使用同一原始网格。类别掩膜仅采用最近邻重采样；logits 的双线性恢复按原模型协议执行。缩略图只用于显示，统计必须使用原尺寸掩膜。裁剪图绑定同一窗口，禁止按视觉位置手工移动掩膜。')
    table(['指标或对象','定义与显示要求'],[
        ['目标与有效区','FloodNet 类别 3 为受淹道路，255 为无效标签。生产影像未提供有效区时以完整影像范围为分母并标明口径；有效像素为零则拒绝统计。'],
        ['覆盖率','100 × 预测受淹道路有效像素数 / 有效像素数；单位 %。不是所有道路中受淹占比。'],
        ['场景筛查','预测覆盖率 ≥ 1% 时标记达到筛查阈值。历史评估中真实阳性定义为存在目标像素；两者定义分别保存。'],
        ['IoU 与精确率','有 GT 才计算 IoU=TP/(TP+FP+FN)、Precision=TP/(TP+FP)、Recall=TP/(TP+FN)。分母为零按指标返回 null 并说明。'],
        ['全局 IoU','先对同一评估分区累加 TP、FP、FN，再算 IoU。不能用逐图 IoU 平均值替代。'],
        ['覆盖率 MAE','逐图预测覆盖率与参考覆盖率绝对差的均值；单位百分点 pp；与像素 IoU 分开呈现。'],
        ['多图汇总','显示逐图分布与处理数量；重叠航拍图不能直接累加成区域面积，影像数不等同于道路条数。']
    ],[3.4,13.8],9.4)
    h('地理能力按元数据开放')
    p('P1 接入带 CRS 与仿射变换的正射 RGB GeoTIFF。仅在坐标单位、投影和像元面积可靠时计算平方米；经纬度坐标须采用适当地理面积算法或等面积投影。单张斜视照片中的拍摄 GPS 不能代替像元地理配准。')
    p('无配准资产导出带明确 pixel 坐标定义的 JSON 与 PNG；有可靠配准时才导出标准地理 GeoJSON 或 GeoTIFF。首版像素多边形存为 JSONB，不伪造 EPSG:4326 坐标。')
    p('系统不以覆盖率生成“模型置信度”。仅有二值掩膜时不绘制概率热力图；没有 GT 的新影像不生成 IoU 或误差图；未达 1% 阈值也不等于道路可通行。')

    page(9,'数据模型与结果契约')
    p('以不可变原始资产和版本化结果为主线。用户可以修改项目描述、复核记录和展示参数，原始影像、模型预测以及已导出快照保留独立版本。')
    table(['实体','关键字段','关系与约束'],[
        ['User / ProjectMember','用户、项目、角色、状态','项目级权限；角色为管理员、分析员、复核员、只读'],
        ['Project','名称、事件说明、创建者、归档状态','一个项目对应多幅影像；示范项目可重建'],
        ['ImageAsset','哈希、宽高、格式、split、坐标模式、采集时间','不可变文件；采集时间未知则为空，不用导入时间代替'],
        ['ModelVersion','基础模型摘要、增量摘要、预处理、策略、可用状态','固定最终版本；真实推理前执行健康检查'],
        ['AnalysisTask','模式、输入资产、配置摘要、幂等键、状态、时间','每次执行独立；批次用 parent_id 关联'],
        ['Prediction','task_id、mask_asset_id、网格、模型版本、来源','原始预测不可被复核覆盖；一个执行键唯一结果'],
        ['MetricSet','valid_pixels、pred_pixels、口径、评估分区、可空 GT 指标','原始像素整数优先存储；展示时计算比例'],
        ['Review / Annotation','prediction_id、revision、结论、备注、pixel geometry','乐观锁版本号；原始预测和修订掩膜分开'],
        ['ReportSnapshot','结果版本、复核版本、模板版本、导出哈希','快照固定，复核更新后旧报告仍可追溯'],
        ['AuditEvent / AssetFile','操作人、动作、时间、对象版本；路径、媒体类型、SHA256','文件 ID 映射存储路径；日志不泄露凭据']
    ],[3.6,7.0,6.6],9.1)
    h('结果契约必须包含的内容')
    p('prediction_id、image_id、source_mode、model_version、strategy、threshold、preprocess_version、width、height、coordinate_mode、mask_asset_id、input_sha256、mask_sha256、validity_source、created_at。原始预测与复核派生结果另用 parent_prediction_id 或 revision 关联。')
    p('metrics 返回 pred_pixels、valid_pixels、coverage_percent、scene_threshold_percent；evaluation 可为空。有标签时再返回 TP、FP、FN、IoU 等；地理面积字段仅在 geographic 能力通过检查时返回数值。')
    h('一致性处理')
    p('结果先检查掩膜维度、值域、文件摘要和像素核算，再提交数据库事务。复核提交携带 base_revision，冲突返回 409 并显示差异。时间戳保存为 UTC，前端按本地时区显示；不使用文件名推断真实采集日期。')

    page(10,'接口设计与前后端契约')
    p('业务接口统一使用 /api/v1 前缀。FastAPI 生成 OpenAPI，前端由其生成类型；分页采用固定排序和分页参数，错误结构包含 code、message、request_id 与可展示的 field_errors。')
    table(['方法与路径','输入与结果','主要校验'],[
        ['POST /auth/login','登录凭据 → 受保护会话','失败限流，密码哈希校验'],
        ['GET /projects','项目列表与后端汇总','仅返回有权限的项目'],
        ['POST /projects','项目名称、说明 → 项目 ID','名称长度与成员权限'],
        ['POST /projects/{id}/images','multipart 文件 → 影像 ID','类型、解码、尺寸、体积、重复哈希'],
        ['GET /images/{id}','元数据、图层与可用操作','资产所属项目校验'],
        ['POST /analysis-tasks','影像 ID、mode、model、strategy → 202','能力可用、配置有效、幂等键'],
        ['GET /analysis-tasks/{id}','状态、阶段、已完成数量、错误','只读真实持久化状态'],
        ['POST /analysis-tasks/{id}/cancel','取消申请 → 状态','仅允许可取消阶段'],
        ['POST /analysis-tasks/{id}/retry','失败执行 → 新 attempt','旧记录保留，限制重试次数'],
        ['GET /predictions/{id}','掩膜资产与结果契约','区分来源、分母及评估能力'],
        ['POST /predictions/{id}/reviews','结论、备注、圈选区、base_revision','权限、坐标边界、乐观锁'],
        ['GET /experiments/{id}/metrics','分区、配置、汇总与逐景结果','保持 dataset 与 split 隔离'],
        ['POST /reports','项目、结果版本、复核版本 → 202','快照固定；模板与导出权限'],
        ['GET /assets/{id}/download','下载已授权资产','禁止任意文件路径，校验归属'],
        ['GET /system/capabilities','回放、导入、推理、地理能力','真实推理 availability 与原因']
    ],[6.4,6.3,4.5],8.8)
    h('约定的错误与状态')
    p('400 表示配置无效；401/403 表示认证或权限失败；404 表示资源不存在；409 表示状态或版本冲突；413 表示文件超限；422 表示图像或掩膜验证失败；503 表示模型服务不可用。失败响应不包含服务器堆栈或内部文件路径。')
    p('模型服务另设受控接口 /inference-jobs，接收影像资产与不可变推理配置；返回掩膜和元数据。该接口不接受 GT。前端不直接调用 GPU 服务，也不持有模型服务密钥。')

    page(11,'复核机制与成果报告')
    h('人工复核形成可追溯的调查记录')
    p('P0 允许在原图上圈出复核区域、填写判断依据，并提交“确认结果”“退回分析”“需补充调查”。圈选区域作为调查注记，不自动改变模型输出。每条记录保存操作者、时间、绑定结果版本与前一版本。')
    p('P1 增加掩膜修订：在原始网格上记录新增与扣除区域，按明确顺序栅格化为修订掩膜，重新计算指标并创建新版本。修订掩膜以人工复核结果命名，不能替换模型原始评估结果，也不能自动作为训练真值。')
    h('报告内容和导出包')
    table(['产物','内容','用途'],[
        ['PDF 调查报告','项目、影像来源、模型与策略、结果模式、原图/叠加图、覆盖率、复核意见、来源边界','课堂展示与老师审阅'],
        ['CSV 统计表','逐景样本 ID、分区、预测像素、有效像素、覆盖率、复核状态、结果版本','核对统计与二次分析'],
        ['PNG 掩膜与叠加图','原尺寸二值掩膜；独立可视化叠加；必要的差异图','结果复用与空间核查'],
        ['JSON 元数据','网格、分母口径、模型/输入摘要、来源模式、参数、复核版本','机器复现与资产导入'],
        ['ZIP 证据包','上述产物及文件哈希清单、简明说明','完整提交与离线交接']
    ],[3.6,8.8,4.8],9.5)
    p('报告从后端数据快照生成，图件在后端按固定尺寸重绘，不依赖浏览器截图或外部字体 CDN。P0 使用 ReportLab 与可分发中文字体；缺失 GT、采集时间或地理参考时相应字段留空或说明口径。')
    h('最小可用权限体系')
    p('管理员管理项目和成员；分析员导入影像、提交任务和生成草稿；复核员提交复核结论；只读用户浏览和下载允许的成果。前端按钮隐藏仅用于体验，所有读取和写入均由后端验证项目权限。课程演示账号允许兼具多个角色。')
    h('基础工程防护')
    p('采用 HttpOnly 会话 Cookie、CSRF 防护与同源部署；远程访问启用 HTTPS。上传采用扩展名、内容类型与解码联合校验，限制压缩体积和像素总数，资产使用随机 ID，避免任意路径访问。日志记录操作与 request_id，密钥通过环境变量提供。')
    p('模板静态资源随交付打包；SVG、HTML 等主动内容不作为普通图像上传执行。示范数据重置仅作用于独立示范项目。删除项目采用可恢复归档；核心资产引用仍有效时不物理删除。')

    page(12,'部署方式与验收标准')
    h('普通笔记本的交付方案')
    p('主方案使用 Docker Compose 启动 web、api、worker、postgres、redis 五个容器，CPU 模式不安装 CUDA。建议以 4 核 CPU、16 GB 内存作为首轮测试目标；8 GB 机器采用低并发配置单独验证，不预先承诺吞吐。Windows 使用 Docker 的 Linux 容器环境，避免原生 Windows Celery 兼容问题。')
    p('提交包包含 Windows 与 macOS 启动脚本、环境检查、数据库迁移与初始化命令、示范数据、预构建前端和容器镜像获取说明。若要求首次启动也完全离线，额外提供与目标平台匹配的镜像归档；演示前核验 amd64 与 arm64 支持。')
    p('运行数据使用持久化卷；停止服务后复核记录仍保留。提供项目备份与恢复命令、版本信息、日志导出和系统能力页。GPU 可远程部署，断网时本地案例、复核和导出流程继续可用。')
    h('必要的正确性与工程验收')
    table(['验收项','通过条件'],[
        ['资料与指标一致','7301 预测像素 152,585、有效像素 701,440、覆盖率约 21.7531%；与原始 JSON 一致。'],
        ['图层与坐标','四角、边界、同一裁剪窗口测试通过；翻转逆变换对齐；缩放不改变统计。'],
        ['模式真实性','历史结果标记可见；未知影像无匹配时不生成预测；无 GT 不返回 IoU。'],
        ['任务恢复','重启 API 不丢失记录；重复提交不生成重复结果；失败、取消、重试均有状态证据。'],
        ['权限与文件','跨项目访问被拒绝；超限图像、损坏文件和错误尺寸掩膜被拒绝。'],
        ['复核与导出','刷新后复核存在；并发修改触发冲突；导出报告绑定相同结果与复核版本。'],
        ['离线运行','断开外网完成示例选择、结果查看、复核、导出；无外部 CDN 和底图强依赖。'],
        ['资源与体验','目标机缓存后切图 p95 ≤ 1 秒、普通查询 p95 ≤ 500 ms、单景报告 ≤ 10 秒，作为待实测目标。']
    ],[3.7,13.5],9.4)
    p('用 pytest 覆盖像素指标、网格、有效区、适配器和权限；Vitest 覆盖关键界面状态；Playwright 验证一条完整业务流程与刷新持久化。GPU 延迟、显存、冷启动与四视图耗时另做基准，记录设备与输入尺寸，不宣称未经测量的实时性能。')

    page(13,'开发安排与课堂演示')
    p('建议按 3 至 4 人、2 至 3 周组织 P0，约 20 至 30 人日；这是排期估算，实际取决于熟练程度和模型环境恢复。优先完成数据到报告的纵向流程，再扩展页面覆盖。')
    table(['阶段','工作与负责人','完成门槛'],[
        ['第 1 至 2 天','共同冻结数据契约；模型同学确认权重可用性；建立项目骨架与案例资产索引','7301 可通过后端返回真实指标；明确 GPU 是否可接入'],
        ['第 3 至 6 天','前端实现影像工作台；后端实现资产、任务、数据库；算法同学实现掩膜核算适配器','创建项目到查看真实结果跑通'],
        ['第 7 至 10 天','前后端联调复核与报告；接入权限、任务失败处理；完成实验评估页面','可保存复核并导出一致的报告'],
        ['第 11 至 14 天','目标电脑部署、离线验证、端到端验收、说明书与录像','换一台电脑从提交包启动成功'],
        ['第 15 天以后','按余量开发 P1 修订掩膜或地理能力，算法同学完善 GPU 推理录像','不影响 P0 回归与演示稳定性']
    ],[3.2,9.0,5.0],9.3)
    h('并行分工')
    p('前端负责组件、空间交互与界面状态；后端负责权限、数据库、任务、报告与部署；算法数据负责资产导入、指标口径、推理适配与复现；第四人负责测试、说明书和演示。三人组由后端与前端共同承担测试交付。')
    h('建议八分钟软件演示')
    table(['时间','动作与讲解重点'],[
        ['0:00 至 0:40','项目入口与环境能力；说明本次使用真实历史结果。'],
        ['0:40 至 2:20','打开 7301，创建分析任务，展示原图、掩膜、覆盖率与来源记录。'],
        ['2:20 至 3:40','卷帘和同步缩放，指出受淹道路边界；有 GT 时展示空间差异。'],
        ['3:40 至 4:40','打开 7986 或 7679，对比误报抑制，说明评估分区。'],
        ['4:40 至 6:00','圈选复核区、保存结论、刷新页面验证记录、导出报告。'],
        ['6:00 至 7:00','播放已录制的真实 GPU 推理或展示模型来源与四视图机制。'],
        ['7:00 至 8:00','展示实验评估、技术架构、项目目录与老师可复现的启动方式。']
    ],[3.2,14],9.2)
    p('课程若只有总计八分钟，应压缩原 PPT 讲解，保留约四分钟软件操作。录屏呈现真实操作与实际来源，不加伪造的推理等待动画。提交 6 至 8 分钟完整演示视频，并准备约 90 秒备用剪辑。')

    page(14,'提交清单与设计依据')
    h('最终提交物')
    p('完整前后端源码、依赖锁定清单、数据库迁移、Compose 配置、启动与健康检查脚本；示范数据与哈希清单；用户手册、部署手册、接口文档和测试报告；至少一份真实导出证据包；系统演示视频；若已恢复模型，再附独立模型服务说明及权重获取与校验方法。')
    p('不将密钥、账号凭据或受限制的完整权重混入提交包。数据与模型保留原来源、许可说明和引用。PPT 中区分“已有实验结果”“本次完成的软件功能”“后续规划”。')
    h('本地依据索引')
    p('以下路径以 TerraScope_队友Codex接续资料_20261016 为根；软件导入器应保持原样本 ID、分区与来源，不依赖原作者机器的绝对路径。')
    table(['依据','相对路径或定位'],[
        ['项目任务与边界','00_项目一分钟讲清楚.md；03_实验结果/指标口径与结论边界.md'],
        ['当前指标与模型选择','03_实验结果/当前汇报主要指标.json；03_实验结果/01_最终实验/最终方案选择.json'],
        ['当前汇报与案例','01_当前汇报/ 主稿第 5、7、9、11、12、13 页及同步讲稿'],
        ['推理与逐景结果','04_素材与源码/workspace/work/night_20261016/eval_tta.py；tta_backup/results/'],
        ['原图与语义标签','workspace/work/finetune_formal_20261015/data/；night_20261016/holdout/data/，均位于 04_素材与源码 下'],
        ['7301 像素证据','04_素材与源码/workspace/work/editorial_v2_20261016/assets/measurements.json'],
        ['本轮核验记录','方案设计/资料审阅与案例资产核验.json，含案例哈希、路径及复算结果']
    ],[4.0,13.2],9.0)
    h('技术选型的官方依据')
    refs=[
        ('Vue 的 TypeScript 与 Vite 工程支持','https://vuejs.org/guide/typescript/overview'),
        ('OpenLayers 影像坐标投影示例','https://openlayers.org/en/latest/examples/static-image.html'),
        ('FastAPI 对重计算任务队列的说明','https://fastapi.tiangolo.com/tutorial/background-tasks/'),
        ('Celery 队列与平台支持','https://docs.celeryq.dev/en/stable/getting-started/introduction.html'),
        ('PostGIS 空间数据库扩展','https://postgis.net/documentation/getting_started/'),
        ('Docker Compose 多容器部署','https://docs.docker.com/compose/')
    ]
    for title,url in refs:
        para=p(title+'  '+url)
        for r in para.runs:r.font.size=Pt(8.5)
    p('官方资料查阅日期为 2026 年 10 月 16 日。方案中的技术组合、页面划分与排期属于针对本课程作品的工程设计建议；性能条目为开发验收目标。')
    path=OUT/'TerraScope_功能设计与总体技术方案_v1.0.docx';doc.save(path)
    print(path)

if __name__=='__main__':
    a=audit();print('AUDIT',len(a['案例资产']),'cases',len(a['校验失败']),'hash errors')
    ui_figure();architecture();create_doc()
