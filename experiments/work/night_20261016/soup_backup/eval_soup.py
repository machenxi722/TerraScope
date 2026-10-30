"""Frozen-protocol FloodNet supervised adaptation experiment (2026-10-15).
Fixed SEG prefix; RGB-only input; GT used only by loss/evaluation; original
checkpoints remain read-only. Test metrics never select a checkpoint.
"""
import os,json,time,random,math,hashlib,ast,importlib,traceback,zipfile,signal
from pathlib import Path
from collections import OrderedDict
import numpy as np
from PIL import Image,ImageEnhance
import torch
from torch import nn
import torch.nn.functional as F
from transformers import AutoModel,AutoTokenizer

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
CONFIG=json.loads((ROOT/'protocol.json').read_text())
MANIFEST=json.loads((ROOT/'manifest.json').read_text())
torch.set_num_threads(8)
REPORT={'protocol':CONFIG,'completed':False,'arms':{},'started':time.strftime('%Y-%m-%d %H:%M:%S'),'gpu':torch.cuda.get_device_name(0),'torch':torch.__version__}
START=time.monotonic()
def log(s):print(time.strftime('%H:%M:%S'),s,flush=True)
def save():
 REPORT['elapsed_seconds']=time.monotonic()-START
 tmp=OUT/'report.tmp';tmp.write_text(json.dumps(REPORT,indent=2));tmp.replace(OUT/'report.json')
def guard():
 if time.time()>CONFIG['deadline_epoch'] or time.monotonic()-START>CONFIG['maximum_run_seconds']:raise TimeoutError('Formal experiment wall time cap reached')
def sync():torch.cuda.synchronize()
def amp():return torch.autocast('cuda',dtype=torch.bfloat16)
def seeded(seed):random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)

class LoRALinear(nn.Module):
 def __init__(self,base,r=8,alpha=16):
  super().__init__();self.base=base;self.scale=alpha/r;self.enabled=True
  self.lora_A=nn.Parameter(torch.empty(r,base.in_features,device=base.weight.device,dtype=torch.float32))
  self.lora_B=nn.Parameter(torch.zeros(base.out_features,r,device=base.weight.device,dtype=torch.float32))
  self.reset()
 def reset(self):nn.init.kaiming_uniform_(self.lora_A,a=math.sqrt(5));nn.init.zeros_(self.lora_B)
 def forward(self,x):
  y=self.base(x)
  return y+F.linear(F.linear(x,self.lora_A),self.lora_B)*self.scale if self.enabled else y

