# ---------------------------------------------------------------------------
# Image Caption Generator - API + frontend container
#
# This image runs the FastAPI app (api/main.py). The same app also serves the
# static frontend (frontend/index.html) at "/", so everything is one container
# on one port (8000): open http://localhost:8000 and you get the web UI, and
# the UI calls the API on the same origin.
# ---------------------------------------------------------------------------

# Small official Python image. Matches the project's Python 3.10 / TF 2.18.0.
FROM python:3.10-slim

# - PYTHONUNBUFFERED: logs appear immediately in `docker logs` (no buffering).
# - PYTHONDONTWRITEBYTECODE: don't create .pyc files inside the container.
# - PYTHONPATH=/app: so "api" and "src" import as packages (uvicorn api.main:app).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# All application code lives in /app inside the container.
WORKDIR /app

# TensorFlow's CPU build needs the OpenMP runtime (libgomp1) at import time.
# Without it, `import tensorflow` fails on the slim image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first, in their own layer. If only the app code
# changes later, Docker can reuse this cached layer and skip reinstalling.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Pre-download the VGG16 ImageNet weights into the image. build_feature_model()
# calls VGG16(), which would otherwise download ~500 MB on the FIRST caption
# request. Baking the weights in makes the container work offline and keeps the
# first request fast.
RUN python -c "from tensorflow.keras.applications.vgg16 import VGG16; VGG16()"

# Copy the rest of the project: src/, api/, frontend/, and the trained
# artifacts (model.h5 + the .pkl files). The big dataset and training-only
# files are kept out by .dockerignore.
COPY . .

# uvicorn/FastAPI listens on port 8000.
EXPOSE 8000

# Start the API. host 0.0.0.0 makes it reachable from outside the container.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
