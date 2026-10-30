from pathlib import Path
import json, numpy as np
from PIL import Image, ImageFilter, ImageDraw

R=Path.cwd(); W=R/'work/final_talk_20261016'; A=W/'assets'; A.mkdir(exist_ok=True)
T=R/'work/night_20261016/tta_backup/results'
F=R/'work/finetune_backups_20261015/formal/results'
COL={'pred':(82,151,184),'gt':(76,155,125),'fp':(198,112,134),'fn':(225,182,89)}
meta={}; audits=[]
def overlay(rgb,mask,color,alpha=.48):
    a=np.array(rgb).copy(); a[mask]=a[mask]*(1-alpha)+np.array(color)*alpha
    contour=mask & ~np.array(Image.fromarray(mask).filter(ImageFilter.MinFilter(3)))
    a[contour]=color
    return Image.fromarray(a)
for sid in ['7301','7595','7986','7461','6598','6345','7679','6480','7558']:
    d=R/'work/finetune_formal_20261015/data'/sid
    split='test'
    if sid in ['6598','6345']:split='val'
    if not d.exists():d=R/'work/night_20261016/holdout/data'/sid;split='holdout'
    rgb=Image.open(d/'RGB.jpg').convert('RGB'); lab=np.array(Image.open(d/'labels.png'));gt=lab==3;valid=lab!=255
    rgb.save(A/f'{sid}_rgb.png');overlay(rgb,gt,COL['gt']).save(A/f'{sid}_gt.png')
    Image.fromarray(gt.astype('uint8')*255).save(A/f'{sid}_mask_gt.png')
    mm={'split':split,'size':list(rgb.size)}
    for mode in ['single_view','tta4','baseline']:
        p= (F/'predictions/baseline'/split/f'{sid}.png') if mode=='baseline' else (T/'predictions'/mode/split/f'{sid}.png')
        if not p.exists():continue
        pred=np.array(Image.open(p))>0
        assert pred.shape==lab.shape==(rgb.height,rgb.width)
        overlay(rgb,pred,COL['pred']).save(A/f'{sid}_{mode}.png')
        Image.fromarray(pred.astype('uint8')*255).save(A/f'{sid}_{mode}_mask.png')
        tp=int((pred&gt&valid).sum());fp=int((pred&~gt&valid).sum());fn=int((~pred&gt&valid).sum())
        actual={'iou':tp/(tp+fp+fn) if tp+fp+fn else None,'coverage':float((pred&valid).sum()/valid.sum()*100),'reference':float((gt&valid).sum()/valid.sum()*100)}
        src=json.load(open((F/'baseline_test.json') if mode=='baseline' and split=='test' else (F/'baseline_val.json') if mode=='baseline' else T/f'{mode}_{split}.json'))
        row=next(x for x in src['per_image'] if x['id']==sid)
        assert (tp,fp,fn)==(row['tp'],row['fp'],row['fn']),(sid,mode)
        audits.append({'id':sid,'mode':mode,'aligned':True,'counts_match_saved_json':True})
        mm[mode]=actual
        if mode=='tta4':
            a=np.array(rgb)*.45+255*.55
            for mask,col in [(pred&gt,COL['gt']),(pred&~gt,COL['fp']),(~pred&gt,COL['fn'])]:a[mask]=col
            Image.fromarray(a.astype('uint8')).save(A/f'{sid}_difference.png')
    meta[sid]=mm
    if sid=='7301':
        crop=(60,100,655,590)
        for k in ['rgb','tta4','gt','difference']:
            im=Image.open(A/f'{sid}_{k}.png');im.crop(crop).save(A/f'{sid}_zoom_{k}.png')
        im=Image.open(A/f'{sid}_tta4.png');dr=ImageDraw.Draw(im);dr.rectangle(crop,outline=(255,241,199),width=6);im.save(A/f'{sid}_boxed.png')
for sid in ['6598']:
    rgb=Image.open(A/f'{sid}_rgb.png');z=np.load(T/f'diagnostic_logits/{sid}.npz')['aligned_logits'][:,0,0]
    for i,axes in enumerate([(),(1,),(0,),(0,1)]):
        x=np.array(rgb);x=np.flip(x,axes) if axes else x
        Image.fromarray(x).save(A/f'tta_input_{i}.png')
        pr=1/(1+np.exp(-np.clip(z[i],-20,20)));col=np.array([64,129,159]);a=255*(1-pr[...,None])+col*pr[...,None]
        Image.fromarray(a.astype('uint8')).resize((256,256)).save(A/f'tta_aligned_{i}.png')
sel=json.load(open(R/'outputs/TerraScope_夜间优化_20261016/最终方案选择.json'))
night=json.load(open(R/'work/night_20261016/backup/results/report.json'))
old=json.load(open(R/'work/finetune_ppt_20261015/assets/metrics.json'))
(A/'data.json').write_text(json.dumps({'cases':meta,'selected':sel,'night':night,'old':old},ensure_ascii=False,indent=2))
(W/'asset_alignment_audit.json').write_text(json.dumps(audits,indent=2))
print('Assets:',len(list(A.glob('*.png'))),'audited',len(audits),'actual-mask/label pairs')
print(json.dumps(meta['7301'],ensure_ascii=False))