try:
 # Assert the frozen manifest and all supplied inputs before loading any model.
 assert hashlib.sha256((ROOT/'manifest.json').read_bytes()).hexdigest()==CONFIG['manifest_sha256']
 sets={s:{r['id']for r in MANIFEST if r['split']==s}for s in ['train','val','test']}
 assert all(not sets[a]&sets[b]for a,b in [('train','val'),('train','test'),('val','test')])
 for r in MANIFEST:
  for field,f in [('rgb_sha256','RGB.jpg'),('label_sha256','labels.png')]:
   assert hashlib.sha256((ROOT/'data'/r['id']/f).read_bytes()).hexdigest()==r[field]
 path='/root/autodl-tmp/terrascope/models/TerraScope'
 log('Verified data hashes; loading untouched base checkpoint')
 tokenizer=AutoTokenizer.from_pretrained(path,trust_remote_code=True)
 model=AutoModel.from_pretrained(path,trust_remote_code=True,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True).cuda().eval()
 model.preparing_for_generation(tokenizer);model.requires_grad_(False)
 sam=model.grounding_encoder.sam2_model;decoder=sam.sam_mask_decoder;projection=model.text_hidden_fcs;lm=model.language_model.model
 decoder.dynamic_multimask_via_stability=False
 decoder.float();projection.float()
 baseline={'decoder':{k:v.detach().cpu().clone()for k,v in decoder.state_dict().items()},'projection':{k:v.detach().cpu().clone()for k,v in projection.state_dict().items()}}
 module=importlib.import_module(type(model).__module__)
 adapters=[]
 for name,mod in list(lm.named_modules()):
  if isinstance(mod,nn.Linear)and name.split('.')[-1]in ['q_proj','v_proj']:
   par,leaf=name.rsplit('.',1);adapter=LoRALinear(mod);setattr(lm.get_submodule(par),leaf,adapter);adapters.append(adapter)
 for a in adapters:a.enabled=False;a.requires_grad_(False)
 lm.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
 image_cache=OrderedDict();eval_cache=OrderedDict()
 def read(r):
  sid=r['id']
  if sid not in image_cache:
   im=Image.open(ROOT/'data'/sid/'RGB.jpg').convert('RGB');la=Image.open(ROOT/'data'/sid/'labels.png').copy();assert im.size==la.size
   image_cache[sid]=(im,la)
   if len(image_cache)>900:image_cache.popitem(last=False)
  return image_cache[sid]
 def prepare(r,augment=False):
  im,lab=read(r)
  if augment:
   if random.random()<.5:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT);lab=lab.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
   if random.random()<.5:im=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM);lab=lab.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
   im=ImageEnhance.Brightness(im).enhance(random.uniform(.9,1.1));im=ImageEnhance.Contrast(im).enhance(random.uniform(.9,1.1))
  g=model.extra_image_processor.apply_image(np.array(im));g=torch.from_numpy(g).permute(2,0,1).contiguous().cuda().to(torch.bfloat16);g=model.grounding_encoder.preprocess_image(g)[None]
  images=module.dynamic_preprocess(im,1,4,448,True);pv=torch.stack([model.transformer(i)for i in images]).cuda().to(torch.bfloat16)
  toks='<img>'+'<IMG_CONTEXT>'*(len(images)*model.patch_token)+'</img>'
  prompt=model.template['INSTRUCTION'].format(input=toks+'\nSegment the flooded roads in this aerial image.',round=1,bot_name='BOT')+'The flooded road regions are [SEG]'
  ids=torch.tensor(tokenizer.encode(prompt),device='cuda')[None];assert ids[0,-1].item()==tokenizer.convert_tokens_to_ids('[SEG]')
  with torch.no_grad(),amp():
   raw=sam.image_encoder(g)['backbone_fpn'][-sam.num_feature_levels:]
   vf=model.extract_feature(pv)
   embeds=model.build_inputs_embeds_for_prefill(ids,vf.reshape(-1,vf.shape[-1]),tokenizer.convert_tokens_to_ids('<IMG_CONTEXT>'))
  la=np.array(lab);target=torch.from_numpy((la==3).astype('float32')).cuda()[None,None];valid=torch.from_numpy((la!=255).astype('float32')).cuda()[None,None]
  return {'raw':raw,'embeds':embeds.detach(),'target':target,'valid':valid,
   'y':F.interpolate(target,(256,256),mode='nearest'),'v':F.interpolate(valid,(256,256),mode='nearest')}
 def fwd(c,lora):
  e=c['embeds'].detach().requires_grad_(lora and torch.is_grad_enabled())
  with torch.set_grad_enabled(lora and torch.is_grad_enabled()):
   h=lm(inputs_embeds=e,attention_mask=torch.ones(e.shape[:2],device='cuda',dtype=torch.long),use_cache=False,return_dict=True).last_hidden_state[:,-1]
  hi=[decoder.conv_s0(c['raw'][0]),decoder.conv_s1(c['raw'][1])]
  return sam._forward_sam_heads(c['raw'][-1]+sam.no_mem_embed.reshape(1,-1,1,1),high_res_features=hi,multimask_output=False,language_embd=projection(h).unsqueeze(1))[3]
 def loss_fn(out,c):
  p=out.float();y=c['y'];v=c['v'];prob=p.sigmoid()*v
  return (F.binary_cross_entropy_with_logits(p,y,reduction='none')*v).sum()/v.sum().clamp_min(1)+1-(2*(prob*y).sum()+1)/(prob.sum()+(y*v).sum()+1)
 def summarize(rows):
  tp=sum(r['tp']for r in rows);fp=sum(r['fp']for r in rows);fn=sum(r['fn']for r in rows)
  pos=[r for r in rows if r['gt_pixels']>0];neg=[r for r in rows if r['gt_pixels']==0]
  return {'n':len(rows),'n_positive':len(pos),'global_iou':tp/max(1,tp+fp+fn),'global_dice':2*tp/max(1,2*tp+fp+fn),
   'positive_macro_iou':float(np.mean([r['iou']for r in pos])),'coverage_mae_pp':float(np.mean([r['coverage_error_pp']for r in rows])),
   'negative_false_positive_fraction':float(np.mean([r['pred_pixels']/r['valid_pixels']for r in neg])),
   'scene_tp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in pos),'scene_fn':sum(r['pred_pixels']/r['valid_pixels']<.01 for r in pos),
   'scene_fp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in neg),'scene_tn':sum(r['pred_pixels']/r['valid_pixels']<.01 for r in neg),
   'mean_loss':float(np.mean([r['loss']for r in rows]))}
 @torch.no_grad()
 def evaluate(name,split,lora,save_masks=False):
  lm.eval();decoder.eval();projection.eval();rows=[];start=time.monotonic()
  dest=OUT/'predictions'/name/split
  if save_masks:dest.mkdir(parents=True,exist_ok=True)
  for r in MANIFEST:
   if r['split']!=split:continue
   guard();c=prepare(r)
   with amp():out=fwd(c,lora)
   pred=F.interpolate(out.float(),c['target'].shape[-2:],mode='bilinear',align_corners=False)>0;gt=c['target']>0;v=c['valid']>0
   tp=int((pred&gt&v).sum());fp=int((pred&~gt&v).sum());fn=int((~pred&gt&v).sum());n=int(v.sum());pp=int((pred&v).sum());gg=int((gt&v).sum())
   rows.append({'id':r['id'],'tp':tp,'fp':fp,'fn':fn,'valid_pixels':n,'pred_pixels':pp,'gt_pixels':gg,'iou':tp/(tp+fp+fn)if tp+fp+fn else None,'coverage_error_pp':abs(pp-gg)/n*100,'loss':float(loss_fn(out,c))})
   if save_masks:Image.fromarray(pred[0,0].cpu().numpy().astype('uint8')*255).save(dest/f'{r["id"]}.png')
   if len(rows)%100==0:log(f'EVAL_PROGRESS {name} {split} {len(rows)}')
  result={'summary':summarize(rows),'per_image':rows,'seconds':time.monotonic()-start}
  (OUT/f'{name}_{split}.json').write_text(json.dumps(result,indent=2));log(f'EVAL {name} {split} {json.dumps(result["summary"])}');return result['summary']
 def state():return {n:p.detach().cpu().clone()for n,p in model.named_parameters()if p.requires_grad}
 base=ROOT.parent
 night=json.loads((base/'night_20261016/results/report.json').read_text())
 extra=json.loads((base/'night_holdout_20261016/results/report.json').read_text())
 tta=json.loads((base/'night_tta_20261016/results/report.json').read_text())
 assert night['completed'] and extra['completed'] and tta['completed']
 single=max(night['arms'],key=lambda n:night['arms'][n]['best_val_global_iou'])
 single_val=night['arms'][single]['best_val_global_iou']
 decoder_name=next(n for n,m in model.named_modules()if m is decoder)
 projection_name=next(n for n,m in model.named_modules()if m is projection)
 expected={n for n,p in model.named_parameters()if n.startswith(decoder_name+'.')or n.startswith(projection_name+'.')}
 model.requires_grad_(False);model.eval()
 for adapter in adapters:adapter.enabled=False
 def load_state(weights):
  assert set(weights)==expected
  missing,unexpected=model.load_state_dict(weights,strict=False);assert not unexpected
 def read_delta(name):
  path=base/'night_20261016/results'/f'{name}_best_delta.pt'
  d=torch.load(path,map_location='cpu',weights_only=True);assert set(d)==expected
  return d
 # Reproduce the original pipeline on one positive and one negative validation image.
 load_state(read_delta(single));preflight=[]
 with torch.no_grad():
  for sid in ['6598','6345']:
   row=next(r for r in MANIFEST if r['id']==sid);assert row['split']=='val'
   c=prepare(row)
   with amp():logits=fwd(c,False)
   mask=(F.interpolate(logits.float(),c['target'].shape[-2:],mode='bilinear',align_corners=False)>0)[0,0].cpu().numpy()
   reference=np.array(Image.open(base/'night_tta_20261016/results/predictions/single_view/val'/f'{sid}.png'))>0
   assert reference.shape==mask.shape
   disagreement=float(np.mean(reference!=mask));assert disagreement<=1e-4
   preflight.append({'id':sid,'mask_disagreement_fraction':disagreement})
 REPORT.update(single_checkpoint_name=single,single_validation_iou=single_val,preflight=preflight,candidates={})
 groups={kind:[n for n,a in night['arms'].items()if a['kind']==kind]for kind in ['long_bce_dice','long_bce_lovasz']}
 assert all(len(names)==3 for names in groups.values())
 groups['all_six']=list(night['arms']);assert len(groups['all_six'])==6
 REPORT['groups_locked_before_evaluation']=groups;save()
 best=-1;chosen=None
 for label,names in groups.items():
  guard();average=None;sources=[]
  for i,name in enumerate(names):
   weights=read_delta(name)
   if average is None:average={key:value.float().clone()for key,value in weights.items()}
   else:
    for key in average:
     assert average[key].shape==weights[key].shape
     average[key].add_((weights[key].float()-average[key])/(i+1))
   path=base/'night_20261016/results'/f'{name}_best_delta.pt'
   sources.append({'name':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
   del weights
  load_state(average)
  metrics=evaluate(label,'val',False,True)
  REPORT['candidates'][label]={'members':sources,'validation':metrics,'uniform_weight':1/len(names)}
  if metrics['global_iou']>best:
   best=metrics['global_iou'];chosen=label;torch.save(average,OUT/'best_soup_weights.pt')
  save();log('SOUP_VALIDATION_COMPLETE '+label);del average
 REPORT['selected_soup_by_validation']=chosen
 REPORT['deployment_choice_by_validation']='soup'if best>single_val else 'single_checkpoint'
 REPORT['validation_choice_locked_at']=time.strftime('%Y-%m-%d %H:%M:%S');save()
 load_state(torch.load(OUT/'best_soup_weights.pt',map_location='cpu',weights_only=True))
 REPORT['soup_test']=evaluate('selected_soup','test',False,True);save()
 REPORT['soup_holdout']=evaluate('selected_soup','holdout',False,True);save()
 REPORT['completed']=True
except BaseException as exc:
 REPORT['error']=repr(exc);REPORT['traceback']=traceback.format_exc();traceback.print_exc()
finally:
 save();log('SOUP_FINISHED '+str(REPORT['completed']))
