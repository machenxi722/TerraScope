import csv
import io
import json
import logging
import time
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as PDFImage,
    Table,
    TableStyle,
)
from sqlalchemy import select, update
from ..config import settings
from ..db import SessionLocal
from ..models import ImageAsset, ReportSnapshot, uid
from .storage import read_asset, save_asset, sha256

log = logging.getLogger(__name__)
SOURCE_LABELS = {
    "historical_replay": "历史结果",
    "manual_import": "外部导入",
    "live_inference": "本次推理",
}
DECISIONS = {
    "confirmed": "确认结果",
    "returned": "退回分析",
    "needs_investigation": "需补充调查",
}


def pdf_report(snapshot, original, overlay):
    if "NotoSC" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("NotoSC", str(settings.font_path)))
    stream = io.BytesIO()
    doc = SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=40,
        bottomMargin=40,
        title="TerraScope 洪灾道路调查报告",
        author="TerraScope",
    )
    style = ParagraphStyle(
        "body", fontName="NotoSC", fontSize=10, leading=16, wordWrap="CJK", spaceAfter=7
    )
    heading = ParagraphStyle(
        "heading", parent=style, fontSize=17, leading=24, spaceAfter=12
    )
    story = []

    def p(text, title=False):
        story.append(
            Paragraph(
                escape(str(text)).replace("\n", "<br/>"), heading if title else style
            )
        )

    result, image = snapshot["prediction"], snapshot["image"]
    contract, metrics = result["contract"], result["metrics"]
    p("TerraScope 洪灾道路调查报告", True)
    p(
        f"项目：{snapshot['project']['name']}　样本：{image.get('sample_id') or image['name']}"
    )
    p(f"结果来源：{SOURCE_LABELS[contract['source_mode']]}　数据分区：{image['split']}")
    p(
        f"模型：{contract['model_version']}　策略：{contract['strategy']}　阈值：{contract['threshold']}"
    )
    p(
        f"影像：{image['width']} × {image['height']} 像素　坐标：左上角原点，x 向右、y 向下"
    )
    p(
        f"影像内预测覆盖率：{metrics['coverage_percent']:.4f}%　受淹道路像素：{metrics['pred_pixels']:,}　有效像素：{metrics['valid_pixels']:,}"
    )
    p(
        f"分母依据：{metrics['validity_source']}。覆盖率不是所有道路中的受淹比例；未达筛查阈值不代表可通行。"
    )
    p("采集时间：" + (image.get("acquired_at") or "未知"))
    if location := image.get("location"):
        p(f"GPS 拍摄点：纬度 {location['latitude']:.6f}°，经度 {location['longitude']:.6f}°（WGS 84）。")
    p("解译统计采用像素坐标，GPS 记录相机位置。")
    if result["evaluation"]:
        e = result["evaluation"]
        fmt = lambda x: "未定义（分母为零）" if x is None else f"{x * 100:.2f}%"
        p(
            f"参考标签评估：IoU {fmt(e['iou'])}；精确率 {fmt(e['precision'])}；召回率 {fmt(e['recall'])}。"
        )
        p(
            f"TP {e['tp']:,} / FP {e['fp']:,} / FN {e['fn']:,}。覆盖率误差 {e['coverage_error_pp']:.4f} pp。"
        )
    else:
        p("未提供参考标签，不计算 IoU、精确率、召回率或误差图。")
    width = 244
    height = width * image["height"] / image["width"]
    table = Table(
        [
            [
                PDFImage(io.BytesIO(original), width=width, height=height),
                PDFImage(io.BytesIO(overlay), width=width, height=height),
            ],
            [Paragraph("原始影像", style), Paragraph("预测叠加图", style)],
        ],
        colWidths=[255, 255],
    )
    table.setStyle(
        TableStyle(
            [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]
        )
    )
    story.extend([Spacer(1, 8), table, Spacer(1, 8)])
    review = snapshot["review"]
    p(
        f"复核版本：{snapshot['review_revision']}　结论：{DECISIONS.get(review['decision'], review['decision']) if review else '尚未复核'}"
    )
    if review:
        p(f"复核人：{review['author']}　复核意见：{review['note']}")
        p(
            f"圈选区域：{len(review['annotations'])} 个；区域仅作调查注记，未修改原始预测。像素几何详见 metadata.json。"
        )
    p(
        "来源边界：448 幅测试样本曾用于项目探索；370 幅留出样本仍来自同一灾害事件，不代表跨事件泛化验证。"
    )
    p(
        f"结果 ID：{result['id']}\n输入 SHA256：{contract['input_sha256']}\n掩膜 SHA256：{contract['mask_sha256']}"
    )
    p(f"快照时间：{snapshot['snapshot_at']}　模板版本：{snapshot['template_version']}")

    def footer(canvas, document):
        canvas.setFont("NotoSC", 8)
        canvas.drawString(42, 23, "TerraScope · 可追溯调查记录 · 不替代现场通行核查")
        canvas.drawRightString(A4[0] - 42, 23, str(document.page))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()


