"""One-server timebox. Stops subprocesses, NOT the cloud rental or its billing."""
import argparse
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .common import read_json, write_json


def make_budget(start_iso, hourly_price, total=200.0, reserve=20.0):
    start = dt.datetime.fromisoformat(start_iso)
    if start.tzinfo is None:
        raise ValueError("Rental start must include timezone, e.g. 2026-10-15T10:00:00+08:00")
    if not 0 < hourly_price or not 0 <= reserve < total:
        raise ValueError("Invalid price / budget")
    rental_hours = min(24.0, (total - reserve) / hourly_price)
    if rental_hours <= 1:
        raise ValueError("Budget cannot accommodate one-hour shutdown/export reserve")
    return {"rental_start": start.timestamp(), "hourly_price": hourly_price,
            "total_cny": total, "non_gpu_reserve_cny": reserve,
            "latest_shutdown_epoch": start.timestamp() + rental_hours * 3600,
            "work_deadline_epoch": start.timestamp() + (rental_hours - 1) * 3600,
            "rental_hours_cap": rental_hours}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--hourly-price", type=float, required=True, help="Actual total GPU-server RMB/hour")
    p.add_argument("--rental-start", required=True, help="Actual billing start, ISO8601 with timezone")
    p.add_argument("--reserve-cny", type=float, default=20)
    p.add_argument("--skip-m2", action="store_true", help="Reduced budget: M1 plus held-out evaluation")
    p.add_argument("--skip-second-seed", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    budget = make_budget(a.rental_start, a.hourly_price, reserve=a.reserve_cny)
    out = Path(a.out).resolve()
    if not a.dry_run:
        out.mkdir(parents=True, exist_ok=True)
        ledger = out / "budget.json"
        if ledger.exists() and read_json(ledger) != budget:
            raise ValueError("Existing budget ledger cannot be reset to extend the rental")
        write_json(ledger, budget)
    for name in ("work_deadline_epoch", "latest_shutdown_epoch"):
        print(name, dt.datetime.fromtimestamp(budget[name]).astimezone().isoformat())
    print("IMPORTANT: automatic subprocess stop does not stop cloud billing. Set a provider shutdown timer.")
    common = ["--manifest", str(Path(a.manifest).resolve()), "--cache", str(Path(a.cache).resolve())]

    def run(name, module, args, hours):
        command = [sys.executable, "-m", f"tsft.{module}", *args, "--hours", str(hours)]
        print(name, json.dumps(command, ensure_ascii=False), flush=True)
        if a.dry_run:
            return
        marker = out / f"{name}.done.json"
        if marker.exists():
            print("Already completed:", name)
            return
        remaining = budget["work_deadline_epoch"] - time.time()
        if remaining < min(hours * 3600, 900):
            raise TimeoutError("Insufficient remaining rental time; export results and shut down")
        env = os.environ.copy()
        env["TSFT_DEADLINE"] = str(budget["work_deadline_epoch"])
        # Child's own timer saves latest weights; outer timeout is a fallback, including startup.
        timeout = min(hours * 3600 + 120, remaining)
        with open(out / f"{name}.log", "w") as log:
            proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = proc.wait(timeout=timeout)
            except BaseException:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                raise
        if code:
            raise RuntimeError(f"{name} failed ({code}); inspect {name}.log; billing may still be running")
        write_json(marker, {"finished_epoch": time.time(), "command": command})

    run("cache", "cache", ["--model", str(Path(a.model).resolve()), "--manifest", str(Path(a.manifest).resolve()),
                            "--out", str(Path(a.cache).resolve())], 3)
    run("M1", "train", common + ["--out", str(out / "M1"), "--area-weight", "0.0"], 3)
    active = [("M1", 0.0)]
    skipped = {}
    remaining_hours = lambda: (budget["work_deadline_epoch"] - time.time()) / 3600
    # Preserve final evaluation time before launching optional training.
    enough_m2 = a.dry_run or (out / "M2.done.json").exists() or remaining_hours() >= 6.25
    if not a.skip_m2 and enough_m2:
        run("M2", "train", common + ["--out", str(out / "M2"), "--area-weight", "0.1"], 3)
        active.append(("M2", 0.1))
    else:
        skipped["M2"] = "user request or preserve held-out evaluation time"
    # Choose the second-seed configuration by validation only, before opening test labels.
    chosen, area = "M1", 0.0
    if not a.dry_run:
        candidates = [(read_json(out / name / "status.json"), name, w) for name, w in active]
        if any(c[0]["best_score"] is None for c in candidates):
            raise RuntimeError("No completed validation: do not proceed to held-out evaluation")
        candidates.sort(key=lambda c: tuple(c[0]["best_score"]), reverse=True)
        _, chosen, area = candidates[0]
    eval_names = ["R1"] + [name for name, _ in active]
    enough_seed = a.dry_run or (out / "second_seed.done.json").exists() or remaining_hours() >= 3 + len(eval_names) + 1 + .25
    if not a.skip_second_seed and enough_seed:
        run("second_seed", "train", common + ["--out", str(out / "second_seed"), "--area-weight", str(area),
                                               "--seed", "20261016"], 3)
        eval_names.append("second_seed")
    else:
        skipped["second_seed"] = "user request or preserve held-out evaluation time"
    if not a.dry_run:
        write_json(out / "selection_before_test.json", {"chosen": chosen, "area_weight": area,
                  "basis": "validation micro IoU, then area MAE", "frozen_epoch": time.time(),
                  "evaluated_models": eval_names, "skipped": skipped})
    print("Skipped:", skipped, flush=True)
    for split in ("test", "bolivia"):
        for name in eval_names:
            args = common + ["--out", str(out / "evaluation" / f"{split}_{name}"), "--split", split,
                             "--export-masks"]
            if name != "R1":
                args += ["--checkpoint", str(out / name / "best.pt")]
            run(f"eval_{split}_{name}", "evaluate", args, 0.5)
    print("Finished. Download outputs, then STOP/RELEASE the GPU instance in the provider console.")


if __name__ == "__main__":
    main()
