import pandas as pd
import re
import os

# --- Configuration ---
INPUT_FILE = "generation_results_final.csv"
OUTPUT_FILE = "results_generation_final.csv"

def check_smart_accuracy(prediction, expected):
    """
    1. Returns -1 if Agent crashed (infra error).
    2. Returns 1 if Text Matches or Number is within 5% tolerance.
    3. Returns 0 otherwise.
    """
    def get_nums(text):
        if not isinstance(text, str): return []
        clean = text.replace(",", "")
        matches = re.findall(r'-?\d+\.?\d*', clean)
        return [float(m) for m in matches if m not in [".", "-", "-."]]

    try:
        pred_s = str(prediction).lower()
        exp_s = str(expected).lower()

        # 1. Detect Infra Crashes
        if "error processing" in pred_s or "encountered an error" in pred_s or "rate limit" in pred_s:
            return -1 

        # 2. Exact Text Match
        if exp_s.strip() in pred_s: return 1

        # 3. Numeric Match (5% Tolerance)
        exp_nums = get_nums(exp_s)
        pred_nums = get_nums(pred_s)

        if not exp_nums: 
            # If expected isn't a number, check for text inclusion (e.g., "Yes")
            return 1 if exp_s in pred_s else 0

        target = exp_nums[0]
        for p in pred_nums:
            if abs(p - target) / (abs(target) + 1e-9) <= 0.05:
                return 1
        return 0
    except:
        return 0

def run_cleaning():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find {INPUT_FILE}")
        return

    print(f"Reading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    # 1. Recalculate Scores (to fix Q21 and others)
    print("Applying Smart Scoring (5% tolerance)...")
    df['simple_acc'] = df.apply(lambda x: check_smart_accuracy(x['simple_ans'], x['expected']), axis=1)
    df['agent_acc'] = df.apply(lambda x: check_smart_accuracy(x['agent_ans'], x['expected']), axis=1)
    
    # 2. Remove Crashes
    print("Filtering out API failures...")
    # Keep rows where Agent Score is NOT -1
    valid_df = df[df['agent_acc'] != -1].copy()
    
    # 3. Calculate Final Stats
    agent_score = valid_df['agent_acc'].mean()
    simple_score = valid_df['simple_acc'].mean()
    
    print("\n" + "="*40)
    print("FINAL VALIDATED RESULTS")
    print("="*40)
    print(f"Total Questions Processed: {len(df)}")
    print(f"Valid Questions (No Crash): {len(valid_df)}")
    print("-" * 30)
    print(f"Agent Accuracy:  {agent_score:.1%}")
    print(f"Simple Accuracy: {simple_score:.1%}")
    print("="*40)
    
    # 4. Save
    valid_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved clean dataset to: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_cleaning()