def build_files(db, snapshot):
    pred = snapshot["prediction"]
    image = snapshot["image"]
    original = read_asset(db, image["display_asset_id"])
    overlay = read_asset(db, pred["overlay_asset_id"])
    files = {
        "report.pdf": pdf_report(snapshot, original, overlay),
        "mask.png": read_asset(db, pred["mask_asset_id"]),
        "overlay.png": overlay,
        "original.png": original,
        "metadata.json": json.dumps(
            snapshot, ensure_ascii=False, indent=2, allow_nan=False
        ).encode(),
    }
    if location := image.get("location"):
        geojson = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': image['id'],
            'geometry': {'type': 'Point', 'coordinates': [location['longitude'], location['latitude']]},
            'properties': {'sample_id': image.get('sample_id'), 'acquired_at': image.get('acquired_at'),
                           'prediction_id': pred['id'], **location}}]}
        files['location.geojson'] = json.dumps(geojson, ensure_ascii=False, indent=2).encode()
    source_image = db.get(ImageAsset, image["id"])
    source_bytes = read_asset(db, source_image.original_asset_id)
    source_name = "input.jpg" if source_bytes.startswith(b"\xff\xd8") else "input.png"
    files[source_name] = source_bytes
    if pred["difference_asset_id"]:
        files["difference.png"] = read_asset(db, pred["difference_asset_id"])
    csv_buffer = io.StringIO()
    row = {
        "sample_id": image.get("sample_id") or "",
        "split": image["split"],
        **pred["metrics"],
        "source_mode": pred["contract"]["source_mode"],
        "prediction_id": pred["id"],
        "review_revision": snapshot["review_revision"],
        "review_status": snapshot["review"]["decision"]
        if snapshot["review"]
        else "pending",
    }
    writer = csv.DictWriter(csv_buffer, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    files["statistics.csv"] = csv_buffer.getvalue().encode("utf-8-sig")
    files["README.txt"] = (
        "TerraScope 证据包\n坐标单位 pixel，原点左上角；像素中心为 (列+0.5, 行+0.5)。\n"
        "mask.png: 0=背景，255=预测受淹道路；overlay.png: 独立可视化，不能代替掩膜。\n"
        "difference.png（如有）: 绿=TP，红=FP，黄=FN，透明=其余或无效区。\n"
        "统计仅针对有效区；历史模型结果、人工复核和当前推理来源由 metadata.json 区分。\n"
        "location.geojson（如有）: WGS 84 相机拍摄点，经度在前、纬度在后，不表示影像范围。\n"
        "复核多边形只记录注记，不改变模型预测。此包为固定快照，后续复核不会改写本包。\n"
    ).encode()
    files["SHA256SUMS.txt"] = "".join(
        f"{sha256(content)}  {name}\n" for name, content in sorted(files.items())
    ).encode()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    files["evidence.zip"] = archive.getvalue()
    return files


def run_report(report_id):
    token = uid()
    with SessionLocal() as db:
        claim = db.execute(
            update(ReportSnapshot)
            .where(
                ReportSnapshot.id == report_id,
                ReportSnapshot.status.in_(["QUEUED", "RUNNING"]),
                ReportSnapshot.lease_until < time.time(),
            )
            .values(status="RUNNING", lease_token=token, lease_until=time.time() + 120)
        )
        db.commit()
        if not claim.rowcount:
            return
    try:
        with SessionLocal() as db:
            report = db.get(ReportSnapshot, report_id)
            files = build_files(db, report.snapshot)
            types = {
                "pdf": "application/pdf",
                "png": "image/png",
                "jpg": "image/jpeg",
                "json": "application/json",
                "geojson": "application/geo+json",
                "csv": "text/csv",
                "zip": "application/zip",
                "txt": "text/plain",
            }
            assets = {
                name: save_asset(
                    db, report.project_id, content, name, types[name.split(".")[-1]]
                ).id
                for name, content in files.items()
            }
            updated = db.execute(
                update(ReportSnapshot)
                .where(
                    ReportSnapshot.id == report_id,
                    ReportSnapshot.lease_token == token,
                    ReportSnapshot.status == "RUNNING",
                )
                .values(status="SUCCEEDED", files=assets, lease_until=0)
            )
            if updated.rowcount:
                db.commit()
            else:
                db.rollback()
    except Exception:
        log.exception("Report failed: %s", report_id)
        with SessionLocal() as db:
            db.execute(
                update(ReportSnapshot)
                .where(
                    ReportSnapshot.id == report_id, ReportSnapshot.lease_token == token
                )
                .values(
                    status="FAILED",
                    error="报告生成失败，请根据报告 ID 检查服务日志",
                    lease_until=0,
                )
            )
            db.commit()


def pending_report_ids():
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(ReportSnapshot.id)
                .where(
                    ReportSnapshot.status.in_(["QUEUED", "RUNNING"]),
                    ReportSnapshot.lease_until < time.time(),
                )
                .order_by(ReportSnapshot.created_at)
                .limit(20)
            )
        )
