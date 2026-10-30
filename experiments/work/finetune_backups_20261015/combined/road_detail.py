"""Small residual adapters on SAM2 FPN features; no grid or coordinate changes."""
import torch
from torch import nn

class DetailBlock(nn.Module):
    def __init__(self,channels=256,width=32):
        super().__init__()
        self.down=nn.Conv2d(channels,width,1,bias=False)
        self.local=nn.Conv2d(width,width,3,padding=1,groups=width,bias=False)
        self.up=nn.Conv2d(width,channels,1,bias=False)
        self.activation=nn.GELU()
        self.reset_parameters()
    def reset_parameters(self):
        self.down.reset_parameters();self.local.reset_parameters();nn.init.zeros_(self.up.weight)
    def forward(self,x):
        residual=self.up(self.activation(self.local(self.activation(self.down(x)))))
        assert residual.shape==x.shape
        return x+residual

class RoadDetailAdapter(nn.Module):
    def __init__(self,channels=256,width=32,levels=3):
        super().__init__();self.enabled=True
        self.blocks=nn.ModuleList([DetailBlock(channels,width) for _ in range(levels)])
    def reset(self,seed):
        devices=[p.device.index for p in self.parameters() if p.is_cuda]
        with torch.random.fork_rng(devices=list(set(devices))):
            torch.manual_seed(seed+911)
            for block in self.blocks:block.reset_parameters()
    def forward(self,features):
        assert len(features)==len(self.blocks)
        if not self.enabled:return features
        return [block(x) for block,x in zip(self.blocks,features)]
