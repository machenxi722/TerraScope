"""RGB-only extraction from the supplied eval_tta.py protocol. Requires validated external weights."""

import hashlib
import importlib
import json
from pathlib import Path

DELTA_SHA = "7c70b717815a39b66c052748c44256b685d17ef1513ee482084ce6419d93dfa8"


class InferenceCanceled(Exception):
    pass


class TerraScopeEngine:
    def __init__(self, base_path: str, delta_path: str, base_manifest_path: str):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required for live inference")
        base, delta = Path(base_path).resolve(), Path(delta_path)
        manifest = json.loads(Path(base_manifest_path).read_text())
        if not manifest:
            raise ValueError("A verified base model manifest is required")
        for relative, expected in manifest.items():
            path = (base / relative).resolve()
            if not path.is_relative_to(base) or not path.is_file():
                raise ValueError("Invalid base manifest path")
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    hasher.update(block)
            if hasher.hexdigest() != expected:
                raise ValueError("Base model checksum mismatch")
        # No unchecked executable/config/weight file may enter from a remote-code model directory.
        actual = {
            str(p.relative_to(base))
            for p in base.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        if actual != set(manifest):
            raise ValueError("Base manifest must cover every model file")
        if hashlib.sha256(delta.read_bytes()).hexdigest() != DELTA_SHA:
            raise ValueError("Delta checkpoint checksum mismatch")
        self.base_manifest_sha256 = hashlib.sha256(
            Path(base_manifest_path).read_bytes()
        ).hexdigest()
        self.tokenizer = AutoTokenizer.from_pretrained(
            base, trust_remote_code=True, local_files_only=True
        )
        self.model = (
            AutoModel.from_pretrained(
                base,
                trust_remote_code=True,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
            )
            .cuda()
            .eval()
        )
        self.model.preparing_for_generation(self.tokenizer)
        self.model.requires_grad_(False)
        self.sam = self.model.grounding_encoder.sam2_model
        self.decoder = self.sam.sam_mask_decoder
        self.projection = self.model.text_hidden_fcs
        self.lm = self.model.language_model.model
        self.decoder.dynamic_multimask_via_stability = False
        self.decoder.float()
        self.projection.float()
        decoder_name = next(
            n for n, m in self.model.named_modules() if m is self.decoder
        )
        projection_name = next(
            n for n, m in self.model.named_modules() if m is self.projection
        )
        parameters = dict(self.model.named_parameters())
        expected = {
            n
            for n in parameters
            if n.startswith((decoder_name + ".", projection_name + "."))
        }
        state = torch.load(delta, map_location="cpu", weights_only=True)
        if set(state) != expected or any(
            state[k].shape != parameters[k].shape for k in expected
        ):
            raise ValueError("Delta key set or tensor shapes mismatch")
        _, unexpected = self.model.load_state_dict(state, strict=False)
        if unexpected:
            raise ValueError("Unexpected delta keys")
        self.model.eval().requires_grad_(False)
        self.module = importlib.import_module(type(self.model).__module__)
        self.device = torch.cuda.get_device_name(0)

    def logits(self, image):
        import numpy as np

        t = self.torch
        model, sam, decoder = self.model, self.sam, self.decoder
        g = model.extra_image_processor.apply_image(np.asarray(image))
        g = t.from_numpy(g).permute(2, 0, 1).contiguous().cuda().to(t.bfloat16)
        g = model.grounding_encoder.preprocess_image(g)[None]
        tiles = self.module.dynamic_preprocess(image, 1, 4, 448, True)
        pv = t.stack([model.transformer(tile) for tile in tiles]).cuda().to(t.bfloat16)
        tokens = "<img>" + "<IMG_CONTEXT>" * (len(tiles) * model.patch_token) + "</img>"
        prompt = (
            model.template["INSTRUCTION"].format(
                input=tokens + "\nSegment the flooded roads in this aerial image.",
                round=1,
                bot_name="BOT",
            )
            + "The flooded road regions are [SEG]"
        )
        ids = t.tensor(self.tokenizer.encode(prompt), device="cuda")[None]
        if ids[0, -1].item() != self.tokenizer.convert_tokens_to_ids("[SEG]"):
            raise ValueError("SEG prefix mismatch")
        with t.autocast("cuda", dtype=t.bfloat16):
            raw = sam.image_encoder(g)["backbone_fpn"][-sam.num_feature_levels :]
            vf = model.extract_feature(pv)
            embeds = model.build_inputs_embeds_for_prefill(
                ids,
                vf.reshape(-1, vf.shape[-1]),
                self.tokenizer.convert_tokens_to_ids("<IMG_CONTEXT>"),
            )
            h = self.lm(
                inputs_embeds=embeds,
                attention_mask=t.ones(embeds.shape[:2], device="cuda", dtype=t.long),
                use_cache=False,
                return_dict=True,
            ).last_hidden_state[:, -1]
            hi = [decoder.conv_s0(raw[0]), decoder.conv_s1(raw[1])]
            return sam._forward_sam_heads(
                raw[-1] + sam.no_mem_embed.reshape(1, -1, 1, 1),
                high_res_features=hi,
                multimask_output=False,
                language_embd=self.projection(h).unsqueeze(1),
            )[3]

    def predict(self, image, strategy, cancel_check=lambda: False):
        import numpy as np
        import torch.nn.functional as F
        from PIL import Image

        t = self.torch
        transforms = [
            (None, ()),
            (Image.Transpose.FLIP_LEFT_RIGHT, (3,)),
            (Image.Transpose.FLIP_TOP_BOTTOM, (2,)),
            (Image.Transpose.ROTATE_180, (2, 3)),
        ]
        aligned = []
        with t.inference_mode():
            for transform, axes in (
                transforms[:1] if strategy == "single_view" else transforms
            ):
                if cancel_check():
                    raise InferenceCanceled()
                out = self.logits(
                    image.transpose(transform) if transform is not None else image
                ).float()
                aligned.append(t.flip(out, axes) if axes else out)
            mean = t.stack(aligned).mean(0)
            pred = (
                F.interpolate(
                    mean,
                    (image.height, image.width),
                    mode="bilinear",
                    align_corners=False,
                )
                > 0
            )
        t.cuda.synchronize()
        if cancel_check():
            raise InferenceCanceled()
        return Image.fromarray(pred[0, 0].cpu().numpy().astype(np.uint8) * 255)
