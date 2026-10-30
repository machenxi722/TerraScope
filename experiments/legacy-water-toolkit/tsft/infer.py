"""Apply a trained head to a new RGB image with the SAME fixed-prefix protocol."""
import argparse
from pathlib import Path

import torch
from PIL import Image

from .cache import amp, extract_features, load_official_model, model_identity
from .common import load_tensor_file, write_json
from .evaluate import load_evaluation_head
from .head import selected_logits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True)
    p.add_argument("--cache", required=True, help="Contains base_head.pt and the protocol provenance")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--image", required=True, help="RGB produced using the same band/radiometry recipe")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    head, meta, step = load_evaluation_head(a.cache, a.checkpoint, "cuda")
    if model_identity(a.model) != meta["model"]:
        raise ValueError("Full model does not match the cached frozen backbone")
    model, tokenizer = load_official_model(a.model)
    im = Image.open(a.image).convert("RGB")
    feature = extract_features(model, tokenizer, im, meta["max_patches"])
    head.eval()
    with torch.no_grad(), amp("cuda"):
        low, iou = head([t.cuda() for t in feature["raw_fpn"]], feature["seg_hidden"].cuda())
        logits = selected_logits(low, iou, (im.height, im.width))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((logits[0, 0] > 0).cpu().numpy().astype("uint8") * 255).save(out)
    write_json(out.with_suffix(".json"), {"protocol": meta["protocol"], "step": step,
                "fingerprint": meta["fingerprint"], "size": [im.height, im.width],
                "note": "RGB-only mask; physical area requires a separately supplied valid mask and georeferencing."})


if __name__ == "__main__":
    main()
