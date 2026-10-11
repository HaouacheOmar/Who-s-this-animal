import cv2
import numpy as np

from server import decide, preprocess

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def encode(img: np.ndarray) -> bytes:
    return cv2.imencode(".jpg", img)[1].tobytes()


def noise(h, w, low=0, high=255):
    return np.random.default_rng(0).integers(low, high, (h, w, 3), dtype=np.uint8)


def test_rejects():
    assert preprocess(b"not an image", MEAN, STD) == (None, "unreadable")
    assert preprocess(encode(noise(100, 300)), MEAN, STD) == (None, "too_small")
    assert preprocess(encode(noise(400, 400, 0, 30)), MEAN, STD) == (None, "too_dark")
    assert preprocess(encode(np.full((400, 400, 3), 128, np.uint8)), MEAN, STD) == (None, "blurry")


def test_accepts_and_shapes():
    x, reason = preprocess(encode(noise(480, 640)), MEAN, STD)
    assert reason == "" and x.shape == (1, 3, 224, 224) and x.dtype == np.float32


def test_decide():
    assert decide(np.array([0.95, 0.03]), reject=0.4, sure=0.8) == (True, False)
    assert decide(np.array([0.50, 0.30]), reject=0.4, sure=0.8) == (True, True)
    assert decide(np.array([0.50, 0.10]), reject=0.4, sure=0.8) == (True, False)
    assert decide(np.array([0.30, 0.25]), reject=0.4, sure=0.8) == (False, False)
