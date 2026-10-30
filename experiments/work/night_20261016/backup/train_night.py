"""Frozen-protocol FloodNet supervised adaptation experiment (2026-10-15).
Fixed SEG prefix; RGB-only input; GT used only by loss/evaluation; original
checkpoints remain read-only. Test metrics never select a checkpoint.
"""
import os,json,time,random,math,hashlib,ast,importlib,traceback,zipfile,signal
from datetime import datetime, timezone
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
 # Binary Lovasz hinge: sorted margin errors weighted by discrete Jaccard increments.
 # Formula: Berman et al., CVPR 2018. Independently expressed in this implementation.
 def lovasz_hinge(logits,labels,valid):
  keep=valid.reshape(-1)>0
  scores=logits.float().reshape(-1)[keep];truth=labels.float().reshape(-1)[keep]
  if scores.numel()==0:return logits.sum()*0
  margins=1-scores*(2*truth-1)
  ordered,indices=torch.sort(margins,descending=True,stable=True)
  ranked=truth[indices];positives=ranked.sum()
  overlap=positives-ranked.cumsum(0)
  union=positives+(1-ranked).cumsum(0)
  jaccard=1-overlap/union.clamp_min(1)
  weights=torch.cat((jaccard[:1],jaccard[1:]-jaccard[:-1]))
  return (ordered.relu()*weights).sum()
 def objective(out,c,kind):
  if kind=='long_bce_dice':return loss_fn(out,c)
  valid=c['v'];bce=(F.binary_cross_entropy_with_logits(out.float(),c['y'],reduction='none')*valid).sum()/valid.sum().clamp_min(1)
  return bce+lovasz_hinge(out,c['y'],valid)
 # Functional edge cases before any training update.
 for truth in [torch.zeros(4),torch.ones(4),torch.tensor([0.,1.,0.,1.])]:
  perfect=(truth*2-1)*2
  assert lovasz_hinge(perfect,truth,torch.ones(4)).item()==0
  wrong=(-perfect).requires_grad_();loss=lovasz_hinge(wrong,truth,torch.ones(4));loss.backward()
  assert abs(loss.item()-3)<1e-6 and torch.isfinite(wrong.grad).all()
 z=torch.randn(4,requires_grad=True);empty=lovasz_hinge(z,torch.ones(4),torch.zeros(4));empty.backward();assert z.grad.abs().sum()==0
 REPORT['loss_tests']='perfect, opposite, all-negative, all-positive, all-ignore and gradients passed';save()
 # Reproduce two existing validation masks before changing any weights.
 preflight=[]
 with torch.no_grad():
  for positive in [True,False]:
   row=next(r for r in MANIFEST if r['split']=='val'and bool(r['positive'])==positive)
   c=prepare(row)
   with amp():out=fwd(c,False)
   mask=(F.interpolate(out.float(),c['target'].shape[-2:],mode='bilinear',align_corners=False)>0)[0,0].cpu().numpy()
   old=Path('/root/autodl-tmp/terrascope/finetune_formal_20261015/results/predictions/baseline/val')/(row['id']+'.png')
   reference=np.array(Image.open(old))>0
   assert reference.shape==mask.shape
   disagreement=float(np.mean(reference!=mask))
   assert disagreement<=.0001,(row['id'],disagreement)
   preflight.append({'id':row['id'],'positive':positive,'mask_disagreement_fraction':disagreement})
 REPORT['preflight_baseline_mask_reproduction']=preflight;save();log('PREFLIGHT '+json.dumps(preflight))
 def load_delta(path):
  saved=torch.load(path,map_location='cpu',weights_only=True)
  missing,unexpected=model.load_state_dict(saved,strict=False)
  assert not unexpected
  assert set(saved)=={n for n,p in model.named_parameters()if p.requires_grad}
 def train_arm(kind,seed):
  name=kind+'_seed'+str(seed)
  seeded(seed);model.requires_grad_(False);decoder.load_state_dict(baseline['decoder']);projection.load_state_dict(baseline['projection'])
  decoder.requires_grad_(True);projection.requires_grad_(True)
  for a in adapters:a.enabled=False;a.reset();a.requires_grad_(False)
  params=[p for p in model.parameters()if p.requires_grad]
  opt=torch.optim.AdamW(params,lr=CONFIG['head_lr'],weight_decay=.01)
  steps=CONFIG['micro_steps'];accum=CONFIG['gradient_accumulation']
  pos=[r for r in MANIFEST if r['split']=='train'and r['positive']];neg=[r for r in MANIFEST if r['split']=='train'and not r['positive']]
  best=-1;trace=[];history=[];average=None;average_n=0;best_step=None
  opt.zero_grad(set_to_none=True);sync();torch.cuda.reset_peak_memory_stats();t0=time.monotonic()
  log('ARM_START '+name)
  for i in range(steps):
   guard();lm.eval();decoder.train();projection.train()
   t=time.perf_counter();r=random.choice(pos if i%2==0 else neg);c=prepare(r,True)
   with amp():out=fwd(c,False);loss=objective(out,c,kind)
   if not torch.isfinite(loss):raise FloatingPointError('Nonfinite training loss')
   (loss/accum).backward();norm=None
   if(i+1)%accum==0:
    update=(i+1)//accum;total=steps//accum;warm=CONFIG['warmup_updates']
    scale=min(1,update/warm)if update<=warm else .1+.9*(1+math.cos(math.pi*(update-warm)/(total-warm)))/2
    for group in opt.param_groups:group['lr']=CONFIG['head_lr']*scale
    norm=float(torch.nn.utils.clip_grad_norm_(params,1));assert math.isfinite(norm)
    opt.step();opt.zero_grad(set_to_none=True)
   sync();trace.append({'micro_step':i+1,'sample_id':r['id'],'loss':float(loss.detach()),'seconds':time.perf_counter()-t,'gradient_norm':norm})
   if(i+1)%100==0:log(f'TRAIN {name} {i+1}/{steps} loss={np.mean([x["loss"]for x in trace[-100:]]):.4f} sec={np.mean([x["seconds"]for x in trace[-100:]]):.3f}')
   if(i+1)%CONFIG['validate_every']==0:
    current=state()
    if i+1>=3200:
     average_n+=1
     if average is None:average={k:v.clone()for k,v in current.items()}
     else:
      for k in average:average[k].add_((current[k]-average[k])/average_n)
    metrics=evaluate(name+f'_step{i+1}','val',False)
    history.append({'micro_step':i+1,**metrics})
    if metrics['global_iou']>best:
     best=metrics['global_iou'];best_step=i+1;torch.save(current,OUT/f'{name}_best_delta.pt')
    (OUT/f'{name}_training.json').write_text(json.dumps({'trace':trace,'validation':history,'best_step':best_step},indent=2))
  elapsed=time.monotonic()-t0;peak=torch.cuda.max_memory_allocated()/2**30
  assert average_n==3
  model.load_state_dict(average,strict=False)
  averaged_metrics=evaluate(name+'_late_average','val',False)
  selected='single_checkpoint'
  if averaged_metrics['global_iou']>best:
   best=averaged_metrics['global_iou'];selected='late_weight_average';torch.save(average,OUT/f'{name}_best_delta.pt')
  REPORT['arms'][name]={'seed':seed,'kind':kind,'trainable_parameters':sum(p.numel()for p in params),'micro_steps':steps,'optimizer_updates':steps//accum,'best_single_micro_step':best_step,'selected':selected,'best_val_global_iou':best,'late_average_val':averaged_metrics,'train_and_validation_seconds':elapsed,'peak_gpu_allocated_gib':peak,'validation_history':history,'test':None}
  save();log('TRAINING_COMPLETE '+name);del opt,average,current
 # Paired schedule is frozen before execution; no branching on test performance.
 for seed in CONFIG['seeds']:
  for kind in CONFIG['arms']:
   # Reserve 20 minutes for evaluations, packaging and local backup before hard stop.
   if time.time()+2300>CONFIG['deadline_epoch']:
    REPORT['schedule_stopped_for_deadline']=True;log('Not starting another training arm: deadline reserve');break
   train_arm(kind,seed)
  else:continue
  break
 # All training/validation choices are now fixed. Test is opened only below.
 REPORT['selection_locked_at']=time.strftime('%Y-%m-%d %H:%M:%S');save()
 for name,result in REPORT['arms'].items():
  load_delta(OUT/f'{name}_best_delta.pt')
  result['test']=evaluate(name,'test',False,True);save();log('ARM_COMPLETE '+name)
 REPORT['completed']=len(REPORT['arms'])==6 and all(r['test']is not None for r in REPORT['arms'].values())
except BaseException as exc:
 REPORT['error']=repr(exc);REPORT['traceback']=traceback.format_exc();traceback.print_exc()
finally:
 save();log('NIGHT_FINISHED '+str(REPORT['completed']))
