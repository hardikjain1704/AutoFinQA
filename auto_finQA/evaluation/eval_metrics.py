# eval_metrics.py
import math
import re
import numpy as np

class SmartMatcher:
    """
    Robust matching logic for Financial RAG Evaluation.
    """
    SYNONYMS = {
        "decline": ["decrease", "drop", "fall", "lower", "reduction", "down", "dip", "contraction"],
        "growth": ["increase", "rise", "up", "higher", "improvement", "gain", "expansion"],
        "stable": ["flat", "consistent", "unchanged", "same", "steady"],
        "construction": ["building", "progress", "underway", "development"],
    }

    @staticmethod
    def normalize(text):
        return str(text).lower().strip()

    @staticmethod
    def check_number_match(doc_text, expected_val, tolerance=0.02):
        try:
            clean_expected = re.sub(r'[^\d\.-]', '', str(expected_val))
            if not clean_expected: return False
            val_exp = float(clean_expected)
        except ValueError:
            return False

        candidates = re.findall(r'-?\d{1,3}(?:,\d{3})*(?:\.\d+)?', doc_text)
        for c in candidates:
            try:
                val_c = float(c.replace(',', ''))
                if val_exp != 0 and abs((val_c - val_exp) / val_exp) <= tolerance: return True
                if val_c == val_exp: return True
                if val_exp != 0:
                    if abs((val_c - (val_exp / 100))) < 1e-4: return True
                    if abs((val_c - (val_exp * 100))) < 1e-4: return True
            except ValueError:
                continue
        return False

    @staticmethod
    def check_semantic_match(doc_text, expected_str):
        norm_doc = SmartMatcher.normalize(doc_text)
        norm_exp = SmartMatcher.normalize(expected_str)
        if norm_exp in norm_doc: return True
        if norm_exp in SmartMatcher.SYNONYMS:
            for syn in SmartMatcher.SYNONYMS[norm_exp]:
                if syn in norm_doc: return True
        return False

    @classmethod
    def is_match(cls, doc_content, expected_output):
        if cls.check_number_match(doc_content, expected_output): return True
        if cls.check_semantic_match(doc_content, expected_output): return True
        return False

# --- METRICS ---

def calculate_hit_rate(docs, expected_str):
    """Checks if answer exists ANYWHERE in the retrieved set (Recall)."""
    for d in docs:
        if SmartMatcher.is_match(d.page_content, expected_str):
            return 1.0
    return 0.0

def calculate_mrr(docs, expected_str):
    """Score based on RANK of the first correct answer."""
    for i, d in enumerate(docs, 1):
        if SmartMatcher.is_match(d.page_content, expected_str):
            return 1.0 / i
    return 0.0

def calculate_precision_at_k(docs, expected_str, k=5):
    """De-duplicated Precision@K."""
    current_k = min(len(docs), k)
    relevant_found = False
    for i in range(current_k):
        if SmartMatcher.is_match(docs[i].page_content, expected_str):
            relevant_found = True
            break 
    if relevant_found: return 1.0 / k 
    return 0.0

def calculate_ndcg(docs, expected_str, k=5):
    """
    NDCG@K with De-duplication.
    Only rewards the FIRST relevant doc. 
    Strictly cuts off at k=5 to measure Ranking Quality.
    """
    current_k = min(len(docs), k)
    dcg = 0.0
    found_first = False
    
    for i, d in enumerate(docs[:current_k]):
        if SmartMatcher.is_match(d.page_content, expected_str):
            if not found_first:
                dcg += 1.0 / math.log2((i + 1) + 1)
                found_first = True
            else:
                pass # Ignore duplicates (penalize Simple)
            
    idcg = 1.0
    return dcg / idcg