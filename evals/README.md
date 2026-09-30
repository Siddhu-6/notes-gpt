# RAG Evaluation — notes-gpt

Evaluation of retrieval and answer quality with [RAGAS](https://github.com/explodinggradients/ragas) on a 20-question hand-written eval set covering all 20 sample PDFs.

## Results: LlamaIndex dense-retrieval baseline

| Metric | Score | What it measures |
|---|---|---|
| Faithfulness | 0.95 | Are answers grounded in the retrieved context (no hallucination)? |
| Answer Relevancy | 0.88 | Do answers actually address the question asked? |
| Context Precision | 0.98 | Did retrieval find the right chunks? |

These numbers are for the **baseline** in `llamaindex_version.py`: dense retrieval only (bge-small-en-v1.5) with `llama-3.3-70b-versatile`. They are **not** the app's pipeline, which adds BM25, a cross-encoder reranker and GPT-OSS 120B. Faithfulness is averaged over 19 questions because the judge returned no score for one.

## Results: app pipeline

Not run yet. See "Evaluate the app pipeline" below, then fill this table in.

| Metric | Baseline | App pipeline |
|---|---|---|
| Faithfulness | 0.95 | – |
| Answer Relevancy | 0.88 | – |
| Context Precision | 0.98 | – |

## Methodology

- **Baseline answers:** `llamaindex_version.py`, a LlamaIndex `VectorStoreIndex` over the sample PDFs with `BAAI/bge-small-en-v1.5` embeddings and Groq's `llama-3.3-70b-versatile`.
- **App answers:** `run_eval_app.py` imports the app's own `ingest`, `retrieve` and `chat` modules, so it uses exactly what the Streamlit app uses: 800/100 chunking, BM25 + semantic retrieval, bge-reranker-base, and `openai/gpt-oss-120b`.
- **Judge model:** Groq's `llama-3.1-8b-instant`, deliberately different from the answer models to avoid self-evaluation bias.
- **Embeddings for scoring:** `BAAI/bge-small-en-v1.5`, run locally, no OpenAI dependency.

## Files

- `eval_questions.json` — 20 hand-written question / ground-truth pairs, one per source PDF
- `llamaindex_version.py` — the baseline pipeline
- `run_eval.py` — runs every question through the baseline, saves answers + contexts to `eval_results.json`
- `run_eval_app.py` — runs every question through the app pipeline, saves to `eval_results_app.json`
- `score.py` — RAGAS scoring; takes an input results file and an output scores file
- `scores.json` — per-question baseline scores

## Reproduce

Eval-only dependencies (not needed to run the app):

```bash
uv pip install ragas datasets langchain-openai langchain-huggingface \
  llama-index llama-index-llms-groq llama-index-embeddings-huggingface
export GROQ_API_KEY=your_key
```

Put the 20 sample PDFs in `notes_gpt/data/`, then:

```bash
# baseline
uv run python evals/run_eval.py
uv run python evals/score.py evals/eval_results.json evals/scores.json

# app pipeline
uv run python evals/run_eval_app.py
uv run python evals/score.py evals/eval_results_app.json evals/scores_app.json
```
