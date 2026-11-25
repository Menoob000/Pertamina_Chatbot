# Dockerfile khusus Hugging Face Spaces (SDK Docker).
# Di-upload sebagai `Dockerfile` di root Space oleh scripts/deploy_hf_space.py.
# Perbedaan dengan Dockerfile.backend: container berjalan sebagai user non-root UID 1000
# (aturan HF Spaces), jadi folder yang ditulis saat runtime harus milik user tersebut.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache

# LibreOffice  -> RKS preview.pdf (DOCX -> PDF) di Linux
# libgl1/glib  -> dependensi native docling/opencv
# curl         -> healthcheck
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui fonts-dejavu-core fonts-liberation \
        libgl1 libglib2.0-0 curl \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user

WORKDIR /app

# torch + torchvision CPU dipasang BERSAMA dari index CPU agar versinya cocok. torchvision dari PyPI
# yang tidak cocok membuat transformers/sentence_transformers gagal import ("torchvision::nms does not exist").
# Baris python -c di akhir menggagalkan build bila import embedding rusak.
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv \
 && uv pip install --system --no-cache --index-url https://download.pytorch.org/whl/cpu torch torchvision \
 && uv pip install --system --no-cache -r pyproject.toml \
 && python -c "import torch, torchvision, sentence_transformers; print('torch', torch.__version__, 'torchvision', torchvision.__version__)"

# Model embedding dimuat dengan local_files_only=True (rag/vector_store.py), jadi harus ada di image.
# HF Spaces meneruskan Space variable EMBEDDING_MODEL sebagai build arg.
ARG EMBEDDING_MODEL=sentence-transformers/all-minilm-l6-v2
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('${EMBEDDING_MODEL}')" \
 && chown -R user:user /opt/hf-cache

COPY --chown=user:user . .
RUN mkdir -p /app/output /app/data && chown -R user:user /app

USER user
ENV HOME=/home/user \
    FASTAPI_HOST=0.0.0.0 \
    FASTAPI_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# Satu worker: memori percakapan LangGraph (MemorySaver) disimpan in-process.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-keep-alive", "75"]
