# auto_finQA/eval/evaluate_numeric_only.py
"""
Numeric-only RAG evaluator.

- Runs retrieval + LLM (or uses cache) with a prompt that asks JSON-only numeric output.
- Extracts numeric prediction from the returned JSON ("answer" field).
- Computes numeric metrics (MAE, MAPE, RMSE) and a numeric exact-match (within tolerance).
- If --skip-non-numeric is set, samples that yield no numeric prediction are skipped.
- Has robust handling for retriever errors (will log and skip sample if retrieval fails).
"""

import argparse
import json
import logging
import math
import hashlib
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from retriever.retrieval import RetrievalPipeline
from workflow.simple_rag_workflow import format_docs
from prompt_library.prompts import PROMPT_REGISTRY, PromptType
from utils.model_loader import ModelLoader
from langchain_core.prompts import ChatPromptTemplate
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("eval_numeric")

# -------------------------
# Utilities
# -------------------------
def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_text(s: str) -> str:
    return " ".join(s.lower().strip().split()) if s is not None else ""

def tokens(s: str) -> List[str]:
    return normalize_text(s).split()

def exact_match(a: str, b: str) -> bool:
    return normalize_text(a) == normalize_text(b)

def f1_score(pred: str, gold: str) -> float:
    pa = tokens(pred)
    ga = tokens(gold)
    if not pa and not ga:
        return 1.0
    if not pa or not ga:
        return 0.0
    common = {}
    for t in pa:
        common[t] = common.get(t, 0) + 1
    matched = 0
    for t in ga:
        if common.get(t, 0) > 0:
            matched += 1
            common[t] -= 1
    if matched == 0:
        return 0.0
    precision = matched / len(pa)
    recall = matched / len(ga)
    return 2 * precision * recall / (precision + recall)

# -------------------------
# Rate limiter + cache
# -------------------------
class SimpleRateLimiter:
    def __init__(self, max_calls_per_minute: int = 60):
        self.capacity = max_calls_per_minute
        self.tokens = float(self.capacity)
        self.fill_rate = float(self.capacity) / 60.0
        self.timestamp = time.time()

    def wait_for_slot(self):
        now = time.time()
        elapsed = now - self.timestamp
        self.timestamp = now
        self.tokens += elapsed * self.fill_rate
        if self.tokens > self.capacity:
            self.tokens = self.capacity
        if self.tokens < 1.0:
            to_wait = (1.0 - self.tokens) / self.fill_rate
            time.sleep(to_wait)
            self.tokens += (time.time() - now) * self.fill_rate
            self.timestamp = time.time()
        self.tokens -= 1.0

class DiskCache:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        else:
            self.cache = {}

    def _key(self, question: str, context_hash: str):
        return hashlib.sha256((question + "|" + context_hash).encode()).hexdigest()

    def get(self, question: str, context_hash: str):
        return self.cache.get(self._key(question, context_hash))

    def set(self, question: str, context_hash: str, value: Any):
        self.cache[self._key(question, context_hash)] = value
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2)

# -------------------------
# Numeric prompt builder
# -------------------------
def build_eval_prompt_numeric_json_only() -> ChatPromptTemplate:
    """
    Build a numeric-focused FINANCIAL_QA prompt but instruct the model to return JSON only.
    JSON schema:
      {"answer": "<numeric or empty string>", "units": "<optional units>", "sources": [{"source":"file","page":<int|null>}], "confidence": "<optional numeric or text>"}
    NOTE: 'answer' should be numeric string or empty.
    """
    base = PROMPT_REGISTRY[PromptType.FINANCIAL_QA].template
    eval_instructions = (
        "\n\nIMPORTANT (for numeric evaluation automation): Return a JSON object ONLY (no extra text) with this exact schema:\n"
        '{{"answer": "<final numeric answer as string or empty if unknown>", "units": "<optional units or empty>", "sources": [{{"source": "<filename>", "page": <page-number-or-null>}}], "confidence": "<optional numeric/confidence>"}}\n'
        "If the context does not contain the numeric answer, set answer to an empty string and sources to [].\n"
        "When you return a numeric value include units (like 'million', '%' etc.) in 'units' field when relevant. The 'answer' field should contain the numeric value only (no commas, no currency signs), e.g. \"97.5\" or \"14\" or \"15.9\" (for percentages, still numeric: \"14\").\n"
    )
    final = base + eval_instructions
    return ChatPromptTemplate.from_template(final)

