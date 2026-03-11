from __future__ import annotations

from pathlib import Path

from experiments.scripts.benchmark_cms_attention import run_benchmark


def test_benchmark_runs_on_corpus_dataset():
    corpus_path = Path(__file__).resolve().parents[1] / 'data' / 'dialogue_corpus.txt'
    result = run_benchmark(
        length=10,
        dimension=3,
        seed=42,
        dataset_source='corpus',
        corpus_path=corpus_path,
    )
    assert result['dataset']['source'] == 'corpus'
    assert result['dataset']['length'] == 10
    assert 'acceptance' in result
    assert 'checks' in result['acceptance']


def test_benchmark_acceptance_thresholds_toggle():
    corpus_path = Path(__file__).resolve().parents[1] / 'data' / 'dialogue_corpus.txt'
    permissive = run_benchmark(
        length=10,
        dimension=3,
        seed=42,
        dataset_source='corpus',
        corpus_path=corpus_path,
        min_coherence_delta=-1.0,
        min_stability_delta=-1.0,
        min_mean_similarity_delta=-1.0,
    )
    strict = run_benchmark(
        length=10,
        dimension=3,
        seed=42,
        dataset_source='corpus',
        corpus_path=corpus_path,
        min_coherence_delta=0.5,
        min_stability_delta=0.5,
        min_mean_similarity_delta=0.5,
    )
    assert permissive['acceptance']['passed'] is True
    assert strict['acceptance']['passed'] is False

