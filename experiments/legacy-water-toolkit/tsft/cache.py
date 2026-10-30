"""Cache frozen pre-projector SEG states and RAW SAM2 FPN features on one CUDA GPU."""
import argparse
import contextlib
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from .common import (HF_REPO, HF_REVISION, PROMPT, PREFIX, PROTOCOL, ROOT,
                     atomic_torch_save, check_deadline, deadline, digest,
                     load_manifest, load_tensor_file, read_json, sha256, write_json)
from .head import WaterHead


def amp(device):
    return torch.autocast("cuda", dtype=torch.bfloat16) if str(device).startswith("cuda") else contextlib.nullcontext()


def model_identity(model_dir):
    root = Path(model_dir).resolve()
    required = ["config.json", "modeling_sa2va_chat.py", "sam2.py", "tokenizer_config.json"]
    for name in required:
        if not (root / name).is_file():
            raise FileNotFoundError(root / name)
    for name in ("sam2.py", "modeling_sa2va_chat.py"):
        if sha256(root / name) != sha256(ROOT / "vendor_metadata" / name):
            raise ValueError(f"{name} differs from pinned official code; review compatibility first")
    weights = sorted(root.glob("*.safetensors"))
    if not weights:
        raise FileNotFoundError("Need an exported HF model with safetensors weights, not a training .pth")
    # Hash actual tensors once per cache invocation, not just config / checkpoint filename.
    files = weights + sorted(root.glob("*.json")) + sorted(root.glob("*.py"))
    return {"source_repo": HF_REPO, "reference_revision": HF_REVISION,
            "files_sha256": {f.name: sha256(f) for f in files}}


def load_official_model(model_dir):
    from transformers import AutoModel, AutoTokenizer
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError("Cache stage requires a CUDA GPU with BF16 support")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True, local_files_only=True)
    model = AutoModel.from_pretrained(model_dir, trust_remote_code=True, local_files_only=True,
                                      torch_dtype=torch.bfloat16, low_cpu_mem_usage=True,
                                      use_flash_attn=False).to("cuda").eval()
    model.requires_grad_(False)
    model.preparing_for_generation(tokenizer, max_new_tokens=8, torch_dtype=torch.bfloat16)
    if model.config.llm_config.architectures != ["Qwen2ForCausalLM"]:
        raise ValueError("This bridge was inspected for the pinned TerraScope Qwen2 model only")
    return model, tokenizer


@torch.no_grad()
def extract_features(model, tokenizer, image, max_patches=1):
    """No masks, coordinates, GT fractions, or generated answers enter this function."""
    module = sys.modules[model.__class__.__module__]
    tiles = module.dynamic_preprocess(image, 1, max_patches, model.image_size, model.use_thumbnail)
    pixels = torch.stack([model.transformer(im) for im in tiles]).to("cuda", torch.bfloat16)
    token_string = "<img>" + "<IMG_CONTEXT>" * (len(tiles) * model.patch_token) + "</img>"
    question = PROMPT.replace("<image>", token_string)
    text = model.template["INSTRUCTION"].format(input=question, round=1, bot_name=model.bot_name) + PREFIX
    ids = torch.tensor(tokenizer.encode(text), device="cuda").unsqueeze(0)
    seg_id = tokenizer.convert_tokens_to_ids("[SEG]")
    if int((ids == seg_id).sum()) != 1 or int(ids[0, -1]) != seg_id:
        raise ValueError("The fixed assistant prefix must end in exactly one atomic [SEG] token")
    with amp("cuda"):
        visual = model.extract_feature(pixels).reshape(-1, model.language_model.config.hidden_size)
        embeddings = model.build_inputs_embeds_for_prefill(ids, visual, model.img_context_token_id)
        # Base Qwen2Model avoids allocating a full L x vocabulary LM-head logits tensor.
        out = model.language_model.model(inputs_embeds=embeddings, attention_mask=torch.ones_like(ids),
                                          use_cache=False, return_dict=True)
        seg = out.last_hidden_state[:, -1].detach()
        g_image = model.extra_image_processor.apply_image(np.asarray(image))
        g = torch.from_numpy(g_image.copy()).permute(2, 0, 1).to("cuda", torch.bfloat16)
        g = model.grounding_encoder.preprocess_image(g).unsqueeze(0)
        # forward_image() would execute trainable conv_s0/s1: explicitly call image_encoder.
        raw = model.grounding_encoder.sam2_model.image_encoder(g)["backbone_fpn"][-3:]
    return {"raw_fpn": [t.detach().cpu().to(torch.bfloat16) for t in raw],
            "seg_hidden": seg.cpu().to(torch.bfloat16), "tokens": ids.shape[1]}