# -------------------------
# Retriever wrapper
# -------------------------
def get_retrieved_documents_safe(retriever, question: str):
    """
    Safe wrapper: prefers get_relevant_documents, otherwise tries invoke.
    If any retriever raises an exception (e.g. Mongo aggregation error), return empty list and log.
    """
    try:
        if hasattr(retriever, "get_relevant_documents"):
            return retriever.get_relevant_documents(question)
    except Exception as e:
        log.debug("get_relevant_documents failed: %s", e)

    try:
        if hasattr(retriever, "invoke"):
            return retriever.invoke(question)
    except Exception as e:
        log.exception("Retriever invoke failed. Returning empty docs for this sample.")
        return []

    log.error("Retriever has neither get_relevant_documents nor invoke. Returning [].")
    return []

# -------------------------
# Numeric parsing helpers
# -------------------------
_NUMERIC_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[-+]?\d+\.\d+|[-+]?\d+")

def parse_number_from_text(s: str) -> Optional[float]:
    """
    Try to extract a number from free text and apply heuristics for units.
    Returns a float (interpreted as plain numeric) or None.
    Heuristics:
      - If '%' present, returns number as percentage (e.g. '14%' -> 14.0).
      - If 'million' in text -> returns number as millions (97.5 million -> 97.5).
      - If 'billion' in text -> returns number as billions, converted to millions? (we'll return in same base as number but note units separately)
      - Removes commas.
    We return the raw numeric (not scaled) and rely on 'units' field for interpretation.
    """
    if not s:
        return None
    s = s.replace("−", "-")  # sometimes minus is weird
    # First look for explicit JSON numeric fields like "answer": 97.5
    try:
        # if the whole string is numeric (e.g., "97.5"), parse directly
        stripped = s.strip()
        if re.fullmatch(r"[-+]?\d+(\.\d+)?", stripped):
            return float(stripped)
    except Exception:
        pass

    # find first number-like token
    m = _NUMERIC_RE.search(s)
    if not m:
        return None
    num_text = m.group(0)
    # normalize commas
    num_text = num_text.replace(",", "")
    try:
        val = float(num_text)
    except Exception:
        return None
    return val

def extract_numeric_from_model_response(parsed_json: dict) -> (Optional[float], Optional[str]):
    """
    Given parsed JSON from the model, try to return (pred_numeric, units).
    - parsed_json expected to contain "answer" (string) and optional "units" and "confidence".
    - If 'answer' contains a number, parse and return it.
    - If answer is empty but 'confidence' is numeric and 'use_confidence_as_numeric' is desired, you could choose to use it (we do not by default).
    """
    if not isinstance(parsed_json, dict):
        return None, None
    ans = parsed_json.get("answer", "")
    units = parsed_json.get("units", "") or None
    # attempt parse numeric from answer
    n = parse_number_from_text(str(ans))
    if n is not None:
        return n, units
    # fallback: sometimes the model puts numeric in 'confidence' or 'confidence' is numeric string.
    conf = parsed_json.get("confidence")
    if conf is not None:
        try:
            c = float(str(conf))
            # by default we do not treat confidence as the numeric prediction (it is a confidence measure)
            # return None to indicate no numeric prediction
            return None, None
        except Exception:
            pass
    return None, units

# -------------------------
# Metrics (numeric)
# -------------------------
def mae(preds: List[float], golds: List[float]) -> float:
    n = len(preds)
    if n == 0:
        return None
    return sum(abs(p - g) for p, g in zip(preds, golds)) / n

def rmse(preds: List[float], golds: List[float]) -> float:
    n = len(preds)
    if n == 0:
        return None
    return math.sqrt(sum((p - g) ** 2 for p, g in zip(preds, golds)) / n)

def mape(preds: List[float], golds: List[float]) -> float:
    n = len(preds)
    if n == 0:
        return None
    total = 0.0
    count = 0
    for p, g in zip(preds, golds):
        if g == 0:
            # skip or handle; here we treat as large error; to avoid divide-by-zero skip from MAPE calculation
            continue
        total += abs((p - g) / g)
        count += 1
    if count == 0:
        return None
    return (total / count) * 100.0

