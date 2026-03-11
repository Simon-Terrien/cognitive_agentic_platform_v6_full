from __future__ import annotations

from pathlib import Path

from experiments.scripts.benchmark_cms_attention import run_benchmark, run_multi_corpus_benchmark


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
    assert result['dataset']['name'] == 'dialogue_corpus'
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


def test_multi_corpus_benchmark_contains_per_corpus_and_aggregate():
    data_dir = Path(__file__).resolve().parents[1] / 'data'
    result = run_multi_corpus_benchmark(data_dir=data_dir, length=20, seed=42, quantile=0.25)

    assert result['mode'] == 'multi-corpus'
    assert 'threshold_calibration' in result
    assert 'thresholds' in result['threshold_calibration']
    assert 'per_corpus' in result
    assert 'aggregate' in result
    assert result['aggregate']['num_corpora'] >= 3
    assert 0.0 <= result['aggregate']['pass_rate'] <= 1.0
    for corpus_result in result['per_corpus'].values():
        assert 'acceptance' in corpus_result
        assert 'delta' in corpus_result
