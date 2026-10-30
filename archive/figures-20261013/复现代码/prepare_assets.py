from pathlib import Path
import json,shutil
import numpy as np,rasterio
from PIL import Image
from scipy.ndimage import binary_erosion
ROOT=Path.cwd();OUT=ROOT/'outputs/TerraScope_全部图件_清新论文版/本地素材';OUT.mkdir(exist_ok=True)
REV=json.loads((ROOT/'outputs/TerraScope_洪灾水体/confirmation_review_simulation.json').read_text())
def overlay(rgb,m,col,alpha=.65):
 out=rgb.copy();out[m]=(rgb[m]*(1-alpha)+np.array(col)*alpha).astype('uint8');return out
for id in ['India_747992','Ghana_406026']:
 rgb=np.array(Image.open(ROOT/'work/flood_water/confirmation'/id/'rgb.png'))
 Image.fromarray(rgb).save(OUT/(id+'_rgb.png'))
 for var,col in [('p1',[80,124,145]),('p2',[166,124,63])]:
  m=np.array(Image.open(ROOT/'outputs/TerraScope_洪灾水体/results_confirmation'/id/var/'mask.png'))>0
  if id=='India_747992':
   with rasterio.open(ROOT/'work/flood_water/raw'/(id+'_JRCWaterHand.tif')) as d:j=d.read(1)>0
   with rasterio.open(ROOT/'work/flood_water/raw'/(id+'_LabelHand.tif')) as d:v=d.read(1)>=0
   m=m&~j&v
  im=overlay(rgb,m,col)
  Image.fromarray(im).save(OUT/(id+'_'+var+'_overlay.png'))
  Image.fromarray(np.where(m[...,None],np.array(col),np.array([238,244,246])).astype('uint8')).save(OUT/(id+'_'+var+'_mask.png'))
 with rasterio.open(ROOT/'work/flood_water/raw'/(id+'_LabelHand.tif')) as f:g=f.read(1)
 reference=(g==1)&~j if id=='India_747992' else g==1
 Image.fromarray(overlay(rgb,reference,[84,124,101])).save(OUT/(id+'_reference.png'))
order=sorted(REV['rows'],key=lambda r:r['p'][0],reverse=True)
for r in order[:3]:
 shutil.copy2(ROOT/'work/flood_water/confirmation'/r['id']/'rgb.png',OUT/(r['id']+'_rank.png'))
sel=json.loads((ROOT/'work/floodnet/selection.json').read_text());s=next(x for x in sel if x['id']=='7571')
rgb=np.array(Image.open(ROOT/'work/floodnet/inputs'/s['split']/'7571/rgb.png'))
water=np.array(Image.open(ROOT/('work/floodnet/results_simple_'+s['split'])/'7571/water/mask.png'))>0
gt=np.array(Image.open(ROOT/'work/floodnet/raw/7571_lab.png').resize((rgb.shape[1],rgb.shape[0]),Image.Resampling.NEAREST));road=np.isin(gt,[3,4])
im=overlay(rgb,water,[80,124,145],.45);im=overlay(im,water&road,[122,104,155],.75);im[road&~binary_erosion(road,iterations=2)]=255
Image.fromarray(rgb).save(OUT/'FloodNet_7571_rgb.png');Image.fromarray(im).save(OUT/'FloodNet_7571_road_water.png')
(OUT/'流程图数据.json').write_text(json.dumps({'ranking':order[:3],'example':next(r for r in REV['rows'] if r['id']=='India_747992')},ensure_ascii=False,indent=2))
