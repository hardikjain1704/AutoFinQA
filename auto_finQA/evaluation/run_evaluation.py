"""
Script to run comprehensive evaluation on all datasets
"""

import sys
from pathlib import Path
from datetime import datetime

from evaluation.numeric_evaluator import NumericEvaluator
from logger import GLOBAL_LOGGER as log
from exception.custom_exception import AutoFinQAException


def main():
    """Run evaluation on multiple datasets"""
    try:
        datasets = {
            'dev': 'dataset/dev.json',
            'test': 'dataset/test.json',
            # Add more as needed
        }
        
        evaluator = NumericEvaluator(threshold=0.05)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for name, path in datasets.items():
            log.info(f"Evaluating {name} dataset...")
            
            results = evaluator.evaluate_dataset(
                dataset_path=path,
                max_samples=None  # Evaluate all samples
            )
            
            # Save results
            output_path = f"logs/evaluation_{name}_{timestamp}.json"
            evaluator.save_results(results, output_path)
            
            # Print summary
            print(f"\n{'='*60}")
            print(f"Results for {name.upper()} dataset:")
            print(f"{'='*60}")
            for metric, value in results['summary'].items():
                print(f"  {metric}: {value:.4f}" if isinstance(value, float) else f"  {metric}: {value}")
        
        log.info("All evaluations completed successfully")
        
    except Exception as e:
        log.error("Evaluation pipeline failed", exc_info=e)
        sys.exit(1)


if __name__ == '__main__':
    main()