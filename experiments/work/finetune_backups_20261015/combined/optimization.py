import torch
from torch import nn
import torch.nn.functional as F

class RoadAuxHead(nn.Module):
 def __init__(self):
  super().__init__();self.net=nn.Sequential(nn.Conv2d(256,32,3,padding=1),nn.GELU(),nn.Conv2d(32,1,1))
 def reset(self,seed):
  devices=list({p.device.index for p in self.parameters() if p.is_cuda})
  with torch.random.fork_rng(devices=devices):
   torch.manual_seed(seed+1729)
   for m in self.net:
    if hasattr(m,'reset_parameters'):m.reset_parameters()
 def forward(self,x):return self.net(x)

def segmentation_loss(p,y,v):
 p=p.float();prob=p.sigmoid()*v
 return (F.binary_cross_entropy_with_logits(p,y,reduction='none')*v).sum()/v.sum().clamp_min(1)+1-(2*(prob*y).sum()+1)/(prob.sum()+(y*v).sum()+1)

def boundary_loss(p,y,v):
 # 3x3 foreground/background transition band on the decoder grid.
 dilation=F.max_pool2d(y,3,stride=1,padding=1)
 erosion=-F.max_pool2d(-y,3,stride=1,padding=1)
 valid_neighborhood=-F.max_pool2d(-v,3,stride=1,padding=1)
 band=(dilation-erosion).clamp(0,1)*valid_neighborhood
 return (F.binary_cross_entropy_with_logits(p.float(),y,reduction='none')*band).sum()/band.sum().clamp_min(1)

def check_loss_edges():
 p=torch.zeros(1,1,8,8,requires_grad=True);v=torch.ones_like(p)
 for y in [torch.zeros_like(p),torch.ones_like(p)]:
  b=boundary_loss(p,y,v);assert b.item()==0;b.backward();assert torch.isfinite(p.grad).all();p.grad.zero_()
 y=torch.zeros_like(p);y[:,:,2:6,2:6]=1
 b=boundary_loss(p,y,v);assert b>0;b.backward();assert p.grad.abs().sum()>0
 z=boundary_loss(p,y,torch.zeros_like(p));assert z.item()==0
 return {'empty_and_full_targets_zero_boundary_loss':True,'partial_target_finite_nonzero_gradient':True,'all_invalid_zero_boundary_loss':True}
