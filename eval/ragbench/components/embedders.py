"""Embedder implementations."""
from __future__ import annotations

import hashlib
import os
import struct
import time

from ragbench.core.registry import register

_GEMINI_BATCH_SIZE = 100

# Known max output_dimensionality per model
_GEMINI_DIM_LIMITS: dict[str, int] = {
    "text-embedding-004": 768,
    "text-embedding-large-exp-03-07": 3072,
    "gemini-embedding-exp-03-07": 3072,
}


@register("embedder", "hash")
class HashEmbedder:
    """Deterministic fake embedder: encodes text via SHA-256 → float vector.

    Produces reproducible vectors with no external API calls.
    Suitable for integration tests and smoke runs.

    Params:
        dim -- output vector dimension (default: 128)
    """

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_vec(t) for t in texts]

    def _hash_to_vec(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        needed = self.dim * 4
        repeated = (digest * (needed // len(digest) + 1))[:needed]
        raw = struct.unpack(f"{self.dim}f", repeated)
        norm = sum(x * x for x in raw) ** 0.5 or 1.0
        return [x / norm for x in raw]


@register("embedder", "gemini")
class GeminiEmbedder:
    """Embed texts using the Google GenAI embedding API (google-genai SDK).

    Params:
        model          -- Gemini embedding model name
                          (default: "text-embedding-large-exp-03-07", 3072 dims)
        dim            -- output dimensionality; must be ≤ model's max (default: 3072)
        task_type      -- embedding task type hint (default: "RETRIEVAL_DOCUMENT")
        api_key_env    -- env var name for the API key (default: "GOOGLE_API_KEY")
        batch_size     -- texts per API call (default: 100)
        retry_attempts -- max retries on rate-limit errors (default: 3)

    Requires env var GOOGLE_API_KEY (or the value of api_key_env).

    Notes:
        - "text-embedding-004" supports dim ≤ 768.
        - "text-embedding-large-exp-03-07" supports dim ≤ 3072 (experimental).
    """

    def __init__(
        self,
        model: str = "text-embedding-large-exp-03-07",
        dim: int = 3072,
        task_type: str = "RETRIEVAL_DOCUMENT",
        api_key_env: str = "GOOGLE_API_KEY",
        batch_size: int = _GEMINI_BATCH_SIZE,
        retry_attempts: int = 3,
    ) -> None:
        self.model = model
        self.dim = dim
        self.task_type = task_type
        self.batch_size = batch_size
        self.retry_attempts = retry_attempts

        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise EnvironmentError(
                f"GeminiEmbedder requires env var '{api_key_env}'. "
                "Set it in .env or export before running."
            )

        max_dim = _GEMINI_DIM_LIMITS.get(model)
        if max_dim is not None and dim > max_dim:
            raise ValueError(
                f"Model '{model}' supports max dim={max_dim}, requested dim={dim}."
            )

        self._client = self._build_client(api_key)

    def _build_client(self, api_key: str):  # type: ignore[return]
        try:
            from google import genai  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "google-genai is not installed. Run: uv add google-genai"
            ) from e
        return genai.Client(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            results.extend(self._embed_batch(texts[i : i + self.batch_size]))
        return results

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        from google.genai import types  # type: ignore[import-untyped]

        for attempt in range(self.retry_attempts):
            try:
                response = self._client.models.embed_content(
                    model=self.model,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type=self.task_type,
                        output_dimensionality=self.dim,
                    ),
                )
                # response.embeddings: list[ContentEmbedding], each has .values
                return [list(emb.values) for emb in response.embeddings]
            except Exception as exc:
                if attempt < self.retry_attempts - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(
                        f"GeminiEmbedder failed after {self.retry_attempts} attempts: {exc}"
                    ) from exc
        return []


@register("embedder", "bge_m3")
class BgeM3Embedder:
    """Dense + sparse embedder using BAAI/bge-m3 via FlagEmbedding.

    Satisfies both the Embedder Protocol (embed → dense) and HybridEmbedder
    (embed_sparse → sparse token-weight dicts for hybrid search).

    BGE-M3 dense vector dimension is 1024.
    Sparse vectors use tokenizer integer IDs as keys (compatible with Qdrant SparseVector).

    Params:
        model_name      -- HuggingFace model id (default: "BAAI/bge-m3")
        use_fp16        -- use float16 inference for speed (default: True)
        device          -- "cpu" | "cuda" | "mps" (default: "cpu")
        batch_size      -- inference batch size (default: 32)
        max_length      -- max token length per text (default: 8192)
        return_sparse   -- also compute sparse lexical weights (default: True)

    Requires: pip install FlagEmbedding
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_fp16: bool = True,
        device: str = "cpu",
        batch_size: int = 32,
        max_length: int = 8192,
        return_sparse: bool = True,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.return_sparse = return_sparse
        self._model = self._load_model(use_fp16, device)

    def _load_model(self, use_fp16: bool, device: str):  # type: ignore[return]
        try:
            from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "FlagEmbedding is not installed. Run: uv add FlagEmbedding"
            ) from e
        return BGEM3FlagModel(self.model_name, use_fp16=use_fp16, device=device)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return dense vectors (1024-dim for bge-m3)."""
        if not texts:
            return []
        output = self._model.encode(
            texts,
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        dense = output["dense_vecs"]
        return [list(map(float, v)) for v in dense]

    def embed_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        """Return sparse lexical-weight dicts (token_id → weight) per text."""
        if not texts:
            return []
        output = self._model.encode(
            texts,
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=False,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        raw_sparse = output["lexical_weights"]  # list[dict[str|int, float]]
        result: list[dict[int, float]] = []
        for token_map in raw_sparse:
            int_map: dict[int, float] = {}
            for k, w in token_map.items():
                # FlagEmbedding may return str keys (token text) or int keys (token id)
                if isinstance(k, int):
                    int_map[k] = float(w)
                else:
                    # Hash-based fallback for string token keys
                    int_map[abs(hash(k)) % (2**20)] = float(w)
            result.append(int_map)
        return result
