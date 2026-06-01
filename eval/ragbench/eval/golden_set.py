"""GoldenSet — typed loader for the Q&A golden set JSON format.

Schema contract (from AGENTS.md):
    {version, questions: [{id, question, answer, expected_sources,
                            difficulty, topic, query_type}]}
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

QueryType = Literal["factual", "procedural", "multi-hop", "comparative", "out-of-scope"]
Difficulty = Literal["factual", "procedural", "multi-hop", "comparative", "edge", "out-of-scope"]


@dataclass
class GoldenQuestion:
    """Single Q&A pair with retrieval ground truth.

    Params:
        id               -- unique identifier ("q001", …)
        question         -- natural-language question
        answer           -- reference / expected answer text
        expected_sources -- list of source identifiers that must be retrieved
        difficulty       -- complexity label
        topic            -- domain topic tag
        query_type       -- retrieval strategy hint
    """
    id: str
    question: str
    answer: str
    expected_sources: list[str]
    difficulty: str
    topic: str
    query_type: str

    @classmethod
    def from_dict(cls, d: dict) -> "GoldenQuestion":
        return cls(
            id=d["id"],
            question=d["question"],
            answer=d["answer"],
            expected_sources=d.get("expected_sources", []),
            difficulty=d.get("difficulty", "factual"),
            topic=d.get("topic", ""),
            query_type=d.get("query_type", "factual"),
        )


@dataclass
class GoldenSet:
    """Versioned collection of golden Q&A pairs.

    Params:
        version   -- semver string (e.g. "1.0.0")
        questions -- list of GoldenQuestion
        source    -- file path the set was loaded from (None if built in-memory)
    """
    version: str
    questions: list[GoldenQuestion]
    source: Path | None = field(default=None, compare=False)

    @classmethod
    def from_json(cls, path: Path) -> "GoldenSet":
        """Load and validate a golden set from *path*.

        Raises:
            FileNotFoundError if *path* doesn't exist.
            KeyError / TypeError if required fields are missing.
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=str(raw.get("version", "0.0.0")),
            questions=[GoldenQuestion.from_dict(q) for q in raw["questions"]],
            source=path,
        )

    def content_hash(self) -> str:
        """SHA-256 hash of the serialised question list (version + all fields)."""
        payload = json.dumps(
            [q.__dict__ for q in self.questions],
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def filter_by_type(self, query_type: str) -> "GoldenSet":
        """Return a subset containing only questions of the given query_type."""
        return GoldenSet(
            version=self.version,
            questions=[q for q in self.questions if q.query_type == query_type],
            source=self.source,
        )

    def __len__(self) -> int:
        return len(self.questions)
