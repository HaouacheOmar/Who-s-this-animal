"""gRPC client for the model service (proto/classifier.proto)."""
import grpc
from django.conf import settings

from . import classifier_pb2 as pb
from . import classifier_pb2_grpc as pb_grpc


class ModelUnavailable(Exception):
    pass


_channel = None


def classify(image: bytes, top_k: int = 3) -> pb.ClassifyReply:
    global _channel
    if _channel is None:
        _channel = grpc.insecure_channel(settings.MODEL_GRPC_ADDR,
                                         options=[("grpc.max_send_message_length", 12 * 2**20)])
    try:
        return pb_grpc.BreedClassifierStub(_channel).Classify(pb.ClassifyRequest(image=image, top_k=top_k), timeout=10)
    except grpc.RpcError as e:
        raise ModelUnavailable(e.code().name) from e
