"""VectorStore implementations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hcns_shared.registry import register
from hcns_shared.types import Chunk, ScoredChunk


@register("vector_store", "inmemory")
class InMemoryVectorStore:
    """Flat in-memory vector store using brute-force cosine similarity.

    No external dependencies. Suitable for tests and smoke runs.
    Params: (none)
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        existing_ids = {c.id: i for i, c in enumerate(self._chunks)}
        for chunk, vec in zip(chunks, vectors):
            if chunk.id in existing_ids:
                idx = existing_ids[chunk.id]
                self._chunks[idx] = chunk
                self._vectors[idx] = vec
            else:
                self._chunks.append(chunk)
                self._vectors.append(vec)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredChunk]:
        if not self._chunks:
            return []
        scores = [self._cosine(query_vector, v) for v in self._vectors]
        ranked = sorted(zip(scores, self._chunks), key=lambda x: x[0], reverse=True)
        return [ScoredChunk(chunk=c, score=s, source="inmemory") for s, c in ranked[:top_k]]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0


@register("vector_store", "qdrant")
class QdrantVectorStore:
    """Vector store backed by Qdrant (local file or in-process memory mode).

    Params:
        collection  -- Qdrant collection name (default: "ragbench")
        mode        -- "memory" (in-process, ephemeral) or "local" (disk-backed)
                       (default: "memory")
        path        -- local storage path when mode="local" (default: "./data/qdrant")
        url         -- Qdrant server URL; overrides mode/path when set (default: None)
        api_key_env -- env var for Qdrant cloud API key when using url (default: "QDRANT_API_KEY")
        dim         -- vector dimension; inferred from first upsert if 0 (default: 0)
        distance    -- distance metric: "Cosine" | "Dot" | "Euclid" (default: "Cosine")

    The collection is created automatically on first upsert.
    Re-running index() is idempotent: existing points are overwritten by id.
    """

    def __init__(
        self,
        collection: str = "ragbench",
        mode: str = "memory",
        path: str = "./data/qdrant",
        url: str | None = None,
        api_key_env: str = "QDRANT_API_KEY",
        dim: int = 0,
        distance: str = "Cosine",
    ) -> None:
        self.collection = collection
        self.distance = distance
        self._dim = dim
        self._client = self._build_client(mode, path, url, api_key_env)

    def _build_client(
        self,
        mode: str,
        path: str,
        url: str | None,
        api_key_env: str,
    ) -> Any:
        try:
            from qdrant_client import QdrantClient  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "qdrant-client is not installed. Run: uv add qdrant-client"
            ) from e

        if url:
            import os
            api_key = os.environ.get(api_key_env)
            return QdrantClient(url=url, api_key=api_key)
        if mode == "memory":
            return QdrantClient(":memory:")
        if mode == "local":
            Path(path).mkdir(parents=True, exist_ok=True)
            return QdrantClient(path=path)
        raise ValueError(f"QdrantVectorStore: unknown mode '{mode}'. Use 'memory' or 'local'.")

    def _ensure_collection(self, dim: int) -> None:
        from qdrant_client.models import Distance, VectorParams  # type: ignore[import-untyped]

        dist_map = {"Cosine": Distance.COSINE, "Dot": Distance.DOT, "Euclid": Distance.EUCLID}
        distance = dist_map.get(self.distance, Distance.COSINE)

        existing = [c.name for c in self._client.get_collections().collections]
        if self.collection not in existing:
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=distance),
            )

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        dim = len(vectors[0])
        if self._dim == 0:
            self._dim = dim
        self._ensure_collection(self._dim)

        from qdrant_client.models import PointStruct  # type: ignore[import-untyped]

        points = [
            PointStruct(
                id=_chunk_id_to_uint(chunk.id),
                vector=vec,
                payload=_chunk_to_payload(chunk),
            )
            for chunk, vec in zip(chunks, vectors)
        ]
        # Upsert in batches of 256 to stay within Qdrant's default payload limit
        batch = 256
        for i in range(0, len(points), batch):
            self._client.upsert(
                collection_name=self.collection,
                points=points[i : i + batch],
            )

    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredChunk]:
        self._ensure_collection(len(query_vector))
        # qdrant-client ≥1.9 uses query_points(); older versions used search()
        try:
            points = self._client.query_points(
                collection_name=self.collection,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            ).points
        except AttributeError:
            points = self._client.search(  # type: ignore[attr-defined]
                collection_name=self.collection,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )
        return [
            ScoredChunk(
                chunk=_payload_to_chunk(r.payload or {}),
                score=r.score,
                source="qdrant",
            )
            for r in points
        ]

    # ── Hybrid (dense + sparse) ────────────────────────────────────────────────

    def _ensure_hybrid_collection(self, dense_dim: int) -> None:
        """Create a hybrid collection with both a dense and a sparse vector field."""
        from qdrant_client.models import (  # type: ignore[import-untyped]
            Distance,
            SparseVectorParams,
            VectorParams,
        )

        dist_map = {"Cosine": Distance.COSINE, "Dot": Distance.DOT, "Euclid": Distance.EUCLID}
        distance = dist_map.get(self.distance, Distance.COSINE)
        existing = [c.name for c in self._client.get_collections().collections]
        if self.collection not in existing:
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config={"dense": VectorParams(size=dense_dim, distance=distance)},
                sparse_vectors_config={"sparse": SparseVectorParams()},
            )

    def upsert_hybrid(
        self,
        chunks: list[Chunk],
        dense_vecs: list[list[float]],
        sparse_vecs: list[dict[int, float]],
    ) -> None:
        """Index chunks with both dense and sparse vectors (for BGE-M3 hybrid search)."""
        if not chunks:
            return
        dim = len(dense_vecs[0])
        if self._dim == 0:
            self._dim = dim
        self._ensure_hybrid_collection(self._dim)

        from qdrant_client.models import PointStruct, SparseVector  # type: ignore[import-untyped]

        points = [
            PointStruct(
                id=_chunk_id_to_uint(chunk.id),
                vector={
                    "dense": d_vec,
                    "sparse": SparseVector(
                        indices=list(s_vec.keys()),
                        values=list(s_vec.values()),
                    ),
                },
                payload=_chunk_to_payload(chunk),
            )
            for chunk, d_vec, s_vec in zip(chunks, dense_vecs, sparse_vecs)
        ]
        batch = 256
        for i in range(0, len(points), batch):
            self._client.upsert(collection_name=self.collection, points=points[i : i + batch])

    def search_hybrid(
        self,
        dense_vec: list[float],
        sparse_vec: dict[int, float],
        top_k: int = 5,
        rrf_k: int = 60,
    ) -> list[ScoredChunk]:
        """Hybrid search using Qdrant's native RRF fusion over dense + sparse fields."""
        from qdrant_client.models import (  # type: ignore[import-untyped]
            Fusion,
            FusionQuery,
            Prefetch,
            SparseVector,
        )

        self._ensure_hybrid_collection(len(dense_vec))
        # rrf_k is kept for interface parity; Qdrant's built-in RRF uses its own fixed k
        del rrf_k
        response = self._client.query_points(
            collection_name=self.collection,
            prefetch=[
                Prefetch(query=dense_vec, using="dense", limit=top_k * 4),
                Prefetch(
                    query=SparseVector(
                        indices=list(sparse_vec.keys()),
                        values=list(sparse_vec.values()),
                    ),
                    using="sparse",
                    limit=top_k * 4,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        return [
            ScoredChunk(
                chunk=_payload_to_chunk(r.payload or {}),
                score=r.score,
                source="qdrant_hybrid",
            )
            for r in response.points
        ]


# ── Qdrant payload helpers ─────────────────────────────────────────────────────

def _chunk_id_to_uint(chunk_id: str) -> int:
    """Map a hex chunk id to a uint64 Qdrant point id."""
    return int(chunk_id[:16], 16)


def _chunk_to_payload(chunk: Chunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.id,
        "doc_id": chunk.doc_id,
        "text": chunk.text,
        "parent_id": chunk.parent_id,
        "metadata": json.dumps(chunk.metadata, ensure_ascii=False),
    }


def _payload_to_chunk(payload: dict[str, Any]) -> Chunk:
    metadata: dict[str, Any] = {}
    raw_meta = payload.get("metadata", "{}")
    if isinstance(raw_meta, str):
        try:
            metadata = json.loads(raw_meta)
        except json.JSONDecodeError:
            pass
    elif isinstance(raw_meta, dict):
        metadata = raw_meta

    return Chunk(
        id=payload.get("chunk_id", ""),
        doc_id=payload.get("doc_id", ""),
        text=payload.get("text", ""),
        metadata=metadata,
        parent_id=payload.get("parent_id"),
    )
