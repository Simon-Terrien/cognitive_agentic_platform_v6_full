from __future__ import annotations

from pathlib import Path

from experiments.cms.task_benchmark import load_retrieval_dataset, run_retrieval_rerank_benchmark


def test_retrieval_dataset_loads_examples():
    dataset_path = Path(__file__).resolve().parents[1] / 'data' / 'retrieval_rerank_dataset.json'
    examples = load_retrieval_dataset(dataset_path)
    assert examples
    assert all(example.candidates for example in examples)


def test_task_benchmark_returns_metrics_and_signal():
    dataset_path = Path(__file__).resolve().parents[1] / 'data' / 'retrieval_rerank_dataset.json'
    result = run_retrieval_rerank_benchmark(dataset_path)

    assert result['task'] == 'retrieval_reranking'
    assert result['num_queries'] > 0
    assert result['practical_signal'] in {'positive', 'negative', 'weak_or_mixed'}
    for method in ('cms', 'cosine'):
        metrics = result['metrics'][method]
        assert 0.0 <= metrics['hit_at_1'] <= 1.0
        assert 0.0 <= metrics['mrr'] <= 1.0
        assert 0.0 <= metrics['ndcg_at_3'] <= 1.0
    assert 'delta_cms_minus_cosine' in result['metrics']
    assert result['per_query']

