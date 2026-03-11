#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.cms.task_benchmark import run_retrieval_rerank_benchmark


DEFAULT_DATASET = Path(__file__).resolve().parents[1] / 'data' / 'retrieval_rerank_dataset.json'


def main() -> None:
    parser = argparse.ArgumentParser(description='Task-grounded CMS benchmark (retrieval reranking).')
    parser.add_argument('--dataset-path', default=str(DEFAULT_DATASET), help='Path to retrieval benchmark dataset JSON.')
    parser.add_argument('--json', action='store_true', help='Print JSON output.')
    args = parser.parse_args()

    result = run_retrieval_rerank_benchmark(Path(args.dataset_path))
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print('CMS Task Benchmark: Retrieval Reranking')
    print(f"Dataset: {result['dataset_path']}")
    print(f"Queries: {result['num_queries']}")
    print('')
    print('CMS metrics:')
    print(json.dumps(result['metrics']['cms'], indent=2))
    print('Cosine metrics:')
    print(json.dumps(result['metrics']['cosine'], indent=2))
    print('Delta (CMS - Cosine):')
    print(json.dumps(result['metrics']['delta_cms_minus_cosine'], indent=2))
    print(f"Practical signal: {result['practical_signal']}")


if __name__ == '__main__':
    main()

