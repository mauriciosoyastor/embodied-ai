# Backend webcam dev: FastAPI :8000 (YOLO ONNX + MediaPipe + voz/Ollama).
# Modelos y keys NO se bakean: modelos van en volumen, keys por env_file.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2

# libgl/libglib: opencv + mediapipe en slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Deps backend (ver plataforma/webcam/backend/pyproject.toml) + openai/dotenv
# que VozHandler usa vía fase-1/gemini_client.
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    "onnxruntime==1.29.*" \
    "opencv-python==4.14.*" \
    "mediapipe==1.0.1" \
    numpy \
    "pydantic>=2" \
    openai \
    python-dotenv

COPY plataforma/ /app/plataforma/
COPY fase-1/gemini_client.py /app/fase-1/gemini_client.py

EXPOSE 8000

# Descarga modelos si faltan (idempotente, volumen persiste) y levanta API.
CMD ["sh", "-c", "python plataforma/webcam/backend/descargar_modelos.py --skip-frontend || true; exec uvicorn plataforma.webcam.backend.app:app --host 0.0.0.0 --port 8000"]
