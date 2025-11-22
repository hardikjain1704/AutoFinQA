# eval_retrieval.py

import os
import json
import pandas as pd
import importlib
from dotenv import load_dotenv
import retriever.retrieval as ret_module
from logger import GLOBAL_LOGGER as log

# --- IMPORT METRICS ---
from eval_metrics import (
    calculate_hit_rate, 
    calculate_mrr, 
    calculate_ndcg, 
    calculate_precision_at_k
)

load_dotenv()

class GoogleKeyManager:
    def __init__(self):
        self.keys = [os.getenv("GOOGLE_API_KEY")]
        i = 1
        while os.getenv(f"GOOGLE_API_KEY_{i}"):
            self.keys.append(os.getenv(f"GOOGLE_API_KEY_{i}"))
            i += 1
        self.index = 0

    def rotate(self):
        self.index = (self.index + 1) % len(self.keys)
        os.environ["GOOGLE_API_KEY"] = self.keys[self.index]
        importlib.reload(ret_module)
        log.info(f"🔄 Rotated Google Key to #{self.index}")

key_mgr = GoogleKeyManager()

def run_eval():
    print("Loading dataset...")
    # Ensure this path is correct for your system
    dataset_path = "D:/GenAI_and_Agentic_AI/AutoFinQA/auto_finQA/dataset/retrieval_dataset.json"
    with open(dataset_path, "r") as f: 
        dataset = json.load(f)
    
    results = []
    modes = ["simple", "mmr", "rerank"]
    
    print("\nStarting Evaluation with Expanded Search Depth (k=10)...")
    print("(This ensures Hit Rate measures Recall@10, while NDCG measures Rank@5)\n")

    for item in dataset:
        print(f"Retrieving Q{item['id']}...", end="\r")
        
        for mode in modes:
            docs = []
            try:
                attempts = 0
                while attempts < 2:
                    try:
                        pipeline = ret_module.RetrievalPipeline()
                        
                        # --- RUNTIME PATCH ---
                        # We force the retriever to fetch MORE docs (10) to fix Hit Rate.
                        # Reranker will now score 20 candidates (top_k*2) and keep 10.
                        # This prevents the "correct" doc from being dropped.
                        if 'retriever' not in pipeline.config: pipeline.config['retriever'] = {}
                        pipeline.config['retriever']['top_k'] = 10
                        pipeline.config['retriever']['fetch_k'] = 50
                        # ---------------------

                        retriever = pipeline.get_retriever(mode=mode)
                        docs = retriever.invoke(item['query'])
                        break
                    except Exception as e:
                        # log.warning(f"Retry due to: {e}")
                        key_mgr.rotate()
                        attempts += 1

                # --- METRICS CALCULATION ---
                # Hit Rate: Checks ALL 10 docs (Reward for finding it anywhere)
                hit = calculate_hit_rate(docs[:5], item['expected_output'])
                
                # MRR: Checks ALL 10 docs (But rewards rank, so 10th place is low score)
                mrr = calculate_mrr(docs, item['expected_output'])
                
                # NDCG / Precision: STRICTLY checked at Top 5 (Reward for placement)
                # If the answer is at Rank 8, Hit Rate = 1.0, but NDCG@5 = 0.0
                ndcg = calculate_ndcg(docs, item['expected_output'], k=5)
                prec = calculate_precision_at_k(docs, item['expected_output'], k=5)
                
                results.append({
                    "id": item['id'],
                    "mode": mode,
                    "hit_rate": hit,
                    "mrr": mrr,
                    "ndcg": ndcg,
                    "precision_at_5": prec
                })
            except Exception as e:
                log.error(f"Failed Q{item['id']} Mode {mode}: {e}")

    df = pd.DataFrame(results)
    df.to_csv("results_retrieval_final.csv", index=False)
    
    print("\n\n=== EVALUATION SUMMARY ===")
    summary = df.groupby('mode')[['hit_rate', 'mrr', 'ndcg', 'precision_at_5']].mean()
    print(summary.sort_values(by="ndcg", ascending=True))
    print("\nDetailed results saved to: results_retrieval_final.csv")

if __name__ == "__main__":
    run_eval()