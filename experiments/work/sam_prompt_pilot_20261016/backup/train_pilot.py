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
from dense_prompt import DenseRoadPrompt

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
CONFIG=json.loads((ROOT/'protocol.json').read_text())
MANIFEST=json.loads((ROOT/'manifest.json').read_text())
DATA_ROOT=Path('/root/autodl-tmp/terrascope/finetune_formal_20261015')
CONFIG['deadline_epoch']=float(os.environ['PILOT_DEADLINE'])
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
  if r['split']=='test':continue
  for field,f in [('rgb_sha256','RGB.jpg'),('label_sha256','labels.png')]:
   assert hashlib.sha256((DATA_ROOT/'data'/r['id']/f).read_bytes()).hexdigest()==r[field]
 path='/root/autodl-tmp/terrascope/models/TerraScope'
 log('Verified data hashes; loading untouched base checkpoint')
 tokenizer=AutoTokenizer.from_pretrained(path,trust_remote_code=True)
 model=AutoModel.from_pretrained(path,trust_remote_code=True,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True).cuda().eval()
 model.preparing_for_generation(tokenizer);model.requires_grad_(False)
 sam=model.grounding_encoder.sam2_model;decoder=sam.sam_mask_decoder;projection=model.text_hidden_fcs;lm=model.language_model.model
 decoder.dynamic_multimask_via_stability=False
 decoder.float();projection.float()
 initial_path=Path(CONFIG['initial_checkpoint'])
 assert hashlib.sha256(initial_path.read_bytes()).hexdigest()==CONFIG['initial_checkpoint_sha256']
 initial_delta=torch.load(initial_path,map_location='cpu',weights_only=True)
 missing,unexpected=model.load_state_dict(initial_delta,strict=False);assert not unexpected
 del initial_delta
 prompt_module=DenseRoadPrompt().cuda().float()
 model.add_module('dense_road_prompt',prompt_module)
 prompt_hook=sam.sam_prompt_encoder.register_forward_hook(prompt_module.prompt_hook)
 initial_prompt={k:v.detach().cpu().clone()for k,v in prompt_module.state_dict().items()}
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
   im=Image.open(DATA_ROOT/'data'/sid/'RGB.jpg').convert('RGB');la=Image.open(DATA_ROOT/'data'/sid/'labels.png').copy();assert im.size==la.size
   image_cache[sid]=(im,la)
   if len(image_cache)>900:image_cache.popitem(last=False)
  return image_cache[sid]
 def prepare(r,augment=False):
  if not augment and r['id']in eval_cache:return eval_cache[r['id']]
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
   hidden=lm(inputs_embeds=embeds,attention_mask=torch.ones(embeds.shape[:2],device='cuda',dtype=torch.long),use_cache=False,return_dict=True).last_hidden_state[:,-1]
  la=np.array(lab);target=torch.from_numpy((la==3).astype('float32')).cuda()[None,None];valid=torch.from_numpy((la!=255).astype('float32')).cuda()[None,None]
  cache={'raw':raw,'hidden':hidden.detach(),'target':target,'valid':valid,
   'y':F.interpolate(target,(256,256),mode='nearest'),'v':F.interpolate(valid,(256,256),mode='nearest')}
  if not augment:eval_cache[r['id']]=cache
  return cache

 def fwd(c,enabled):
  language=projection(c['hidden'])
  coarse=prompt_module(c['raw'],language) if enabled else None
  prompt_module.active=enabled
  hi=[decoder.conv_s0(c['raw'][0]),decoder.conv_s1(c['raw'][1])]
  logits=sam._forward_sam_heads(c['raw'][-1]+sam.no_mem_embed.reshape(1,-1,1,1),high_res_features=hi,multimask_output=False,language_embd=language.unsqueeze(1),mask_inputs=coarse)[3]
  return logits,coarse

 def dice_bce(out,c):
  p=out.float();y=c['y'];v=c['v'];prob=p.sigmoid()*v
  return (F.binary_cross_entropy_with_logits(p,y,reduction='none')*v).sum()/v.sum().clamp_min(1)+1-(2*(prob*y).sum()+1)/(prob.sum()+(y*v).sum()+1)

 def lovasz_hinge(logits,labels,valid):
  keep=valid.reshape(-1)>0;scores=logits.float().reshape(-1)[keep];truth=labels.float().reshape(-1)[keep]
  if scores.numel()==0:return logits.sum()*0
  ordered,indices=torch.sort(1-scores*(2*truth-1),descending=True,stable=True)
  ranked=truth[indices];positives=ranked.sum();overlap=positives-ranked.cumsum(0);union=positives+(1-ranked).cumsum(0)
  jaccard=1-overlap/union.clamp_min(1);weights=torch.cat((jaccard[:1],jaccard[1:]-jaccard[:-1]))
  return (ordered.relu()*weights).sum()

 def task_loss(out,c):
  v=c['v'];bce=(F.binary_cross_entropy_with_logits(out.float(),c['y'],reduction='none')*v).sum()/v.sum().clamp_min(1)
  return bce+lovasz_hinge(out,c['y'],v)

 def summarize(rows):
  tp=sum(r['tp']for r in rows);fp=sum(r['fp']for r in rows);fn=sum(r['fn']for r in rows)
  pos=[r for r in rows if r['gt_pixels']>0];neg=[r for r in rows if r['gt_pixels']==0]
  return {'n':len(rows),'n_positive':len(pos),'global_iou':tp/max(1,tp+fp+fn),'global_dice':2*tp/max(1,2*tp+fp+fn),
   'positive_macro_iou':float(np.mean([r['iou']for r in pos])),'coverage_mae_pp':float(np.mean([r['coverage_error_pp']for r in rows])),
   'scene_tp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in pos),'scene_fn':sum(r['pred_pixels']/r['valid_pixels']<.01 for r in pos),
   'scene_fp':sum(r['pred_pixels']/r['valid_pixels']>=.01 for r in neg),'scene_tn':sum(r['pred_pixels']/r['valid_pixels']<.01 for r in neg)}

 @torch.no_grad()
 def evaluate(name,enabled,save_masks=False,include_coarse=False):
  model.eval();rows=[];coarse_rows=[];start=time.monotonic()
  dest=OUT/'predictions'/name
  if save_masks:dest.mkdir(parents=True,exist_ok=True)
  def row_metrics(r,p,c):
   pred=F.interpolate(p.float(),c['target'].shape[-2:],mode='bilinear',align_corners=False)>0
   gt=c['target']>0;v=c['valid']>0
   tp=int((pred&gt&v).sum());fp=int((pred&~gt&v).sum());fn=int((~pred&gt&v).sum());n=int(v.sum());pp=int((pred&v).sum());gg=int((gt&v).sum())
   return {'id':r['id'],'tp':tp,'fp':fp,'fn':fn,'valid_pixels':n,'pred_pixels':pp,'gt_pixels':gg,'iou':tp/(tp+fp+fn)if tp+fp+fn else None,'coverage_error_pp':abs(pp-gg)/n*100},pred
  for r in MANIFEST:
   if r['split']!='val':continue
   guard();c=prepare(r)
   with amp():out,coarse=fwd(c,enabled)
   row,pred=row_metrics(r,out,c);rows.append(row)
   if save_masks:Image.fromarray(pred[0,0].cpu().numpy().astype('uint8')*255).save(dest/(r['id']+'.png'))
   if include_coarse:
    row,pred=row_metrics(r,coarse,c);coarse_rows.append(row)
    if save_masks:Image.fromarray(pred[0,0].cpu().numpy().astype('uint8')*255).save(dest/(r['id']+'_coarse.png'))
  result={'summary':summarize(rows),'per_image':rows,'seconds':time.monotonic()-start,'gate':float(prompt_module.gate.tanh())if enabled else None}
  if coarse_rows:result['coarse']={'summary':summarize(coarse_rows),'per_image':coarse_rows}
  (OUT/(name+'_val.json')).write_text(json.dumps(result,indent=2));log('VAL '+name+' '+json.dumps(result['summary']));return result

 def reset_model(enabled):
  model.requires_grad_(False);decoder.load_state_dict(baseline['decoder']);projection.load_state_dict(baseline['projection']);prompt_module.load_state_dict(initial_prompt)
  decoder.requires_grad_(True);projection.requires_grad_(True);prompt_module.requires_grad_(enabled)
  prompt_module.active=enabled

 def delta():return {n:p.detach().cpu().clone()for n,p in model.named_parameters()if p.requires_grad}
 def load_delta(path):
  weights=torch.load(path,map_location='cpu',weights_only=True);missing,unexpected=model.load_state_dict(weights,strict=False);assert not unexpected

 # Actual-model identity, alignment and gradient checks, before any experiment update.
 reset_model(True);row=next(r for r in MANIFEST if r['split']=='train'and r['positive']);c=prepare(row)
 with amp():
  a,_=fwd(c,False);b,coarse=fwd(c,True);identity=float((a.float()-b.float()).abs().max());loss=task_loss(b,c)+CONFIG['aux_weight']*dice_bce(coarse,c)
 assert identity==0,identity
 loss.backward();new_grad=sum(float(p.grad.abs().sum())for p in prompt_module.parameters()if p.grad is not None)
 assert math.isfinite(new_grad)and new_grad>0
 assert all(p.grad is None for p in sam.image_encoder.parameters())
 assert all(p.grad is None for p in lm.parameters())
 REPORT['preflight']={'zero_gate_max_logit_difference':identity,'new_module_gradient_l1':new_grad,'new_module_parameters':sum(p.numel()for p in prompt_module.parameters()),'visual_and_language_encoders_frozen':True}
 model.zero_grad(set_to_none=True);reset_model(False);save()
 initial=evaluate('initial_single_view',False,True)
 assert abs(initial['summary']['global_iou']-CONFIG['expected_initial_val_iou'])<1e-6,(initial['summary']['global_iou'],CONFIG['expected_initial_val_iou'])
 REPORT['initial_validation']=initial['summary'];save()
 plans=[]

 def train_arm(name,enabled):
  reset_model(enabled);seeded(CONFIG['seed']);model.zero_grad(set_to_none=True)
  groups=[{'params':list(decoder.parameters())+list(projection.parameters()),'lr':CONFIG['head_lr'],'initial_lr':CONFIG['head_lr']}]
  if enabled:groups.append({'params':list(prompt_module.parameters()),'lr':CONFIG['module_lr'],'initial_lr':CONFIG['module_lr']})
  opt=torch.optim.AdamW(groups,weight_decay=.01);params=[p for p in model.parameters()if p.requires_grad]
  best=initial['summary']['global_iou'];best_step=0;torch.save(delta(),OUT/(name+'_best_delta.pt'))
  trace=[];history=[{'micro_step':0,**initial['summary']}];plan=[];start=time.monotonic();steps=CONFIG['micro_steps'];accum=CONFIG['gradient_accumulation']
  pos=[r for r in MANIFEST if r['split']=='train'and r['positive']];neg=[r for r in MANIFEST if r['split']=='train'and not r['positive']]
  torch.cuda.reset_peak_memory_stats();log('ARM_START '+name)
  for i in range(steps):
   guard();lm.eval();decoder.train();projection.train();prompt_module.train(enabled)
   t=time.perf_counter();r=random.choice(pos if i%2==0 else neg);c=prepare(r,True);plan.append(r['id'])
   with amp():
    out,coarse=fwd(c,enabled);main=task_loss(out,c);aux=dice_bce(coarse,c)if enabled else main*0;loss=main+CONFIG['aux_weight']*aux
   assert torch.isfinite(loss),float(loss)
   (loss/accum).backward()
   if(i+1)%accum==0:
    update=(i+1)//accum;total=steps//accum;warm=CONFIG['warmup_updates']
    scale=min(1,update/warm)if update<=warm else .1+.9*(1+math.cos(math.pi*(update-warm)/(total-warm)))/2
    for g in opt.param_groups:g['lr']=g['initial_lr']*scale
    torch.nn.utils.clip_grad_norm_(params,1);opt.step();opt.zero_grad(set_to_none=True)
   sync();trace.append({'micro_step':i+1,'id':r['id'],'loss':float(loss.detach()),'main_loss':float(main.detach()),'aux_loss':float(aux.detach()),'seconds':time.perf_counter()-t,'gate':float(prompt_module.gate.tanh())if enabled else None})
   if(i+1)%100==0:log(f'TRAIN {name} {i+1}/{steps} loss={np.mean([x["loss"]for x in trace[-100:]]):.4f} sec={np.mean([x["seconds"]for x in trace[-100:]]):.3f} gate={float(prompt_module.gate.tanh()):.4f}')
   if(i+1)%CONFIG['validate_every']==0:
    metrics=evaluate(name+'_step'+str(i+1),enabled);history.append({'micro_step':i+1,**metrics['summary']})
    if metrics['summary']['global_iou']>best:best=metrics['summary']['global_iou'];best_step=i+1;torch.save(delta(),OUT/(name+'_best_delta.pt'))
    (OUT/(name+'_training.json')).write_text(json.dumps({'trace':trace,'validation':history,'best_step':best_step,'sampling_sequence':plan},indent=2))
  plans.append(plan);load_delta(OUT/(name+'_best_delta.pt'))
  final=evaluate(name+'_selected',enabled,True,enabled)
  result={'best_micro_step':best_step,'validation':final['summary'],'micro_steps':steps,'optimizer_updates':steps//accum,'seconds':time.monotonic()-start,'trainable_parameters':sum(p.numel()for p in params),'peak_gpu_allocated_gib':torch.cuda.max_memory_allocated()/2**30,'gate':float(prompt_module.gate.tanh())if enabled else None}
  if enabled:
   result['coarse_only_validation']=final['coarse']['summary']
   result['disable_prompt_validation']=evaluate(name+'_prompt_disabled',False,True)['summary']
  REPORT['arms'][name]=result;save();log('ARM_COMPLETE '+name);del opt

 train_arm('continued_control',False)
 train_arm('dense_prompt',True)
 assert plans[0]==plans[1];REPORT['paired_sampling_identical']=True
 REPORT['completed']=True;REPORT['test_accessed']=False
 REPORT['conclusion_scope']='Single-seed validation pilot, not an independent test result or full RS2-SAM2 reproduction.'
except BaseException as exc:
 REPORT['error']=repr(exc);REPORT['traceback']=traceback.format_exc();traceback.print_exc()
finally:
 save();log('PILOT_FINISHED '+str(REPORT['completed']))
