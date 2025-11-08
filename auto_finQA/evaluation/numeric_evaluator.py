"""
Numeric Evaluation Module for AutoFinQA RAG System
Evaluates the model's performance on numerical reasoning tasks from financial documents.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException
from workflow.simple_rag_workflow import invoke_chain


class MetricType(str, Enum):
    """Types of numeric evaluation metrics"""
    EXACT_MATCH = "exact_match"
    RELATIVE_ERROR = "relative_error"
    PERCENTAGE_ACCURACY = "percentage_accuracy"
    WITHIN_THRESHOLD = "within_threshold"


@dataclass
class EvaluationResult:
    """Container for evaluation results"""
    question: str
    ground_truth: float
    predicted_value: Optional[float]
    raw_answer: str
    exact_match: bool
    relative_error: Optional[float]
    within_threshold: bool
    error_type: Optional[str] = None


class NumericExtractor:
    """Extracts numeric values from text responses"""
    
    @staticmethod
    def extract_number(text: str) -> Optional[float]:
        """
        Extracts the first numeric value from text.
        Handles formats like: 1,234.56, $1.2M, 45%, etc.
        """
        if not text:
            return None
            
        # Remove common currency symbols and units
        cleaned = text.replace('$', '').replace('€', '').replace('£', '')
        
        # Handle millions/billions notation
        multiplier = 1.0
        if 'million' in cleaned.lower() or 'm' in cleaned.lower():
            multiplier = 1_000_000
            cleaned = re.sub(r'\s*(million|m)\s*', '', cleaned, flags=re.IGNORECASE)
        elif 'billion' in cleaned.lower() or 'b' in cleaned.lower():
            multiplier = 1_000_000_000
            cleaned = re.sub(r'\s*(billion|b)\s*', '', cleaned, flags=re.IGNORECASE)
        elif 'thousand' in cleaned.lower() or 'k' in cleaned.lower():
            multiplier = 1_000
            cleaned = re.sub(r'\s*(thousand|k)\s*', '', cleaned, flags=re.IGNORECASE)
        
        # Handle percentages
        is_percentage = '%' in cleaned
        cleaned = cleaned.replace('%', '')
        
        # Extract numeric value (handles commas and decimals)
        pattern = r'[-+]?\d{1,3}(?:,?\d{3})*(?:\.\d+)?'
        matches = re.findall(pattern, cleaned)
        
        if not matches:
            return None
            
        # Take the first number found
        num_str = matches[0].replace(',', '')
        try:
            value = float(num_str) * multiplier
            if is_percentage:
                value = value / 100.0  # Normalize percentages
            return value
        except ValueError:
            return None
    
    @staticmethod
    def extract_all_numbers(text: str) -> List[float]:
        """Extracts all numeric values from text"""
        pattern = r'[-+]?\d{1,3}(?:,?\d{3})*(?:\.\d+)?'
        matches = re.findall(pattern, text.replace('$', '').replace('%', ''))
        return [float(m.replace(',', '')) for m in matches]


class NumericEvaluator:
    """Evaluates RAG model performance on numeric questions"""
    
    def __init__(self, threshold: float = 0.05):
        """
        Args:
            threshold: Relative error threshold for "close enough" answers (default 5%)
        """
        self.threshold = threshold
        self.extractor = NumericExtractor()
        log.info(f"NumericEvaluator initialized with threshold={threshold}")
    
    def evaluate_single(
        self, 
        question: str, 
        ground_truth: float, 
        model_answer: str
    ) -> EvaluationResult:
        """
        Evaluates a single question-answer pair.
        
        Args:
            question: The input question
            ground_truth: The correct numeric answer
            model_answer: The RAG model's text response
            
        Returns:
            EvaluationResult with computed metrics
        """
        predicted = self.extractor.extract_number(model_answer)
        
        if predicted is None:
            log.warning(f"Could not extract number from answer: {model_answer[:100]}")
            return EvaluationResult(
                question=question,
                ground_truth=ground_truth,
                predicted_value=None,
                raw_answer=model_answer,
                exact_match=False,
                relative_error=None,
                within_threshold=False,
                error_type="extraction_failed"
            )
        
        # Calculate metrics
        exact_match = abs(predicted - ground_truth) < 1e-6
        
        # Avoid division by zero
        if abs(ground_truth) < 1e-9:
            relative_error = abs(predicted - ground_truth)
        else:
            relative_error = abs(predicted - ground_truth) / abs(ground_truth)
        
        within_threshold = relative_error <= self.threshold
        
        return EvaluationResult(
            question=question,
            ground_truth=ground_truth,
            predicted_value=predicted,
            raw_answer=model_answer,
            exact_match=exact_match,
            relative_error=relative_error,
            within_threshold=within_threshold
        )
    
    def evaluate_dataset(
        self, 
        dataset_path: str,
        max_samples: Optional[int] = None
    ) -> Dict:
        """
        Evaluates the RAG model on a complete dataset.
        
        Args:
            dataset_path: Path to the JSON dataset file
            max_samples: Maximum number of samples to evaluate (None for all)
            
        Returns:
            Dictionary with aggregated metrics and detailed results
        """
        try:
            dataset_file = Path(dataset_path)
            if not dataset_file.exists():
                raise AutoFinQAException(f"Dataset file not found: {dataset_path}")
            
            with open(dataset_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different dataset formats
            if isinstance(data, dict):
                samples = data.get('data', data.get('examples', []))
            else:
                samples = data
            
            if max_samples:
                samples = samples[:max_samples]
            
            log.info(f"Evaluating {len(samples)} samples from {dataset_file.name}")
            
            results = []
            for idx, sample in enumerate(samples):
                try:
                    question = sample.get('question', sample.get('qa', {}).get('question', ''))
                    
                    # Extract ground truth (handle different formats)
                    ground_truth = sample.get('answer', sample.get('qa', {}).get('answer'))
                    if isinstance(ground_truth, str):
                        ground_truth = self.extractor.extract_number(ground_truth)
                    else:
                        ground_truth = float(ground_truth)
                    
                    if ground_truth is None:
                        log.warning(f"Skipping sample {idx}: could not parse ground truth")
                        continue
                    
                    # Get model prediction
                    log.info(f"Processing sample {idx + 1}/{len(samples)}")
                    model_answer = invoke_chain(question)
                    
                    # Evaluate
                    result = self.evaluate_single(question, ground_truth, model_answer)
                    results.append(result)
                    
                except Exception as e:
                    log.error(f"Error processing sample {idx}", exc_info=e)
                    continue
            
            # Aggregate metrics
            metrics = self._compute_aggregate_metrics(results)
            
            return {
                'summary': metrics,
                'detailed_results': [
                    {
                        'question': r.question,
                        'ground_truth': r.ground_truth,
                        'predicted': r.predicted_value,
                        'exact_match': r.exact_match,
                        'relative_error': r.relative_error,
                        'within_threshold': r.within_threshold,
                        'raw_answer': r.raw_answer[:200]  # Truncate for readability
                    }
                    for r in results
                ]
            }
            
        except Exception as e:
            raise AutoFinQAException(f"Failed to evaluate dataset: {dataset_path}", e)
    
    def _compute_aggregate_metrics(self, results: List[EvaluationResult]) -> Dict:
        """Computes aggregate metrics from evaluation results"""
        total = len(results)
        if total == 0:
            return {}
        
        valid_results = [r for r in results if r.predicted_value is not None]
        valid_count = len(valid_results)
        
        exact_matches = sum(1 for r in valid_results if r.exact_match)
        within_threshold = sum(1 for r in valid_results if r.within_threshold)
        
        relative_errors = [r.relative_error for r in valid_results if r.relative_error is not None]
        
        metrics = {
            'total_samples': total,
            'valid_predictions': valid_count,
            'extraction_success_rate': valid_count / total if total > 0 else 0,
            'exact_match_accuracy': exact_matches / valid_count if valid_count > 0 else 0,
            'threshold_accuracy': within_threshold / valid_count if valid_count > 0 else 0,
            'mean_relative_error': sum(relative_errors) / len(relative_errors) if relative_errors else None,
            'median_relative_error': sorted(relative_errors)[len(relative_errors) // 2] if relative_errors else None,
        }
        
        log.info("Evaluation complete", **metrics)
        return metrics
    
    def save_results(self, results: Dict, output_path: str):
        """Saves evaluation results to a JSON file"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            log.info(f"Results saved to {output_path}")
        except Exception as e:
            raise AutoFinQAException(f"Failed to save results to {output_path}", e)


# --- Usage Example ---
if __name__ == '__main__':
    """
    Run evaluation on the FinQA dataset
    """
    try:
        log.info("--- STARTING NUMERIC EVALUATION ---")
        
        evaluator = NumericEvaluator(threshold=0.05)  # 5% error tolerance
        
        # Evaluate on dev set (or change to test.json)
        results = evaluator.evaluate_dataset(
            dataset_path="dataset/dev.json",
            max_samples=10  # Remove or increase for full evaluation
        )
        
        # Print summary
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)
        for metric, value in results['summary'].items():
            print(f"{metric}: {value}")
        
        # Save detailed results
        evaluator.save_results(
            results, 
            output_path="../../logs/evaluation_results.json"
        )
        
        log.info("--- NUMERIC EVALUATION COMPLETED ---")
        
    except AutoFinQAException as e:
        log.error("Evaluation failed", exc_info=e)