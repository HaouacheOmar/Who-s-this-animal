FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app/server
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto /app/proto
COPY server .
# Stubs are regenerated at start because ../server is bind-mounted over /app/server in dev.
CMD ["sh", "-c", "python -m grpc_tools.protoc -Iscans=../proto --python_out=. --grpc_python_out=. scans/classifier.proto && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
