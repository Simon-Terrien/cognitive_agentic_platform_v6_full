from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from experiments.cms.attention import cosine_similarity, phase_alignment, state_overlap
from experiments.cms.encoding import text_to_cms_state

Method = Literal['cms', 'cosine']


@dataclass(frozen=True)
class Candidate:
    id: str
    text: str
    relevance: int


@dataclass(frozen=True)
class QueryExample:
    query_id: str
    query: str
    candidates: list[Candidate]


def load_retrieval_dataset(path: Path) -> list[QueryExample]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    examples: list[QueryExample] = []
    for item in payload.get('queries', []):
        candidates = [
            Candidate(
                id=candidate['id'],
                text=candidate['text'],
                relevance=int(candidate.get('relevance', 0)),
            )
            for candidate in item.get('candidates', [])
        ]
        examples.append(QueryExample(query_id=item['query_id'], query=item['query'], candidates=candidates))
    return examples


def _score_pair(query: str, candidate: str, method: Method) -> float:
    q_state = text_to_cms_state(query)
    c_state = text_to_cms_state(candidate)
    if method == 'cosine':
        return cosine_similarity(q_state, c_state)
    overlap = state_overlap(q_state, c_state)
    phase = phase_alignment(q_state, c_state)
    return 0.7 * overlap + 0.3 * phase


def _dcg(relevances: list[int], k: int) -> float:
    total = 0.0
    for rank, rel in enumerate(relevances[:k], start=1):
        gain = (2**rel - 1)
        total += gain / math.log2(rank + 1)
    return total


def _query_metrics(ranked: list[tuple[Candidate, float]]) -> dict[str, float]:
    ordered_relevance = [candidate.relevance for candidate, _ in ranked]
    positive_positions = [index + 1 for index, rel in enumerate(ordered_relevance) if rel > 0]
    best = positive_positions[0] if positive_positions else None

    hit_at_1 = 1.0 if ordered_relevance and ordered_relevance[0] > 0 else 0.0
    mrr = 1.0 / best if best is not None else 0.0
    dcg3 = _dcg(ordered_relevance, k=3)
    ideal_relevance = sorted(ordered_relevance, reverse=True)
    idcg3 = _dcg(ideal_relevance, k=3)
    ndcg3 = dcg3 / idcg3 if idcg3 > 0 else 0.0
    return {
        'hit_at_1': hit_at_1,
        'mrr': mrr,
        'ndcg_at_3': ndcg3,
    }


def _aggregate_metric_rows(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {'hit_at_1': 0.0, 'mrr': 0.0, 'ndcg_at_3': 0.0}
    keys = rows[0].keys()
    return {key: sum((row[key] for row in rows)) / len(rows) for key in keys}


def run_retrieval_rerank_benchmark(dataset_path: Path) -> dict:
    examples = load_retrieval_dataset(dataset_path)
    per_method_rows: dict[Method, list[dict[str, float]]] = {'cms': [], 'cosine': []}
    per_query: dict[str, dict] = {}

    for example in examples:
        by_method: dict[Method, dict] = {}
        for method in ('cms', 'cosine'):
            scored = [(candidate, _score_pair(example.query, candidate.text, method)) for candidate in example.candidates]
            ranked = sorted(scored, key=lambda item: item[1], reverse=True)
            metrics = _query_metrics(ranked)
            per_method_rows[method].append(metrics)
            by_method[method] = {
                'top_candidate_id': ranked[0][0].id if ranked else None,
                'metrics': metrics,
            }
        per_query[example.query_id] = by_method

    cms_metrics = _aggregate_metric_rows(per_method_rows['cms'])
    cosine_metrics = _aggregate_metric_rows(per_method_rows['cosine'])
    delta = {key: cms_metrics[key] - cosine_metrics[key] for key in cms_metrics}

    practical_signal = 'weak_or_mixed'
    if delta['mrr'] > 0.03 and delta['ndcg_at_3'] > 0.03:
        practical_signal = 'positive'
    elif delta['mrr'] < -0.03 and delta['ndcg_at_3'] < -0.03:
        practical_signal = 'negative'

    return {
        'task': 'retrieval_reranking',
        'dataset_path': str(dataset_path),
        'num_queries': len(examples),
        'metrics': {
            'cms': cms_metrics,
            'cosine': cosine_metrics,
            'delta_cms_minus_cosine': delta,
        },
        'per_query': per_query,
        'practical_signal': practical_signal,
    }

