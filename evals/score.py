from dotenv import load_dotenv
load_dotenv()

import json
import os
import sys
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings

judge = LangchainLLMWrapper(ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant",
))

embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
)

answer_relevancy.strictness = 1

src = sys.argv[1] if len(sys.argv) > 1 else "evals/eval_results.json"
dst = sys.argv[2] if len(sys.argv) > 2 else "evals/scores.json"

results = json.load(open(src))
data = Dataset.from_dict({
    "question": [r["question"] for r in results],
    "answer": [r["answer"] for r in results],
    "contexts": [r["contexts"] for r in results],
    "ground_truth": [r["ground_truth"] for r in results],
})

run_config = RunConfig(max_workers=2, timeout=120)

report = evaluate(
    data,
    metrics=[faithfulness, answer_relevancy, context_precision],
    llm=judge,
    embeddings=embeddings,
    run_config=run_config,
)
print(report)
report.to_pandas().to_json(dst, orient="records", indent=2)
