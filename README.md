# 📖 notes-gpt

Chat with your own PDFs — upload your notes, ask questions, get cited answers.

- Hybrid retrieval: BM25 + semantic search (`BAAI/bge-small-en-v1.5`), reranked with `BAAI/bge-reranker-base`
- Answers cite `[filename p.N]` so you can verify every claim, and say "I don't know" when your files don't have the answer
- Each user's uploads are session-only, in-memory, and never shared with other visitors
- Powered by Groq (`openai/gpt-oss-120b`) for fast streaming responses

## Live demo

- **Microsoft Azure Container Apps (primary):** https://notes-gpt.wittyflower-e8ca6384.centralindia.azurecontainerapps.io/
- **Streamlit Community Cloud:** https://notes-gpt.streamlit.app/

> The Azure app scales to zero when idle, so the first request after a quiet spell takes ~60–90s to cold-start and load the models. After that it's instant.

Refer above links for trying it by yourself...🙃🤞🏻

## How it works

| Step | What happens | Where |
|---|---|---|
| Parse | PyMuPDF reads each page; empty pages are skipped | `ingest.py` |
| Chunk | 800-character chunks with 100-character overlap, each tagged with file name and page number | `ingest.py` |
| Index | chunks are embedded with bge-small-en-v1.5 (normalized) into a ChromaDB collection that exists only for your browser session | `ingest.py`, `app.py` |
| Retrieve | BM25 top 10 + semantic top 10, merged and de-duplicated | `retrieve.py` |
| Rerank | a bge-reranker-base cross-encoder scores every candidate; the best 5 go to the model | `retrieve.py` |
| Answer | GPT-OSS 120B on Groq answers only from those 5 chunks, cites `[file p.N]`, and streams the reply | `chat.py` |

No LangChain or LlamaIndex in the app itself. Every step above is plain Python so each one can be inspected and changed.

## Run locally

```bash
git clone https://github.com/Siddhu-6/notes-gpt.git && cd notes-gpt
uv sync
export GROQ_API_KEY=your_key        # free key: https://console.groq.com/keys
uv run streamlit run notes_gpt/app.py
```

The app reads `GROQ_API_KEY` from the environment. On Streamlit Cloud, add it under **App settings → Secrets** as `GROQ_API_KEY = "..."`.

Or run the container:

```bash
docker build -t notes-gpt .
docker run -p 8080:8080 -e GROQ_API_KEY=your_key notes-gpt   # open http://localhost:8080
```

## Deploy

The app is containerized (`Dockerfile`) with a CPU-only image and both models baked in, so it starts offline with no runtime downloads.

- **Azure Container Apps** (what the live demo runs on): a GitHub Actions workflow (`.github/workflows/docker.yml`) builds the image and pushes it to GHCR, and Container Apps pulls that image. Full walkthrough in [AZURE.md](AZURE.md).
- **Google Cloud Run:** [DEPLOY.md](DEPLOY.md).

## CI/CD

On every push to `main`, GitHub Actions builds the Docker image and publishes it to the GitHub Container Registry (`ghcr.io/siddhu-6/notes-gpt:latest`). Redeploying is then just pulling the new image.

## Evaluation

`evals/` holds a RAGAS harness: 20 hand-written question/answer pairs (one per sample PDF), scored by `llama-3.1-8b-instant`, a different model from the one that writes the answers.

The published scores (faithfulness 0.95, answer relevancy 0.88, context precision 0.98) come from a **LlamaIndex dense-retrieval baseline** (`evals/llamaindex_version.py`), not from the app's hybrid pipeline. `evals/run_eval_app.py` runs the same questions through the app's own retrieval, reranker and model, so the two can be compared. Details in [evals/README.md](evals/README.md).

## NOTE
"notes-gpt" is just a Retrieval-Augmented Generation (RAG) project I built as an experiment to understand the full RAG pipeline hands-on, not just wiring together a framework, but implementing CHUNKING, HYBRID Retrieval, RERANKING, and Citation-grounded generation from scratch.
Each user's uploaded PDFs are indexed into an isolated, in-memory vector store scoped to their browser session — nothing is persisted or shared between users. Answers are generated only from retrieved context, with the model instructed to say "I don't know" rather than hallucinate when nothing relevant is found. Hope you try it...
