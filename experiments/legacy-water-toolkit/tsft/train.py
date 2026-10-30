"""M1/M2: train only the text projector and active SAM2 mask-decoder branches."""
import argparse
import json
import random
import signal
import time
from pathlib import Path

import numpy as np
import torch

from .cache import amp
from .common import atomic_torch_save, check_deadline, deadline, write_json
from .dataset import CachedDataset, to_device
from .evaluate import evaluate
from .head import WaterHead, losses, native_logits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--area-weight", type=float, choices=[0.0, 0.1], default=0.0)
    p.add_argument("--seed", type=int, default=20261015)
    p.add_argument("--max-steps", type=int, default=1000, help="Optimizer steps, not microbatches")
    p.add_argument("--accum", type=int, default=8)
    p.add_argument("--val-every", type=int, default=100)
    p.add_argument("--patience", type=int, default=5)
    p.add_argument("--decoder-lr", type=float, default=1e-4)
    p.add_argument("--projector-lr", type=float, default=2e-5)
    p.add_argument("--hours", type=float, default=3)
    p.add_argument("--device", default="cuda")
    a = p.parse_args()
    if min(a.max_steps, a.accum, a.val_every, a.patience) <= 0:
        p.error("steps, accumulation, validation interval, patience must be positive")
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Use a new run directory; cache is reusable but runs are never overwritten")
    out.mkdir(parents=True, exist_ok=True)
    end = deadline(a.hours)
    started = time.time()
    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)
    torch.backends.cudnn.benchmark = False
    if str(a.device).startswith("cuda"):
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError("CUDA BF16 is required by the server training configuration")
        torch.cuda.manual_seed_all(a.seed)
    train = CachedDataset(a.manifest, a.cache, "train")
    val = CachedDataset(a.manifest, a.cache, "val")
    model, meta = WaterHead.load_base(Path(a.cache) / "base_head.pt")
    model.to(a.device)
    groups = [{"params": [p for p in model.projector.parameters() if p.requires_grad], "lr": a.projector_lr},
              {"params": [p for p in model.decoder.parameters() if p.requires_grad], "lr": a.decoder_lr}]
    optimizer = torch.optim.AdamW(groups, weight_decay=0.01)
    trainable = {n: p.numel() for n, p in model.named_parameters() if p.requires_grad}
    assert all(n.startswith(("projector.", "decoder.")) for n in trainable)
    write_json(out / "run_config.json", {**vars(a), "fingerprint": meta["fingerprint"],
               "trainable_parameters": trainable, "trainable_total": sum(trainable.values()),
               "versions": {"torch": str(torch.__version__), "numpy": np.__version__},
               "gpu": torch.cuda.get_device_name() if str(a.device).startswith("cuda") else "CPU"})
    # End a timed subprocess gracefully; best.pt always refers to a completed validation.
    def stop(signum, frame):
        raise TimeoutError(f"Received signal {signum}")
    signal.signal(signal.SIGTERM, stop)
    step, best_score, best_step, stale = 0, None, 0, 0
    order, pos = list(range(len(train))), 0
    random.shuffle(order)
    log = open(out / "metrics.jsonl", "a", buffering=1)

    def checkpoint(path, validation=None):
        atomic_torch_save({"state": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                           "fingerprint": meta["fingerprint"], "step": step, "seed": a.seed,
                           "area_weight": a.area_weight, "validation": validation,
                           "protocol": meta["protocol"]}, path)

    def validate():
        nonlocal best_score, best_step, stale
        summary, _ = evaluate(model, val, a.device, end)
        if summary["micro_iou"] is None:
            raise ValueError("Validation IoU undefined")
        score = (summary["micro_iou"], -summary["area_mae_pp"])
        improved = best_score is None or score > best_score
        if improved:
            best_score, best_step, stale = score, step, 0
            checkpoint(out / "best.pt", summary)
        else:
            stale += 1
        event = {"step": step, "validation": summary, "improved": improved}
        log.write(json.dumps(event) + "\n")
        print(event, flush=True)
        model.train()

    status = "completed"
    try:
        validate()  # R1 checkpoint at step 0 is an explicit fallback if every update is worse.
        for planned_step in range(1, a.max_steps + 1):
            check_deadline(end, reserve=90)
            optimizer.zero_grad(set_to_none=True)
            batch_losses = []
            for _ in range(a.accum):
                check_deadline(end, reserve=60)
                feature, target, _ = train[order[pos]]
                pos += 1
                if pos == len(order):
                    random.shuffle(order)
                    pos = 0
                feature, target = to_device(feature, target, a.device)
                with amp(a.device):
                    low, ious = model(feature["raw_fpn"], feature["seg_hidden"])
                    logits = native_logits(low, target["label"].shape[-2:])
                    loss, parts = losses(logits, ious, target["label"], target["valid"],
                                          target["area_m2"], a.area_weight)
                if not torch.isfinite(loss):
                    raise FloatingPointError("Non-finite training loss")
                (loss / a.accum).backward()
                batch_losses.append(loss.item())
            if planned_step == 1:
                for module in (model.projector, model.decoder.conv_s0, model.decoder.conv_s1):
                    if not any(p.grad is not None and bool(p.grad.abs().sum() > 0) for p in module.parameters()):
                        raise RuntimeError("Missing gradient: stale/post-projection cache or detached head")
                assert all(p.grad is None for p in model.prompt_encoder.parameters())
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0,
                                           error_if_nonfinite=True)
            optimizer.step()
            step = planned_step
            event = {"step": step, "loss": float(np.mean(batch_losses)),
                     "elapsed_seconds": time.time() - started, **parts}
            log.write(json.dumps(event) + "\n")
            if step % 10 == 0:
                print(event, flush=True)
            if step == 100:
                # Includes loading, validation, disk IO, and all eight microbatches per update.
                forecast = {"profile_steps": step, "elapsed_seconds": time.time() - started,
                            "conservative_1000_step_hours": (time.time() - started) * 10 / 3600,
                            "peak_gpu_gib": torch.cuda.max_memory_allocated() / 2**30 if str(a.device).startswith("cuda") else None}
                write_json(out / "profile_100_steps.json", forecast)
                print(forecast, flush=True)
            if step % a.val_every == 0 or step == a.max_steps:
                validate()
                checkpoint(out / "latest.pt")
                if stale >= a.patience:
                    status = "early_stopped"
                    break
    except TimeoutError as exc:
        status = "time_budget_reached"
        print(str(exc), flush=True)
    except BaseException:
        status = "failed"
        raise
    finally:
        checkpoint(out / "latest.pt")
        write_json(out / "status.json", {"status": status, "last_step": step, "best_step": best_step,
                   "best_score": list(best_score) if best_score is not None else None,
                   "elapsed_seconds": time.time() - started,
                   "best_is_untrained_fallback": best_step == 0,
                   "note": "latest.pt is recovery weights; only best.pt passed a complete validation"})
        log.close()


if __name__ == "__main__":
    main()
