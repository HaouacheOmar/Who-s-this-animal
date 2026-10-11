"""Evaluate a trained candidate on the test split, pick thresholds on val, export + verify ONNX, time CPU latency.

Usage: python model/training/evaluate.py --arch convnext_tiny [--ood-dir DIR]
Output: model/runs/<arch>/model.onnx and metrics.json (read by compare.py)
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from PIL import Image
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader

from common import (ARCHS, DEFAULT_DATA_DIR, IMG_SIZE, RUNS_DIR, ManifestDataset, create_model, eval_transform,
                    read_manifest)


@torch.no_grad()
def predict(model, loader) -> tuple[np.ndarray, np.ndarray]:
    probs, targets = [], []
    for x, y in loader:
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(x.cuda(non_blocking=True))
        probs.append(logits.float().softmax(1).cpu().numpy())
        targets.append(y.numpy())
    return np.concatenate(probs), np.concatenate(targets)


def thresholds(probs: np.ndarray, targets: np.ndarray) -> tuple[float, float]:
    """IMPLEMENTATION.md §6.4: reject keeps >= 95% of correct predictions; sure = lowest conf with precision >= 97%."""
    conf, pred = probs.max(1), probs.argmax(1)
    correct = pred == targets
    reject = float(np.percentile(conf[correct], 5))
    order = np.argsort(-conf)
    precision = np.cumsum(correct[order]) / np.arange(1, len(order) + 1)
    ok = np.where(precision >= 0.97)[0]
    sure = float(conf[order][ok[-1]]) if len(ok) else 0.99
    return reject, max(sure, reject)


def ood_reject_rate(model, ood_dir: Path, transform, reject: float) -> float:
    paths = [p for p in ood_dir.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    rejected = 0
    with torch.no_grad():
        for p in paths:
            with Image.open(p) as im:
                x = transform(im.convert("RGB")).unsqueeze(0).cuda()
            rejected += model(x).softmax(1).max().item() < reject
    return rejected / max(len(paths), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", choices=ARCHS, required=True)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    ap.add_argument("--ood-dir", type=Path, help="folder of non-pet images, to report the OOD reject rate")
    args = ap.parse_args()

    run = RUNS_DIR / args.arch
    ckpt = torch.load(run / "best.pt", map_location="cpu", weights_only=True)
    labels, mean, std = ckpt["labels"], ckpt["mean"], ckpt["std"]
    model = create_model(args.arch, len(labels), pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model = model.cuda().eval()

    rows, _ = read_manifest(args.data_dir)
    tf = eval_transform(mean, std)
    loader = lambda split: DataLoader(ManifestDataset(args.data_dir, rows, labels, split, tf),
                                      batch_size=64, num_workers=6)

    val_p, val_y = predict(model, loader("val"))
    reject, sure = thresholds(val_p, val_y)

    test_p, test_y = predict(model, loader("test"))
    top5 = np.argsort(-test_p, 1)[:, :5]
    per_class = f1_score(test_y, test_p.argmax(1), average=None, labels=range(len(labels)))
    worst = np.argsort(per_class)[:5]
    metrics = {
        "arch": args.arch,
        "top1": float((test_p.argmax(1) == test_y).mean()),
        "top5": float((top5 == test_y[:, None]).any(1).mean()),
        "macro_f1": float(per_class.mean()),
        "worst5": {labels[i]: round(float(per_class[i]), 3) for i in worst},
        "reject_threshold": round(reject, 3),
        "sure_threshold": round(sure, 3),
    }
    if args.ood_dir:
        metrics["ood_reject_rate"] = ood_reject_rate(model, args.ood_dir, tf, reject)

    # ONNX export (fp32, dynamic batch) + parity check against PyTorch.
    model = model.float().cpu()
    dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)
    onnx_path = run / "model.onnx"
    torch.onnx.export(model, dummy, onnx_path, opset_version=17, input_names=["input"], output_names=["logits"],
                      dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}}, dynamo=False)
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    with torch.no_grad():
        ref = model(dummy).numpy()
    out = sess.run(None, {"input": dummy.numpy()})[0]
    metrics["onnx_max_abs_diff"] = float(np.abs(ref - out).max())
    assert metrics["onnx_max_abs_diff"] < 1e-3, metrics["onnx_max_abs_diff"]

    x = dummy.numpy()
    for _ in range(5):
        sess.run(None, {"input": x})
    t0 = time.perf_counter()
    for _ in range(50):
        sess.run(None, {"input": x})
    metrics["cpu_latency_ms"] = round((time.perf_counter() - t0) / 50 * 1000, 1)
    metrics["onnx_size_mb"] = round(onnx_path.stat().st_size / 2**20, 1)

    meta = {"arch": args.arch, "labels": labels, "mean": mean, "std": std, "input_size": IMG_SIZE,
            "reject_threshold": metrics["reject_threshold"], "sure_threshold": metrics["sure_threshold"]}
    (run / "meta.json").write_text(json.dumps(meta, indent=1))
    (run / "metrics.json").write_text(json.dumps(metrics, indent=1))
    print(json.dumps(metrics, indent=1))


if __name__ == "__main__":
    main()
