import copy
import datetime as dt
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from affine import Affine

from tsft.data import official_rows, pixel_areas
from tsft.evaluate import aggregate, sample_metrics
from tsft.head import WaterHead, losses, official_sam_module
from tsft.run_budget import make_budget

torch.set_num_threads(2)


def feature():
    return [torch.randn(1, 256, 16, 16), torch.randn(1, 256, 8, 8), torch.randn(1, 256, 4, 4)]


def test_official_head_parity_gradients_and_reload(tmp_path):
    torch.manual_seed(7)
    head = WaterHead(llm_dim=32, grid=4).eval()
    fpn, seg = feature(), torch.randn(1, 32)
    actual, iou = head(fpn, seg)
    # Direct execution of the actual official TerraScope SAM2Base head method.
    core = SimpleNamespace(sam_prompt_embed_dim=256, sam_image_embedding_size=4,
                           sam_prompt_encoder=head.prompt_encoder, sam_mask_decoder=head.decoder,
                           pred_obj_scores=False, obj_ptr_proj=torch.nn.Identity(), image_size=1024)
    official = official_sam_module().SAM2Base._forward_sam_heads(
        core, fpn[-1], high_res_features=[head.decoder.conv_s0(fpn[0]), head.decoder.conv_s1(fpn[1])],
        multimask_output=True, language_embd=head.projector(seg).unsqueeze(1))
    torch.testing.assert_close(actual, official[0], rtol=0, atol=0)
    torch.testing.assert_close(iou, official[2], rtol=0, atol=0)
    label = (torch.rand(1, 1, 16, 16) > .5).float()
    valid, area = torch.ones_like(label), torch.ones_like(label)
    loss, _ = losses(actual, iou, label, valid, area, .1)
    loss.backward()
    for mod in (head.projector, head.decoder.conv_s0, head.decoder.conv_s1,
                head.decoder.iou_prediction_head, *head.decoder.output_hypernetworks_mlps[1:]):
        assert any(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum() > 0 for p in mod.parameters())
    assert all(p.grad is None for p in head.prompt_encoder.parameters())
    assert all(n.startswith(("projector.", "decoder.")) for n, p in head.named_parameters() if p.requires_grad)
    head.save_base(tmp_path / "head.pt", {"test": True})
    restored, meta = WaterHead.load_base(tmp_path / "head.pt")
    restored.eval()
    torch.testing.assert_close(restored(fpn, seg)[0], actual, rtol=0, atol=0)
    assert meta["test"]


def test_invalid_pixels_have_zero_gradient_and_do_not_change_loss():
    logits = torch.randn(1, 3, 4, 4, requires_grad=True)
    label = torch.ones(1, 1, 4, 4)
    valid = torch.ones_like(label)
    valid[:, :, :2] = 0
    area = torch.ones_like(label) * 100
    ious = torch.full((1, 3), .5, requires_grad=True)
    loss, _ = losses(logits, ious, label, valid, area, .1)
    changed = label.clone()
    changed[:, :, :2] = 0
    other, _ = losses(logits, ious, changed, valid, area, .1)
    torch.testing.assert_close(loss, other)
    loss.backward()
    assert torch.count_nonzero(logits.grad[:, :, :2]) == 0
    assert logits.grad[:, :, 2:].abs().sum() > 0


def test_empty_ground_truth_remains_supervised():
    logits = torch.zeros(1, 3, 4, 4, requires_grad=True)
    zero, one = torch.zeros(1, 1, 4, 4), torch.ones(1, 1, 4, 4)
    loss, parts = losses(logits, torch.ones(1, 3), zero, one, one, .1)
    loss.backward()
    assert parts["dice"] == 0 and logits.grad.sum() > 0
    with pytest.raises(ValueError, match="invalid"):
        losses(logits, torch.ones(1, 3), zero, zero, one)


def test_pixel_area_and_empty_metric_policy():
    areas = pixel_areas("EPSG:32631", Affine(10, 0, 0, 0, -10, 0), 2, 2)
    np.testing.assert_allclose(areas, 100)
    geo = pixel_areas("EPSG:4326", Affine(.0001, 0, 0, 0, -.0001, 60), 2, 2)
    assert 50 < geo.mean() < 70  # Real m² near 60N; not degrees² or a nominal 100 m².
    empty = np.zeros((2, 2), dtype=bool)
    valid = np.ones((2, 2), dtype=bool)
    row = sample_metrics(empty, empty, valid, areas)
    assert row["iou"] is None and row["area_abs_error_pp"] == 0
    summary = aggregate([row])
    assert summary["micro_iou"] is None and summary["n_empty_both"] == 1
    invalid_pred = np.ones((2, 2), dtype=bool)
    valid[0, 0] = False
    assert sample_metrics(invalid_pred, empty, valid, areas)["fp"] == 3


def test_official_splits_and_budget():
    rows = official_rows()
    assert {s: sum(r["split"] == s for r in rows) for s in ("train", "val", "test", "bolivia")} == {
        "train": 252, "val": 89, "test": 90, "bolivia": 15}
    assert len({r["id"] for r in rows}) == 446
    b = make_budget("2026-10-15T10:00:00+08:00", 7.5)
    assert b["rental_hours_cap"] == 24
    assert b["work_deadline_epoch"] - b["rental_start"] == 23 * 3600
    assert b["hourly_price"] * b["rental_hours_cap"] + b["non_gpu_reserve_cny"] <= 200
    assert make_budget("2026-10-15T10:00:00+08:00", 12)["rental_hours_cap"] == 15
    with pytest.raises(ValueError, match="timezone"):
        make_budget("2026-10-15T10:00:00", 5)
