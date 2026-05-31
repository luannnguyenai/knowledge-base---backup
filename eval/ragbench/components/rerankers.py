"""Reranker implementations."""
from __future__ import annotations

import os

from ragbench.core.registry import register
from ragbench.core.types import ScoredChunk


@register("reranker", "noop")
class NoReranker:
    """Pass-through reranker — returns chunks unchanged.

    Use as a baseline or when no reranking is desired.
    Params: (none)
    """

    def rerank(
        self,
        query: str,  # noqa: ARG002
        chunks: list[ScoredChunk],
        top_k: int | None = None,
    ) -> list[ScoredChunk]:
        if top_k is not None:
            return chunks[:top_k]
        return chunks


@register("reranker", "cohere")
class CohereReranker:
    """Rerank candidates using the Cohere Rerank API.

    Retrieves a larger initial candidate set (the full input list), scores
    each (query, document) pair via Cohere's cross-encoder, and returns
    the top-k above score_threshold.

    Params:
        model           -- Cohere rerank model (default: "rerank-multilingual-v3.0")
        top_k           -- max results to return (default: 5)
        score_threshold -- min relevance score to keep; 0 = keep all (default: 0.0)
        api_key_env     -- env var name for the API key (default: "COHERE_API_KEY")

    Requires env var COHERE_API_KEY (or the value of api_key_env).
    """

    def __init__(
        self,
        model: str = "rerank-multilingual-v3.0",
        top_k: int = 5,
        score_threshold: float = 0.0,
        api_key_env: str = "COHERE_API_KEY",
    ) -> None:
        self.model = model
        self.top_k = top_k
        self.score_threshold = score_threshold

        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise EnvironmentError(
                f"CohereReranker requires env var '{api_key_env}'. "
                "Set it in .env or export before running."
            )
        self._client = self._build_client(api_key)

    def _build_client(self, api_key: str):  # type: ignore[return]
        try:
            import cohere  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "cohere is not installed. Run: uv add cohere"
            ) from e
        return cohere.ClientV2(api_key=api_key)

    def rerank(
        self,
        query: str,
        chunks: list[ScoredChunk],
        top_k: int | None = None,
    ) -> list[ScoredChunk]:
        if not chunks:
            return []
        k = top_k if top_k is not None else self.top_k
        documents = [sc.chunk.text for sc in chunks]

        response = self._client.rerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=k,
        )
        results: list[ScoredChunk] = []
        for hit in response.results:
            score = hit.relevance_score
            if score < self.score_threshold:
                continue
            original = chunks[hit.index]
            results.append(
                ScoredChunk(chunk=original.chunk, score=score, source="cohere")
            )
        return results


@register("reranker", "bge")
class BgeReranker:
    """Rerank candidates using a local BGE cross-encoder via FlagEmbedding.

    Scores each (query, document) pair and filters by score_threshold.
    Runs fully on-device — no API calls.

    Params:
        model           -- HuggingFace model id
                           (default: "BAAI/bge-reranker-v2-m3")
        top_k           -- max results after reranking (default: 5)
        score_threshold -- min score to keep in [0, 1] range (default: 0.0)
        use_fp16        -- use float16 for speed (default: True)
        device          -- "cpu" | "cuda" | "mps" (default: "cpu")

    Requires: pip install FlagEmbedding
    """

    def __init__(
        self,
        model: str = "BAAI/bge-reranker-v2-m3",
        top_k: int = 5,
        score_threshold: float = 0.0,
        use_fp16: bool = True,
        device: str = "cpu",
    ) -> None:
        self.top_k = top_k
        self.score_threshold = score_threshold
        self._model = self._load_model(model, use_fp16, device)

    def _load_model(self, model: str, use_fp16: bool, device: str):  # type: ignore[return]
        try:
            from FlagEmbedding import FlagReranker  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "FlagEmbedding is not installed. Run: uv add FlagEmbedding"
            ) from e
        return FlagReranker(model, use_fp16=use_fp16, device=device)

    def rerank(
        self,
        query: str,
        chunks: list[ScoredChunk],
        top_k: int | None = None,
    ) -> list[ScoredChunk]:
        if not chunks:
            return []
        k = top_k if top_k is not None else self.top_k
        pairs = [[query, sc.chunk.text] for sc in chunks]

        # compute_score returns list of floats in the same order
        raw_scores: list[float] = self._model.compute_score(pairs, normalize=True)

        scored = sorted(
            zip(raw_scores, chunks),
            key=lambda x: x[0],
            reverse=True,
        )
        results: list[ScoredChunk] = []
        for score, sc in scored[:k]:
            if score < self.score_threshold:
                break
            results.append(ScoredChunk(chunk=sc.chunk, score=score, source="bge_reranker"))
        return results
