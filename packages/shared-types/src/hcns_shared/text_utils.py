"""Lightweight, dependency-free text utilities shared across packages.

Used by the agent self-correct node (faithfulness proxy) and by the legacy
P0 eval harness. Kept in shared-types so neither agents nor eval needs to
import the other for this primitive.
"""
from __future__ import annotations


def token_overlap_score(text_a: str, text_b: str) -> float:
    """Token Jaccard similarity between two strings.

    Params:
        text_a -- first string
        text_b -- second string
    Returns:
        |A ∩ B| / |A ∪ B| over whitespace tokens; 0.0 if either is empty.
    """
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
