FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY model/service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto /app/proto
COPY model/service .
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/classifier.proto
EXPOSE 50051
CMD ["python", "server.py"]