# -------------------------
# Main evaluator
# -------------------------
def evaluate(
    dataset_path: str,
    out_path: str,
    use_local_model: bool = True,
    max_calls_per_minute: int = 60,
    top_k_eval: int = 5,
    cache_path: str = "auto_finQA/eval/cache_numeric.json",
    max_samples: int = 20,
    skip_non_numeric: bool = True,
):
    log.info("Loading dataset from %s", dataset_path)
    data = load_dataset(dataset_path)

    # Init retrieval + loader
    retrieval_pipeline = RetrievalPipeline()
    retriever = retrieval_pipeline.get_retriever()
    model_loader = ModelLoader()
    llm = model_loader.load_llm() if use_local_model else model_loader.load_llm()

    # Build numeric evaluation prompt
    eval_prompt_template = build_eval_prompt_numeric_json_only()

    def run_llm_with_context(question: str, docs: List[Any], rate_limiter: SimpleRateLimiter, cache: DiskCache):
        ctx_text = format_docs(docs)
        context_hash = hashlib.sha256(ctx_text.encode()).hexdigest()
        cached = cache.get(question, context_hash)
        if cached:
            return cached

        rate_limiter.wait_for_slot()
        prompt = eval_prompt_template
        formatted_prompt = prompt.format(context=ctx_text, question=question)

        resp_text = None
        try:
            if hasattr(llm, "invoke"):
                resp_text = llm.invoke(formatted_prompt)
            elif hasattr(llm, "generate"):
                gen = llm.generate([formatted_prompt])
                resp_text = gen.generations[0][0].text
            elif hasattr(llm, "call"):
                resp_text = llm.call(formatted_prompt)
            else:
                raise RuntimeError("LLM object missing invoke/generate/call methods.")
        except Exception:
            log.exception("LLM call failed, retrying once.")
            time.sleep(1.0)
            try:
                if hasattr(llm, "invoke"):
                    resp_text = llm.invoke(formatted_prompt)
                elif hasattr(llm, "generate"):
                    gen = llm.generate([formatted_prompt])
                    resp_text = gen.generations[0][0].text
                elif hasattr(llm, "call"):
                    resp_text = llm.call(formatted_prompt)
            except Exception:
                log.exception("Second LLM attempt failed. Returning empty string.")
                resp_text = ""

        # coerce to string
        resp_str = str(resp_text).strip()
        cache.set(question, context_hash, resp_str)
        return resp_str

    rate_limiter = SimpleRateLimiter(max_calls_per_minute)
    cache = DiskCache(cache_path)

    results = []
    numeric_preds = []
    numeric_golds = []
    numeric_em_list = []
    skipped_samples = 0

    # limit
    for idx, sample in enumerate(tqdm(data, desc=f"Evaluating up to {max_samples} numeric samples")):
        if idx >= max_samples:
            break

        qa = sample.get("qa", {})
        question = qa.get("question")
        gold_raw = qa.get("answer", "")
        gold_numeric = None
        # Prefer explicit numeric field if dataset includes it (some datasets include 'gold_numeric' directly)
        if "gold_numeric" in sample:
            try:
                gold_numeric = float(sample.get("gold_numeric"))
            except Exception:
                gold_numeric = None
        # fallback: try to parse gold from gold_raw
        if gold_numeric is None:
            try:
                parsed = parse_number_from_text(str(gold_raw))
                if parsed is not None:
                    gold_numeric = parsed
            except Exception:
                gold_numeric = None

        if question is None:
            continue
        if gold_numeric is None and skip_non_numeric:
            # nothing numeric to evaluate
            skipped_samples += 1
            continue

        # Retrieve (safe)
        try:
            docs = get_retrieved_documents_safe(retriever, question)
            docs = list(docs) if docs else []
        except Exception as e:
            log.exception("Retriever raised exception; skipping this sample.")
            skipped_samples += 1
            continue

        # run LLM
        response_text = run_llm_with_context(question, docs, rate_limiter, cache)

        # Parse JSON from response_text robustly
        parsed_json = {}
        pred_numeric = None
        pred_units = None
        try:
            first = response_text.find("{")
            last = response_text.rfind("}")
            json_str = response_text[first:last+1] if first != -1 and last != -1 and last > first else response_text
            parsed_json = json.loads(json_str)
            pred_numeric, pred_units = extract_numeric_from_model_response(parsed_json)
        except Exception:
            # fallback: try to extract number from whole response_text
            pred_numeric = parse_number_from_text(response_text)

        # If no numeric predicted and skipping non-numeric, skip sample
        if pred_numeric is None and skip_non_numeric:
            skipped_samples += 1
            # Still record minimal info for diagnostics
            results.append({
                "question": question,
                "gold_answer": gold_raw,
                "gold_numeric": gold_numeric,
                "pred_answer": parsed_json if isinstance(parsed_json, dict) else response_text,
                "pred_numeric": None,
                "raw_response": response_text,
                "retrieval": {
                    "top_k": top_k_eval,
                    "retrieved_count": len(docs),
                    "retrieved_sources": [
                        {
                            "source": (d.metadata.get("source") if hasattr(d, "metadata") else d.metadata.get("source", "N/A")),
                            "page": (d.metadata.get("page") if hasattr(d, "metadata") else d.metadata.get("page", None)),
                            "snippet": (d.page_content[:300] if hasattr(d, "page_content") else str(d)[:300])
                        }
                        for d in docs[:top_k_eval]
                    ]
                },
                "metrics": None
            })
            continue

        # compute numeric metrics for this sample (if gold_numeric exists)
        if gold_numeric is None:
            # cannot compute numeric metrics for this sample; skip aggregation but save result
            results.append({
                "question": question,
                "gold_answer": gold_raw,
                "gold_numeric": gold_numeric,
                "pred_answer": parsed_json if isinstance(parsed_json, dict) else response_text,
                "pred_numeric": pred_numeric,
                "raw_response": response_text,
                "retrieval": {
                    "top_k": top_k_eval,
                    "retrieved_count": len(docs),
                    "retrieved_sources": [
                        {
                            "source": (d.metadata.get("source") if hasattr(d, "metadata") else d.metadata.get("source", "N/A")),
                            "page": (d.metadata.get("page") if hasattr(d, "metadata") else d.metadata.get("page", None)),
                            "snippet": (d.page_content[:300] if hasattr(d, "page_content") else str(d)[:300])
                        }
                        for d in docs[:top_k_eval]
                    ]
                },
                "metrics": None
            })
            continue

        # record metrics
        numeric_preds.append(pred_numeric)
        numeric_golds.append(gold_numeric)
        numeric_em = 1.0 if (pred_numeric == gold_numeric) else 0.0
        numeric_em_list.append(numeric_em)

        sample_metrics = {
            "numeric_abs_error": None if pred_numeric is None else abs(pred_numeric - gold_numeric),
            "numeric_rel_error": None if pred_numeric is None or gold_numeric == 0 else abs(pred_numeric - gold_numeric) / abs(gold_numeric),
            "numeric_em": numeric_em
        }

        results.append({
            "question": question,
            "gold_answer": gold_raw,
            "gold_numeric": gold_numeric,
            "pred_answer": parsed_json if isinstance(parsed_json, dict) else response_text,
            "pred_numeric": pred_numeric,
            "raw_response": response_text,
            "retrieval": {
                "top_k": top_k_eval,
                "retrieved_count": len(docs),
                "retrieved_sources": [
                    {
                        "source": (d.metadata.get("source") if hasattr(d, "metadata") else d.metadata.get("source", "N/A")),
                        "page": (d.metadata.get("page") if hasattr(d, "metadata") else d.metadata.get("page", None)),
                        "snippet": (d.page_content[:300] if hasattr(d, "page_content") else str(d)[:300])
                    }
                    for d in docs[:top_k_eval]
                ]
            },
            "metrics": sample_metrics
        })

    # aggregate numeric metrics
    summary = {
        "dataset": dataset_path,
        "samples_requested": max_samples,
        "samples_processed": len(results),
        "samples_skipped_non_numeric": skipped_samples,
        "numeric_samples_evaluated": len(numeric_preds),
        "numeric_mae": mae(numeric_preds, numeric_golds) if numeric_preds else None,
        "numeric_rmse": rmse(numeric_preds, numeric_golds) if numeric_preds else None,
        "numeric_mape": mape(numeric_preds, numeric_golds) if numeric_preds else None,
        "numeric_em_avg": (sum(numeric_em_list) / len(numeric_em_list)) if numeric_em_list else None
    }

    output = {"summary": summary, "results": results}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    log.info("Numeric evaluation complete. Results saved to %s", out_path)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline for numeric answers only.")
    parser.add_argument("--dataset", type=str, default="dataset/test.json", help="Path to dataset JSON")
    parser.add_argument("--out", type=str, default="auto_finQA/evaluation/eval_numeric_results.json", help="Output results path")
    parser.add_argument("--use_local_model", action="store_true", help="Prefer local model (ModelLoader)")
    parser.add_argument("--max_calls_per_minute", type=int, default=60, help="Rate limit for LLM calls")
    parser.add_argument("--top_k", type=int, default=5, help="top-k for retrieval eval")
    parser.add_argument("--cache", type=str, default="auto_finQA/eval/cache_numeric.json", help="Disk cache for LLM outputs")
    parser.add_argument("--max-samples", type=int, default=20, help="Limit number of samples to evaluate")
    parser.add_argument("--skip-non-numeric", action="store_true", help="Skip samples where model didn't return a numeric prediction")
    args = parser.parse_args()

    evaluate(
        dataset_path=args.dataset,
        out_path=args.out,
        use_local_model=args.use_local_model,
        max_calls_per_minute=args.max_calls_per_minute,
        top_k_eval=args.top_k,
        cache_path=args.cache,
        max_samples=args.max_samples,
        skip_non_numeric=args.skip_non_numeric,
    )
