# Build from the repository root:  docker build -f backend/Dockerfile -t medical-ai-backend .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1) Dependencies first, so Docker caches this slow layer until requirements.txt changes.
#    CPU-only PyTorch keeps the image far smaller than the default (CUDA) build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

# 2) Download the embedding model once at build time, so containers start fast
#    and do not need internet access to huggingface.co.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# 3) Application code and knowledge files (config.py expects data/ next to backend/).
COPY backend/ backend/
COPY data/ data/

WORKDIR /app/backend

EXPOSE 8000

# 0.0.0.0 makes the API reachable from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
