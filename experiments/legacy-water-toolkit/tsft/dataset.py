import numpy as np
import torch

from .common import load_manifest, load_tensor_file, read_json, sha256


class CachedDataset(torch.utils.data.Dataset):
    def __init__(self, manifest, cache, split, verify_hashes=True):
        from pathlib import Path
        self.cache = Path(cache)
        self.index = read_json(self.cache / "index.json")
        if not self.index["complete"]:
            raise ValueError("Incomplete / pilot cache: finish caching all declared samples first")
        if self.index["metadata"]["manifest_sha256"] != sha256(manifest):
            raise ValueError("Manifest mismatch: stale feature cache")
        if sha256(self.cache / "base_head.pt") != self.index["base_sha256"]:
            raise ValueError("Base head changed")
        manifest_obj = load_manifest(manifest)
        if manifest_obj.get("dataset") == "Sen1Floods11-v1.1-handlabeled":
            from .data import official_rows
            expected = {r["id"]: r["split"] for r in official_rows()}
            declared = manifest_obj["samples"] + manifest_obj.get("excluded", [])
            if len(declared) != len(expected) or {r["id"] for r in declared} != set(expected):
                raise ValueError("Official manifest is incomplete; do not silently change the sample population")
            if any(expected[r["id"]] != r["split"] for r in declared):
                raise ValueError("Official split leakage / relabeling")
        self.rows = [r for r in manifest_obj["samples"] if r["split"] == split]
        if not self.rows:
            raise ValueError(f"Empty split: {split}")
        for row in self.rows:
            entry = self.index["features"][row["id"]]
            if entry["split"] != split:
                raise ValueError("Split changed in cache")
            if verify_hashes:
                if sha256(self.cache / entry["file"]) != entry["sha256"]:
                    raise ValueError(f"Corrupt feature: {row['id']}")
                if sha256(row["target"]) != row["target_sha256"]:
                    raise ValueError(f"Target changed: {row['id']}")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        row = self.rows[i]
        f = load_tensor_file(self.cache / self.index["features"][row["id"]]["file"])
        if f["id"] != row["id"] or f["fingerprint"] != self.index["fingerprint"]:
            raise ValueError("Feature identity mismatch")
        with np.load(row["target"], allow_pickle=False) as z:
            target = {k: torch.from_numpy(z[k].copy())[None, None] for k in ("label", "valid", "area_m2")}
        return f, target, row


def to_device(feature, target, device):
    feature = {"raw_fpn": [t.to(device) for t in feature["raw_fpn"]],
               "seg_hidden": feature["seg_hidden"].to(device)}
    if str(device) == "cpu":
        feature["raw_fpn"] = [t.float() for t in feature["raw_fpn"]]
    return feature, {k: v.to(device) for k, v in target.items()}
