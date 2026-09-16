FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FACE_PROVIDER=production \
    FACE_DETECTOR=yunet \
    FACE_MODEL_PATH=/app/models/face_recognition_sface_2021dec.onnx \
    FACE_DETECTOR_MODEL_PATH=/app/models/face_detection_yunet_2023mar.onnx

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl ca-certificates libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY scripts/provision_face_models.sh /usr/local/bin/provision-face-models
RUN chmod +x /usr/local/bin/provision-face-models \
    && pip install --no-cache-dir . \
    && provision-face-models /app/models

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
