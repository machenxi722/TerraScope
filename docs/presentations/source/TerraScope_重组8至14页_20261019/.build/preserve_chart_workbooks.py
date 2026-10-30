"""Restore unchanged source chart XML and workbook dependencies after import/export.

The Artifact Tool-authored slide frames and all authored content remain intact.
The charts were only repositioned, so retaining their original parts preserves
native Excel editability and the exact source values/formulas/styles.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import posixpath
import io
import re

D=Path(__file__).parent
with ZipFile(D/'candidate.pptx') as z:
    parts={n:z.read(n) for n in z.namelist()}
with ZipFile('/Users/chenxi/Desktop/TerraScope_课堂汇报.pptx') as source:
    for i in (1,2,3):
        src=f'ppt/charts/chart{i}.xml'
        dst=f'ppt/slides/charts/chart{i}.xml'
        parts[dst]=source.read(src)
        sr=f'ppt/charts/_rels/chart{i}.xml.rels'
        dr=f'ppt/slides/charts/_rels/chart{i}.xml.rels'
        parts[dr]=source.read(sr)
        for rel in E.fromstring(parts[dr]):
            if rel.get('TargetMode')=='External':
                continue
            target=rel.get('Target')
            workbook=source.read(posixpath.normpath(posixpath.dirname(src)+'/'+target))
            parts[posixpath.normpath(posixpath.dirname(dst)+'/'+target)]=workbook
            # The source chart caches use expanded float strings (e.g.
            # 8.6566320000000001) while the source workbook uses 8.656632.
            # Refresh cache serialization from the same workbook cells. The
            # workbook bytes, source formulas, and displayed values stay intact.
            with ZipFile(io.BytesIO(workbook)) as wz:
                sheet=E.fromstring(wz.read('xl/worksheets/sheet1.xml'))
                vals={c.get('r'):c.xpath('./*[local-name()="v"]/text()')[0] for c in sheet.xpath('//*[local-name()="c"]') if c.xpath('./*[local-name()="v"]/text()')}
            chart=E.fromstring(parts[dst])
            for ref in chart.xpath('//*[local-name()="numRef"]'):
                formula=ref.xpath('./*[local-name()="f"]/text()')[0]
                match=re.search(r'!\$([A-Z]+)\$(\d+):\$[A-Z]+\$(\d+)$',formula)
                if match:
                    col,start,end=match.groups()
                    for point in ref.xpath('./*[local-name()="numCache"]/*[local-name()="pt"]'):
                        cell=col+str(int(start)+int(point.get('idx')))
                        point.xpath('./*[local-name()="v"]')[0].text=vals[cell]
            parts[dst]=E.tostring(chart,xml_declaration=True,encoding='UTF-8',standalone=True)
ct=E.fromstring(parts['[Content_Types].xml'])
ns='http://schemas.openxmlformats.org/package/2006/content-types'
if not any(x.get('Extension')=='xlsx' for x in ct):
    E.SubElement(ct,'{'+ns+'}Default',Extension='xlsx',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
parts['[Content_Types].xml']=E.tostring(ct,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(D/'candidate_preserved.pptx','w',ZIP_DEFLATED) as z:
    for n,v in parts.items():z.writestr(n,v)
print('Preserved 3 original native charts and their embedded workbooks.')
