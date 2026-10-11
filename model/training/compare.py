"""Apply the decision rule (IMPLEMENTATION.md §6.4), print the comparison table, install the winner.

Usage: python model/training/compare.py
Output: model/artifacts/model.onnx + meta.json (what the gRPC service loads)
"""
import json
import shutil
import subprocess
from datetime import date

from common import ARCHS, ARTIFACTS_DIR, RUNS_DIR


def pick(a: dict, b: dict) -> dict:
    """Higher macro-F1 wins, unless within 1 point: then the faster one on CPU."""
    if abs(a["macro_f1"] - b["macro_f1"]) < 0.01:
        return min(a, b, key=lambda m: m["cpu_latency_ms"])
    return max(a, b, key=lambda m: m["macro_f1"])


def main():
    runs = {arch: json.loads((RUNS_DIR / arch / "metrics.json").read_text()) for arch in ARCHS}
    rows = [("Top-1", "top1", "{:.1%}"), ("Top-5", "top5", "{:.1%}"), ("Macro-F1", "macro_f1", "{:.3f}"),
            ("CPU latency (ms)", "cpu_latency_ms", "{}"), ("ONNX size (MB)", "onnx_size_mb", "{}"),
            ("Reject threshold", "reject_threshold", "{}"), ("Sure threshold", "sure_threshold", "{}")]
    print("| Metric | " + " | ".join(runs) + " |\n|---|" + "---|" * len(runs))
    for name, key, fmt in rows:
        print(f"| {name} | " + " | ".join(fmt.format(m[key]) for m in runs.values()) + " |")

    winner = pick(*runs.values())["arch"]
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True,
                                      stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        sha = "nogit"
    meta = json.loads((RUNS_DIR / winner / "meta.json").read_text())
    meta["model_version"] = f"{winner}-{date.today():%Y%m%d}-{sha}"

    ARTIFACTS_DIR.mkdir(exist_ok=True)
    shutil.copy(RUNS_DIR / winner / "model.onnx", ARTIFACTS_DIR / "model.onnx")
    (ARTIFACTS_DIR / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"\nwinner: {winner} -> {ARTIFACTS_DIR} ({meta['model_version']})")


if __name__ == "__main__":
    assert pick({"arch": "a", "macro_f1": 0.900, "cpu_latency_ms": 50},
                {"arch": "b", "macro_f1": 0.905, "cpu_latency_ms": 20})["arch"] == "b"
    assert pick({"arch": "a", "macro_f1": 0.92, "cpu_latency_ms": 50},
                {"arch": "b", "macro_f1": 0.90, "cpu_latency_ms": 20})["arch"] == "a"
    main()
