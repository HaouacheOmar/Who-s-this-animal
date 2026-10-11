"""Fine-tune one candidate on the manifest (IMPLEMENTATION.md §6.3). Keeps the best checkpoint by val top-1.

Usage: python model/training/train.py --arch convnext_tiny [--epochs 15] [--batch 32]
Output: model/runs/<arch>/best.pt
"""
import argparse
import math
import time
from collections import Counter
from pathlib import Path

import torch
from torch.utils.data import DataLoader, WeightedRandomSampler

from common import (ARCHS, DEFAULT_DATA_DIR, RUNS_DIR, ManifestDataset, create_model, eval_transform,
                    norm_stats, read_manifest, train_transform)


@torch.no_grad()
def accuracy(model, loader, device) -> float:
    model.eval()
    correct = total = 0
    for x, y in loader:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            correct += (model(x).argmax(1) == y).sum().item()
        total += len(y)
    return correct / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", choices=ARCHS, required=True)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    device = "cuda"
    torch.manual_seed(42)
    rows, labels = read_manifest(args.data_dir)
    model = create_model(args.arch, len(labels)).to(device)
    mean, std = norm_stats(model)

    train_ds = ManifestDataset(args.data_dir, rows, labels, "train", train_transform(mean, std))
    val_ds = ManifestDataset(args.data_dir, rows, labels, "val", eval_transform(mean, std))

    # Class-balanced sampling: birds have far fewer images than the dog breeds.
    counts = Counter(t for _, t in train_ds.items)
    weights = [1.0 / counts[t] for _, t in train_ds.items]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)
    loader_kw = dict(batch_size=args.batch, num_workers=args.workers, pin_memory=True, persistent_workers=True)
    train_dl = DataLoader(train_ds, sampler=sampler, drop_last=True, **loader_kw)
    val_dl = DataLoader(val_ds, **loader_kw)

    head = list(model.get_classifier().parameters())
    head_ids = {id(p) for p in head}
    opt = torch.optim.AdamW([
        {"params": [p for p in model.parameters() if id(p) not in head_ids], "lr": 1e-4},
        {"params": head, "lr": 3e-4},
    ], weight_decay=0.05)
    steps = args.epochs * len(train_dl)
    warmup = len(train_dl)  # 1 epoch
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warmup if s < warmup else 0.5 * (1 + math.cos(math.pi * (s - warmup) / (steps - warmup))))
    loss_fn = torch.nn.CrossEntropyLoss(label_smoothing=0.1)

    out = RUNS_DIR / args.arch
    out.mkdir(parents=True, exist_ok=True)
    best = 0.0
    print(f"{args.arch}: {len(train_ds)} train / {len(val_ds)} val, {len(labels)} classes")
    for epoch in range(args.epochs):
        model.train()
        t0, running = time.time(), 0.0
        for i, (x, y) in enumerate(train_dl):
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = loss_fn(model(x), y)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            running += loss.item()
            if (i + 1) % 50 == 0:
                done = (i + 1) / len(train_dl)
                eta = (time.time() - t0) / done * (1 - done)
                print(f"  epoch {epoch + 1} [{i + 1}/{len(train_dl)}] loss {running / (i + 1):.3f} "
                      f"{(i + 1) * args.batch / (time.time() - t0):.0f} img/s, epoch ETA {eta / 60:.1f} min", flush=True)
        acc = accuracy(model, val_dl, device)
        print(f"epoch {epoch + 1}/{args.epochs} loss {running / len(train_dl):.3f} val_top1 {acc:.4f} "
              f"({time.time() - t0:.0f}s)", flush=True)
        if acc > best:
            best = acc
            torch.save({"arch": args.arch, "labels": labels, "mean": mean, "std": std,
                        "state_dict": model.state_dict(), "val_top1": acc, "epoch": epoch + 1}, out / "best.pt")
    print(f"best val top-1 {best:.4f} -> {out / 'best.pt'}")


if __name__ == "__main__":
    main()
