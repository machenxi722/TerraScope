from pathlib import Path
import re,json,shutil

R=Path.cwd(); W=R/'work/palette_refresh_20261016'
# Roles stay consistent across diagrams, charts, navigation and tables.
groups={
'203653':['233C48','203E4D','263F48','213B38','22282C','253C36'],
'294F82':['00552B','235C49','335B4A'],
'DCE5F4':['DCECF5','E2EEF5','E7F0F6','D7ECF1'],
'2F5597':['427C9C','4C7FA1','4F80A0','477D99','467F95','426B80'],
'B7C9E8':['A8CADA','ACCBDC','B4D1E1','B4CCD9','B9DCEB','CCE1EC','C2DCE9'],
'F3CFCC':['F1D4D8','F6E1DF','F8E6E9','FCEDF0','F7DDE3','F3D8DF','DDB0B8','DEB0B5','DDB7BE','E7C9D4'],
'B9534F':['B56D7D','B7776C','BA7181','B87A89','C598A3','BF675D','C7897D','A25C69','C56B70'],
'E3A6A1':['E8B2BD','E2B3BE','E3B3BD','E2BD9B'],
'DFEBCF':['DDEBDA','E5F0E7','EAF2E8','DBEAD8','DEEBD9','CDE1CC','E3EEE5','DCE9DE'],
'68874F':['54856B','5B8B74','5B8D70','4D846B','4D8066','477566','4C9B7D'],
'B4CFA0':['B8D5B0','A8CFC1','C4DACA'],
'F6E8B8':['F7E6C6','F8E9D5','F8EBD7','F6E5C3','F5E5B5','F4DCAA','F4DCAA'],
'B88C32':['BA7B48','BE8051','BC7D44','B77A46','C9A394'],
'E7C66F':['EBCB8B','F7DEAF','F4DCAA'],
'E4DEEC':['E7E0F2','ECE6F3','EAE3F2','E7DFF0','D4CDEE','DCD5EC'],
'846C9B':['8971A8','947CB0','8A72A4','8872A3'],
'C4B4D6':['C6B5DD','C9C3DA'],
'667485':['647B73','6B7D84','6F7E7C','61746C','687477'],
'B3C0CD':['93A49D','BDCBD1','BDC9C7','94A99F','83969D','B6C4BE'],
'DEE5EC':['DCE6E0','DDE6E1','E0E8EB','D5E1DB'],
'F9F5E9':['FBF5F0','F7F0E5','F8F4ED'],
'F9E7DF':['F8E4DF','F9ECE7'],
}
colors={x:y for y,xs in groups.items() for x in xs}
(W/'palette.json').write_text(json.dumps(colors,indent=2))
def recolor(t):
 return re.sub(r'#[0-9a-fA-F]{6}',lambda m:'#'+colors.get(m[0][1:].upper(),m[0][1:]),t)
helper=(R/'work/editorial_v2_20261016/method_art.mjs').read_text()
helper=helper.replace("'../alignment_revision/diagram_utils.mjs'","'../alignment_revision/diagram_utils.mjs'")
(W/'styled_art.mjs').write_text(recolor(helper))
configs=[('principle','reference_aligned_20261016'),('workflow','workflow_reference_20261016'),('training','finetune_structure_20261016')]
for name,src in configs:
 d=W/'figures'/name;d.mkdir(exist_ok=True)
 text=(R/'work'/src/'build.mjs').read_text()
 text=text.replace(f"work/{src}",f"work/palette_refresh_20261016/figures/{name}")
 text=text.replace("import {art,mix} from '../editorial_v2_20261016/method_art.mjs';", "import {art as baseArt,mix} from './styled_art.mjs';\nimport {figureArt} from './figure_style.mjs';\nconst art=s=>figureArt(baseArt(s));")
 text=recolor(text)
 text=text.replace("'本地样本 7571'","'TerraScope 原模型'")
 # Each diagram remains a native slide for later insertion into the deck.
 (W/f'{name}.mjs').write_text(text)
 if name=='principle':shutil.copyfile(R/'work/reference_aligned_20261016/water_overlay.png',d/'water_overlay.png')
print('Prepared three native figure sources with one palette.')
