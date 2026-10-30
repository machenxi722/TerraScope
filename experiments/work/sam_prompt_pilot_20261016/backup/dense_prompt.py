"""Experimental SEG-conditioned dense prompt, inspired by RS2-SAM2.

This is a small adaptation, not a reproduction of its BEiT-3 architecture.
Only model features enter forward(); labels are never prompt inputs.
"""
import torch
from torch import nn
from torch.nn import functional as F


class DenseRoadPrompt(nn.Module):
    def __init__(self, channels=256, width=16):
        super().__init__()
        self.projections = nn.ModuleList([nn.Conv2d(channels, width, 1) for _ in range(3)])
        self.condition = nn.Linear(channels, 3 * width)
        self.mask = nn.Sequential(
            nn.Conv2d(3 * width, width, 3, padding=1), nn.GELU(),
            nn.Conv2d(width, 1, 1),
        )
        self.gate = nn.Parameter(torch.zeros(()))
        self.active = False

    def forward(self, features, language):
        assert len(features) == 3
        maps = [F.interpolate(p(x), (256, 256), mode='bilinear', align_corners=False)
                for p, x in zip(self.projections, features)]
        features = torch.cat(maps, dim=1)
        condition = 1 + self.condition(language).tanh()[:, :, None, None]
        return self.mask(features * condition)

    def prompt_hook(self, encoder, args, output):
        sparse, dense = output
        if not self.active:
            return output
        empty = encoder.no_mask_embed.weight.reshape(1, -1, 1, 1).expand_as(dense)
        # At initialization the complete model exactly matches its old path.
        mixed = empty + self.gate.tanh().to(dense.dtype) * (dense - empty)
        return sparse, mixed
