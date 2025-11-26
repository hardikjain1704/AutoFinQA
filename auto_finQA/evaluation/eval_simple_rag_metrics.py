import os
import json
import pandas as pd
import time
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# --- CONFIGURATION ---
INPUT_CSV = "results_generation_final.csv"       # The clean file with 15 rows
DATASET_PATH = "D:/GenAI_and_Agentic_AI/AutoFinQA/auto_finQA/dataset/generation_dataset.json"   # The clean JSON with 15 rows
OUTPUT_CSV = "final_comparison_results.csv"      # The final output

# --- IMPORTS ---
try:
    from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, ContextualPrecisionMetric
    from deepeval.test_case import LLMTestCase
    from deepeval.models.base_model import DeepEvalBaseLLM
    print("DeepEval loaded successfully.")
except ImportError:
    print("CRITICAL: DeepEval not installed. Run 'pip install deepeval'")
    exit()

load_dotenv()

# --- 1. Key Manager ---
class GroqKeyManager:
    def __init__(self):
        self.key = os.getenv("GROQ_API_KEY")
        if not self.key: raise ValueError("GROQ_API_KEY not found in .env!")
    def get_key(self): return self.key

key_mgr = GroqKeyManager()

# --- 2. Custom DeepEval LLM ---
class GroqDeepEvalLLM(DeepEvalBaseLLM):
    def __init__(self, model_name="llama-3.3-70b-versatile"): 
        self.model_name = model_name
    def load_model(self): 
        return ChatGroq(model_name=self.model_name, temperature=0, groq_api_key=key_mgr.get_key())
    def generate(self, prompt: str) -> str:
        try: return self.load_model().invoke(prompt).content
        except: return "Error"
    async def a_generate(self, prompt: str) -> str: return self.generate(prompt)
    def get_model_name(self): return self.model_name

groq_eval_llm = GroqDeepEvalLLM()

# --- 3. Scoring Logic (1.5% Tolerance) ---
def check_smart_accuracy(prediction, expected):
    """
    Checks accuracy with STRICTER 1.5% tolerance.
    """
    def get_nums(text):
        if not isinstance(text, str): return []
        clean = text.replace(",", "")
        matches = re.findall(r'-?\d+\.?\d*', clean)
        return [float(m) for m in matches if m not in [".", "-", "-."]]

    try:
        pred_s = str(prediction).lower()
        exp_s = str(expected).lower()

        # 1. Exact String Match
        if exp_s.strip() in pred_s: return 1

        # 2. Numeric Match (1.5% Tolerance)
        exp_nums = get_nums(exp_s)
        pred_nums = get_nums(pred_s)

        if not exp_nums: 
            return 1 if exp_s in pred_s else 0

        target = exp_nums[0]
        for p in pred_nums:
            # CHANGED: 0.05 -> 0.015 (1.5%)
            if abs(p - target) / (abs(target) + 1e-9) <= 0.015:
                return 1
        return 0
    except:
        return 0

# --- 4. Main Execution ---
def run_simple_eval():
    # 1. Load CSV
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Could not find {INPUT_CSV}")
        return
    df = pd.read_csv(INPUT_CSV)
    
    # 2. Load JSON Context
    json_path = DATASET_PATH
    if not os.path.exists(json_path):
        json_path = "dataset/generation_dataset.json" # Fallback
        
    if not os.path.exists(json_path):
        print("CRITICAL: Dataset JSON not found.")
        return

    with open(json_path, "r") as f: dataset = json.load(f)
    context_map = {str(item['id']): item.get('context', []) for item in dataset}

    print(f"Evaluating Simple RAG on {len(df)} questions...")
    print("Applying 1.5% Tolerance to Accuracy scores...")

    # 3. Recalculate Accuracy Columns (To ensure 1.5% rule is applied)
    df['simple_acc'] = df.apply(lambda x: check_smart_accuracy(x['simple_ans'], x['expected']), axis=1)
    df['agent_acc'] = df.apply(lambda x: check_smart_accuracy(x['agent_ans'], x['expected']), axis=1)

    # 4. Prepare Columns for Metrics
    # Rename existing Agent metrics if they exist
    rename_map = {
        'faithfulness': 'agent_faithfulness',
        'relevancy': 'agent_relevancy',
        'context_precision': 'agent_context_precision'
    }
    df = df.rename(columns=rename_map)

    # Initialize Simple metrics
    df['simple_faithfulness'] = 0.0
    df['simple_relevancy'] = 0.0
    df['simple_context_precision'] = 0.0

    # 5. Evaluation Loop
    for index, row in df.iterrows():
        q_id = str(row['id'])
        query = row['query']
        simple_ans = row['simple_ans']
        expected = row['expected']
        retrieved_context = context_map.get(q_id, [])
        
        print(f"\nProcessing Q{q_id} (Simple RAG)...")
        
        try:
            test_case = LLMTestCase(
                input=query,
                actual_output=simple_ans,
                expected_output=expected,
                retrieval_context=retrieved_context
            )
            
            # Metric 1: Faithfulness
            try:
                fm = FaithfulnessMetric(threshold=0.5, model=groq_eval_llm, include_reason=False)
                fm.measure(test_case)
                df.at[index, 'simple_faithfulness'] = fm.score
                print(f"  > Faithfulness: {fm.score:.2f}")
            except: pass

            # Metric 2: Relevancy
            try:
                arm = AnswerRelevancyMetric(threshold=0.5, model=groq_eval_llm, include_reason=False)
                arm.measure(test_case)
                df.at[index, 'simple_relevancy'] = arm.score
                print(f"  > Relevancy:    {arm.score:.2f}")
            except: pass
                
            # Metric 3: Context Precision
            try:
                cpm = ContextualPrecisionMetric(threshold=0.5, model=groq_eval_llm, include_reason=False)
                cpm.measure(test_case)
                df.at[index, 'simple_context_precision'] = cpm.score
                print(f"  > Precision:    {cpm.score:.2f}")
            except: pass

            # Save incrementally
            df.to_csv(OUTPUT_CSV, index=False)
            time.sleep(2)

        except Exception as e:
            print(f"  [Error] {e}")

    # 6. Final Summary
    print("\n" + "="*50)
    print("FINAL COMPARISON RESULTS (1.5% Tolerance)")
    print("="*50)
    print(f"Simple Accuracy:     {df['simple_acc'].mean():.1%}")
    print(f"Agent Accuracy:      {df['agent_acc'].mean():.1%}")
    print("-" * 30)
    print(f"Simple Faithfulness: {df['simple_faithfulness'].mean():.2f}")
    print(f"Agent Faithfulness:  {df['agent_faithfulness'].mean():.2f}")
    print("-" * 30)
    print(f"Saved to: {OUTPUT_CSV}")

if __name__ == "__main__":
    run_simple_eval()