"""Shared bits for train.py / evaluate.py: candidate archs, manifest dataset, transforms."""
import csv
from pathlib import Path

import timm
import torch
from PIL import Image
from torchvision import transforms as T

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RUNS_DIR = Path(__file__).resolve().parents[1] / "runs"
ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
IMG_SIZE = 224

# IMPLEMENTATION.md §6.2
ARCHS = {
    "convnext_tiny": "convnext_tiny.fb_in22k_ft_in1k",
    "efficientnetv2_s": "tf_efficientnetv2_s.in21k_ft_in1k",
}


def read_manifest(data_dir: Path) -> tuple[list[dict], list[str]]:
    with open(data_dir / "manifest.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    labels = sorted({r["label"] for r in rows})
    return rows, labels


def create_model(arch: str, num_classes: int, pretrained: bool = True) -> torch.nn.Module:
    return timm.create_model(ARCHS[arch], pretrained=pretrained, num_classes=num_classes)


def norm_stats(model: torch.nn.Module) -> tuple[list[float], list[float]]:
    cfg = timm.data.resolve_data_config(model=model)
    return list(cfg["mean"]), list(cfg["std"])


def train_transform(mean, std):
    return T.Compose([
        T.RandomResizedCrop(IMG_SIZE, scale=(0.6, 1.0)),
        T.RandomHorizontalFlip(),
        T.ColorJitter(0.2, 0.2, 0.2),
        T.RandAugment(num_ops=2, magnitude=9),
        T.ToTensor(),
        T.Normalize(mean, std),
    ])


def eval_transform(mean, std):
    # Must match the OpenCV preprocessing in model/service: short side 256, centre crop 224.
    return T.Compose([T.Resize(256), T.CenterCrop(IMG_SIZE), T.ToTensor(), T.Normalize(mean, std)])


class ManifestDataset(torch.utils.data.Dataset):
    def __init__(self, data_dir: Path, rows: list[dict], labels: list[str], split: str, transform):
        index = {l: i for i, l in enumerate(labels)}
        self.items = [(data_dir / r["path"], index[r["label"]]) for r in rows if r["split"] == split]
        self.transform = transform

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, target = self.items[i]
        with Image.open(path) as im:
            return self.transform(im.convert("RGB")), target
