# notes-gpt: Streamlit app for Google Cloud Run (or any Docker host).
# The two models are downloaded at build time so a cold start doesn't fetch 1+ GB.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# CPU-only PyTorch: the default PyPI wheel bundles CUDA and makes the image several GB larger.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Only what the app imports (pyproject.toml also lists LangChain, which the app doesn't use).
RUN pip install \
    "chromadb>=1.5.9" \
    "openai>=1.0.0" \
    "pymupdf>=1.24.0" \
    "rank-bm25>=0.2.2" \
    "sentence-transformers>=3.0.0" \
    "streamlit>=1.40.0"

# Bake the embedder and reranker into the image.
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-small-en-v1.5'); CrossEncoder('BAAI/bge-reranker-base')"

# Models are in the image now; never reach for the network at runtime.
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

COPY notes_gpt ./notes_gpt

# Non-root user. The app only reads /app and /models, so no chown (which would copy the 1.2 GB model layer).
RUN useradd -m app
USER app

# Run from notes_gpt/ so the app's own imports and .streamlit/config.toml are picked up.
WORKDIR /app/notes_gpt
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