@torch.no_grad()
def parity_check(model, head, feature):
    """Verify this adapter against the official first-frame SAM2 head for identical inputs."""
    core = model.grounding_encoder.sam2_model
    fpn = [t.cuda() for t in feature["raw_fpn"]]
    seg = feature["seg_hidden"].cuda()
    head = head.cuda().eval()
    with amp("cuda"):
        actual, actual_iou = head(fpn, seg)
        high = [core.sam_mask_decoder.conv_s0(fpn[0]), core.sam_mask_decoder.conv_s1(fpn[1])]
        reference = core._forward_sam_heads(
            backbone_features=fpn[2] + core.no_mem_embed.reshape(1, 256, 1, 1),
            high_res_features=high, multimask_output=True,
            language_embd=model.text_hidden_fcs(seg).unsqueeze(1))
    torch.testing.assert_close(actual, reference[0], rtol=0.02, atol=0.05)
    torch.testing.assert_close(actual_iou, reference[2].float(), rtol=0.02, atol=0.01)
    agreement = float(((actual > 0) == (reference[0] > 0)).float().mean())
    if agreement < 0.995:
        raise ValueError(f"Head parity failed: binary agreement {agreement:.6f}")
    return {"max_abs_logit_diff": float((actual - reference[0]).abs().max()),
            "binary_agreement": agreement}


def main():
    import transformers
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-patches", type=int, choices=[1, 4], default=1)
    p.add_argument("--limit", type=int, default=0, help="Pilot only; incomplete caches cannot train/evaluate")
    p.add_argument("--hours", type=float, default=3)
    a = p.parse_args()
    end = deadline(a.hours)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(a.manifest)
    metadata = {"schema": 1, "protocol": PROTOCOL, "prompt": PROMPT, "assistant_prefix": PREFIX,
                "max_patches": a.max_patches, "sam_resize": "official-DirectResize-1024",
                "runtime": {"torch": str(torch.__version__), "transformers": transformers.__version__},
                "bridge_sha256": sha256(__file__),
                "manifest_sha256": sha256(a.manifest), "model": model_identity(a.model)}
    fingerprint = digest(metadata)
    index_path = out / "index.json"
    index = {"fingerprint": fingerprint, "metadata": metadata, "features": {}, "complete": False}
    if index_path.exists():
        index = read_json(index_path)
        if index["fingerprint"] != fingerprint:
            raise ValueError("Cache fingerprint changed; use a NEW cache directory")
    check_deadline(end)
    model, tokenizer = load_official_model(a.model)
    head = WaterHead.from_official(model)
    if not (out / "base_head.pt").exists():
        head.save_base(out / "base_head.pt", {"fingerprint": fingerprint, **metadata})
    else:
        saved = load_tensor_file(out / "base_head.pt")
        if saved["metadata"]["fingerprint"] != fingerprint:
            raise ValueError("Base head belongs to a different cache; use a new directory")
        if index.get("base_sha256") and sha256(out / "base_head.pt") != index["base_sha256"]:
            raise ValueError("Base head checkpoint was modified")
    index["base_sha256"] = sha256(out / "base_head.pt")
    start = time.time()
    count = 0
    try:
        for row in manifest["samples"]:
            check_deadline(end)
            if sha256(row["image"]) != row["image_sha256"]:
                raise ValueError(f"Image changed: {row['id']}")
            path = out / "features" / f"{row['id']}.pt"
            existing = index["features"].get(row["id"])
            if existing and path.exists() and sha256(path) == existing["sha256"]:
                continue
            t = time.time()
            feature = extract_features(model, tokenizer, Image.open(row["image"]).convert("RGB"), a.max_patches)
            if count == 0:
                index["parity"] = parity_check(model, head, feature)
                head.cpu()
                torch.cuda.empty_cache()
            feature.update({"id": row["id"], "fingerprint": fingerprint})
            atomic_torch_save(feature, path)
            index["features"][row["id"]] = {"file": str(path.relative_to(out)), "sha256": sha256(path),
                                                   "split": row["split"]}
            count += 1
            write_json(index_path, index)
            print(f"cache {len(index['features'])}/{len(manifest['samples'])} {row['id']} {time.time()-t:.1f}s", flush=True)
            if a.limit and count >= a.limit:
                break
    finally:
        index["complete"] = len(index["features"]) == len(manifest["samples"])
        index["last_run_seconds"] = time.time() - start
        index["peak_gpu_gib"] = torch.cuda.max_memory_allocated() / 2**30
        write_json(index_path, index)
    print("cache complete:", index["complete"], "peak GiB:", index["peak_gpu_gib"])


if __name__ == "__main__":
    main()
