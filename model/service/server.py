"""gRPC BreedClassifier: OpenCV quality checks + ONNX inference (IMPLEMENTATION.md §5).

Env: MODEL_DIR (model.onnx + meta.json), PORT (50051), BLUR_THRESHOLD (60), DARK_THRESHOLD (40),
     REJECT_THRESHOLD / SURE_THRESHOLD (override the values picked during evaluation).
"""
import json
import os
from concurrent import futures
from pathlib import Path

import cv2
import grpc
import numpy as np
import onnxruntime as ort
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

import classifier_pb2 as pb
import classifier_pb2_grpc as pb_grpc

MIN_SIDE = 224
BLUR_THRESHOLD = float(os.environ.get("BLUR_THRESHOLD", 60))
DARK_THRESHOLD = float(os.environ.get("DARK_THRESHOLD", 40))


def preprocess(data: bytes, mean, std, size: int = 224) -> tuple[np.ndarray | None, str]:
    """Bytes -> (NCHW float32 batch, "") or (None, reject_reason)."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)  # applies EXIF orientation
    if img is None:
        return None, "unreadable"
    h, w = img.shape[:2]
    if min(h, w) < MIN_SIDE:
        return None, "too_small"
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if gray.mean() < DARK_THRESHOLD:
        return None, "too_dark"
    if cv2.Laplacian(gray, cv2.CV_64F).var() < BLUR_THRESHOLD:
        return None, "blurry"

    # Same as training eval_transform: short side 256, centre crop 224.
    scale = 256 / min(h, w)
    img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    top, left = (h - size) // 2, (w - size) // 2
    img = img[top:top + size, left:left + size]
    x = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = (x - np.array(mean, np.float32)) / np.array(std, np.float32)
    return x.transpose(2, 0, 1)[None], ""


def decide(probs: np.ndarray, reject: float, sure: float) -> tuple[bool, bool]:
    """(recognized, possible_mix) from sorted-descending probabilities (IMPLEMENTATION.md §5.3)."""
    top1, top2 = probs[0], probs[1]
    recognized = top1 >= reject
    return recognized, bool(recognized and top1 < sure and top1 + top2 >= 0.75)


class Classifier(pb_grpc.BreedClassifierServicer):
    def __init__(self, model_dir: Path):
        self.meta = json.loads((model_dir / "meta.json").read_text())
        self.session = ort.InferenceSession(str(model_dir / "model.onnx"), providers=["CPUExecutionProvider"])
        self.labels = self.meta["labels"]
        self.reject = float(os.environ.get("REJECT_THRESHOLD", self.meta["reject_threshold"]))
        self.sure = float(os.environ.get("SURE_THRESHOLD", self.meta["sure_threshold"]))

    def Classify(self, request, context):
        version = self.meta.get("model_version", "")
        x, reason = preprocess(request.image, self.meta["mean"], self.meta["std"], self.meta["input_size"])
        if x is None:
            return pb.ClassifyReply(recognized=False, reject_reason=reason, model_version=version)

        logits = self.session.run(None, {"input": x})[0][0]
        probs = np.exp(logits - logits.max())
        probs /= probs.sum()
        order = np.argsort(-probs)[: max(request.top_k or 3, 2)]
        recognized, mix = decide(probs[order], self.reject, self.sure)
        return pb.ClassifyReply(
            recognized=recognized,
            possible_mix=mix,
            reject_reason="" if recognized else "low_confidence",
            model_version=version,
            predictions=[pb.Prediction(label=self.labels[i], confidence=float(probs[i])) for i in order],
        )


def serve():
    model_dir = Path(os.environ.get("MODEL_DIR", Path(__file__).resolve().parents[1] / "artifacts"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4),
                         options=[("grpc.max_receive_message_length", 12 * 2**20)])  # 10 MB upload + slack
    pb_grpc.add_BreedClassifierServicer_to_server(Classifier(model_dir), server)
    health_servicer = health.HealthServicer()
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    port = os.environ.get("PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"BreedClassifier listening on :{port}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
