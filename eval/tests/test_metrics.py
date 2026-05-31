"""Unit tests for metric calculation functions."""
import math

from ragbench.metrics import (
    aggregate_generation,
    aggregate_retrieval,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    token_overlap_score,
)


def test_recall_perfect():
    assert recall_at_k(["a", "b"], ["a", "b"]) == 1.0


def test_recall_partial():
    assert recall_at_k(["a", "c"], ["a", "b"]) == 0.5


def test_recall_no_relevant():
    assert recall_at_k(["a"], []) == 1.0


def test_precision_at_k():
    assert precision_at_k(["a", "b", "c"], ["a", "b"]) == pytest_approx(2 / 3)


def test_mrr_first():
    assert reciprocal_rank(["a", "b"], ["a"]) == 1.0


def test_mrr_second():
    assert reciprocal_rank(["x", "a"], ["a"]) == 0.5


def test_mrr_none():
    assert reciprocal_rank(["x", "y"], ["a"]) == 0.0


def test_ndcg_perfect():
    score = ndcg_at_k(["a", "b"], ["a", "b"])
    assert math.isclose(score, 1.0, abs_tol=1e-6)


def test_ndcg_none():
    assert ndcg_at_k(["x", "y"], ["a"]) == 0.0


def test_token_overlap_identical():
    assert token_overlap_score("hello world", "hello world") == 1.0


def test_token_overlap_disjoint():
    assert token_overlap_score("foo bar", "baz qux") == 0.0


def test_aggregate_retrieval():
    rows = [
        {"retrieved_ids": ["a", "b"], "relevant_ids": ["a"]},
        {"retrieved_ids": ["x"], "relevant_ids": ["x", "y"]},
    ]
    m = aggregate_retrieval(rows)
    assert m.num_questions == 2
    assert 0 < m.recall_at_k <= 1.0


def test_aggregate_generation():
    rows = [
        {"answer_text": "xin nghỉ phép", "expected_answer": "nghỉ phép năm", "contexts": ["nghỉ phép"]},
    ]
    m = aggregate_generation(rows)
    assert m.num_questions == 1
    assert 0 <= m.answer_relevancy <= 1.0


# ── helpers for pytest approx without importing pytest directly ───────────────

def pytest_approx(val):
    """Small helper so the test file is self-contained."""
    import pytest
    return pytest.approx(val, abs=1e-6)
