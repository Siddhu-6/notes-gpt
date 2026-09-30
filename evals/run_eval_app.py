"""Run the eval questions through the app's own pipeline: 800/100 chunking, BM25 + semantic
retrieval, bge-reranker-base, and GPT-OSS 120B on Groq. Same code the Streamlit app uses.

Usage (from the repo root):
    uv run python evals/run_eval_app.py [pdf_dir]        # default pdf_dir: notes_gpt/data
    uv run python evals/score.py evals/eval_results_app.json evals/scores_app.json
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "notes_gpt"))

import chromadb
from openai import RateLimitError

from chat import MODEL, build_prompt, get_llm
from ingest import chunk_pages, embed_chunks, index_to_chroma, load_pdf
from retrieve import get_embedder, hybrid_retrieve

pdf_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "notes_gpt/data")
pdfs = sorted(pdf_dir.glob("*.pdf"))
if not pdfs:
    sys.exit(f"no PDFs found in {pdf_dir}")

chunks = [c for p in pdfs for c in chunk_pages(load_pdf(p))]
embed_chunks(chunks, get_embedder())
collection = index_to_chroma(chunks, "eval", chromadb.EphemeralClient())

llm = get_llm()


def answer(messages: list[dict]) -> str:
    for attempt in range(6):
        try:
            resp = llm.chat.completions.create(model=MODEL, messages=messages)
            return resp.choices[0].message.content or ""
        except RateLimitError:
            time.sleep(15 * (attempt + 1))      # Groq free tier: wait out the per-minute token limit
    raise RuntimeError("still rate-limited after 6 attempts")


questions = json.load(open("evals/eval_questions.json"))
for q in questions:
    hits = hybrid_retrieve(q["question"], collection)
    q["answer"] = answer(build_prompt(q["question"], hits))
    q["contexts"] = [h["text"] for h in hits]
    print(f"done: {q['question'][:70]}")

json.dump(questions, open("evals/eval_results_app.json", "w"), indent=2)
print(f"wrote evals/eval_results_app.json: {len(questions)} questions, {len(chunks)} chunks from {len(pdfs)} PDFs")
