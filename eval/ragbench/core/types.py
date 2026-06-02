"""Canonical data types used across all pipeline stages.

All fields are required unless marked Optional. Field names MUST NOT be renamed —
downstream metrics and adapters depend on them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """Raw document returned by a Parser.

    Params:
        id       -- unique doc identifier (e.g. content hash or source URI)
        text     -- full extracted text
        metadata -- arbitrary key/value bag (source, title, page, …)
    """
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """A text segment produced by a Chunker.

    Params:
        id        -- unique chunk identifier
        doc_id    -- parent Document.id
        text      -- chunk text
        metadata  -- inherited + chunk-level metadata
        parent_id -- id of the parent chunk (for hierarchical chunking); None for flat
    """
    id: str
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None


@dataclass
class ScoredChunk:
    """A Chunk paired with a retrieval score.

    Params:
        chunk  -- the retrieved Chunk
        score  -- similarity/relevance score (higher = more relevant)
        source -- name of the retriever that produced this result
    """
    chunk: Chunk
    score: float
    source: str


@dataclass
class Answer:
    """Final answer produced by a Generator.

    Params:
        query      -- original question
        text       -- generated answer text
        citations  -- list of chunk ids cited in the answer
        contexts   -- raw context strings fed to the LLM
        usage      -- token usage dict (prompt_tokens, completion_tokens, …)
        latency_ms -- end-to-end generation latency in milliseconds
        trace      -- optional trace id for observability (e.g. Langfuse trace)
    """
    query: str
    text: str
    citations: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    trace: str | None = None
