"""Use the pinned TerraScope HF implementation's actual SAM2 decoder classes."""
import importlib.util

import torch
from torch import nn
import torch.nn.functional as F

from .common import ROOT, atomic_torch_save, load_tensor_file, verify_sources


def official_sam_module():
    verify_sources()
    spec = importlib.util.spec_from_file_location("terrascope_pinned_sam2", ROOT / "vendor_metadata/sam2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WaterHead(nn.Module):
    def __init__(self, llm_dim=3584, grid=64):
        super().__init__()
        sam = official_sam_module()
        self.llm_dim, self.grid = llm_dim, grid
        self.projector = nn.Sequential(nn.Linear(llm_dim, llm_dim), nn.ReLU(inplace=True),
                                       nn.Linear(llm_dim, 256), nn.Dropout(0.0))
        self.prompt_encoder = sam.PromptEncoder(256, (grid, grid), (1024, 1024), mask_in_chans=16)
        self.decoder = sam.MaskDecoder(
            transformer_dim=256, transformer=sam.TwoWayTransformer(2, 256, 8, 2048),
            num_multimask_outputs=3, iou_head_depth=3, iou_head_hidden_dim=256,
            use_high_res_features=True, iou_prediction_use_sigmoid=True,
            pred_obj_scores=True, pred_obj_scores_mlp=True, use_multimask_token_for_obj_ptr=True,
            dynamic_multimask_via_stability=True,
            dynamic_multimask_stability_delta=0.05, dynamic_multimask_stability_thresh=0.98)
        self.register_buffer("no_mem_embed", torch.zeros(1, 256, 1, 1))
        self.requires_grad_(False)
        self.projector.requires_grad_(True)
        self.decoder.requires_grad_(True)
        # These output branches are unused in a single image, three-candidate mask protocol.
        self.decoder.pred_obj_score_head.requires_grad_(False)
        self.decoder.output_hypernetworks_mlps[0].requires_grad_(False)

    def train(self, mode=True):
        super().train(mode)
        self.prompt_encoder.eval()
        return self

    def forward(self, raw_fpn, seg_hidden):
        if len(raw_fpn) != 3 or raw_fpn[-1].shape[-2:] != (self.grid, self.grid):
            raise ValueError("Expected three RAW FPN levels, before decoder conv_s0 / conv_s1")
        lang = self.projector(seg_hidden.float()).unsqueeze(1)
        batch, _, h, w = raw_fpn[-1].shape
        points = (torch.zeros(batch, 1, 2, device=lang.device),
                  -torch.ones(batch, 1, dtype=torch.int32, device=lang.device))
        sparse, dense = self.prompt_encoder(points=points, boxes=None, masks=None)
        sparse = torch.cat((sparse.to(lang.dtype), lang), dim=1)
        # Do NOT cache these projections: they belong to the trainable decoder.
        high = [self.decoder.conv_s0(raw_fpn[0].float()), self.decoder.conv_s1(raw_fpn[1].float())]
        masks, ious, _, _ = self.decoder(
            image_embeddings=raw_fpn[-1] + self.no_mem_embed.to(raw_fpn[-1].dtype),
            image_pe=self.prompt_encoder.get_dense_pe().to(lang.dtype), sparse_prompt_embeddings=sparse,
            dense_prompt_embeddings=dense.to(lang.dtype), multimask_output=True,
            repeat_image=False, high_res_features=high)
        return masks.float(), ious.float()

    @classmethod
    def from_official(cls, model):
        core = model.grounding_encoder.sam2_model
        if not core.directly_add_no_mem_embed or not core.use_high_res_features_in_sam:
            raise ValueError("Unexpected official SAM2 architecture")
        obj = cls(model.text_hidden_fcs[0].in_features)
        obj.projector.load_state_dict(model.text_hidden_fcs.state_dict(), strict=True)
        obj.decoder.load_state_dict(core.sam_mask_decoder.state_dict(), strict=True)
        obj.prompt_encoder.load_state_dict(core.sam_prompt_encoder.state_dict(), strict=True)
        obj.no_mem_embed.copy_(core.no_mem_embed.detach().reshape(1, 256, 1, 1).cpu())
        return obj

    def save_base(self, path, metadata):
        atomic_torch_save({"llm_dim": self.llm_dim, "grid": self.grid,
                           "state": {k: v.detach().cpu() for k, v in self.state_dict().items()},
                           "metadata": metadata}, path)

    @classmethod
    def load_base(cls, path):
        data = load_tensor_file(path)
        obj = cls(data["llm_dim"], data["grid"])
        obj.load_state_dict(data["state"], strict=True)
        return obj, data["metadata"]


def native_logits(low_res, size):
    # Match the official two-stage mask interpolation, then measure on the native label grid.
    high = F.interpolate(low_res.float(), (1024, 1024), mode="bilinear", align_corners=False)
    return F.interpolate(high, size, mode="bilinear", align_corners=False)


def selected_logits(low_res, ious, size):
    idx = ious.argmax(dim=1)
    best = low_res[torch.arange(len(idx), device=idx.device), idx].unsqueeze(1)
    return native_logits(best, size)


def losses(logits, ious, label, valid, area_m2, area_weight=0.0):
    """All three candidates supervised; IoU targets detached; invalid pixels never contribute."""
    # Shape: B,K,H,W; ground truth B,1,H,W. Loss weights use physical pixel area.
    target = label.float().expand_as(logits)
    weights = (valid.float() * area_m2.float()).expand_as(logits)
    denominator = weights.sum((-2, -1)).clamp_min(1e-8)
    if not bool(valid.any()):
        raise ValueError("All-invalid target cannot be used in training")
    prob = logits.sigmoid()
    bce = (F.binary_cross_entropy_with_logits(logits, target, reduction="none") * weights).sum((-2, -1)) / denominator
    intersection = (prob * target * weights).sum((-2, -1)) / denominator
    pred_fraction = (prob * weights).sum((-2, -1)) / denominator
    gt_fraction = (target * weights).sum((-2, -1)) / denominator
    dice = 1 - (2 * intersection + 1e-6) / (pred_fraction + gt_fraction + 1e-6)
    # Empty-water scenes retain BCE and area supervision; no unstable empty-target Dice term.
    dice = torch.where(gt_fraction > 0, dice, torch.zeros_like(dice))
    area = (pred_fraction - gt_fraction).abs()
    with torch.no_grad():
        binary = prob > 0.5
        tp = (binary * target * weights).sum((-2, -1))
        union = ((binary | target.bool()) * weights).sum((-2, -1))
        quality = torch.where(union > 0, tp / union.clamp_min(1e-8), torch.ones_like(union))
    quality_loss = F.mse_loss(ious, quality)
    total = bce.mean() + dice.mean() + 0.1 * quality_loss + area_weight * area.mean()
    return total, {"bce": bce.mean().item(), "dice": dice.mean().item(),
                   "quality": quality_loss.item(), "area": area.mean().item()}
