"""Chunker implementations."""
from __future__ import annotations

import hashlib
import re

from ragbench.core.registry import register
from ragbench.core.types import Chunk, Document

# Matches markdown headings h1–h3 (lines starting with 1–3 `#`)
_HEADER_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)


@register("chunker", "fixed")
class FixedChunker:
    """Split document text into fixed-size character windows with optional overlap.

    Params:
        chunk_size -- max characters per chunk (default: 512)
        overlap    -- character overlap between adjacent chunks (default: 64)
    """

    def __init__(self, chunk_size: int = 512, overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        chunks: list[Chunk] = []
        step = max(1, self.chunk_size - self.overlap)
        for doc in documents:
            text = doc.text
            idx = 0
            seq = 0
            while idx < len(text):
                window = text[idx : idx + self.chunk_size]
                cid = hashlib.sha256(f"{doc.id}:{idx}".encode()).hexdigest()[:16]
                chunks.append(
                    Chunk(
                        id=cid,
                        doc_id=doc.id,
                        text=window,
                        metadata={**doc.metadata, "chunk_seq": seq, "char_offset": idx},
                    )
                )
                idx += step
                seq += 1
        return chunks


@register("chunker", "parent_child")
class ParentChildChunker:
    """Hierarchical two-level chunker: large parent chunks + small child chunks.

    Strategy:
    - Parent chunks (large window) carry full context; stored in pipeline._parent_map.
    - Child chunks (small window) are embedded and indexed in the vector store.
    - Child.parent_id links back to the parent; caller can expand context at query time.

    Convention used by StaticPipeline: chunks with parent_id=None are PARENTS,
    chunks with parent_id set are CHILDREN.

    Params:
        parent_chunk_size  -- characters per parent chunk (default: 1000)
        child_chunk_size   -- characters per child chunk (default: 300)
        child_overlap      -- character overlap between sibling child chunks (default: 30)
    """

    def __init__(
        self,
        parent_chunk_size: int = 1000,
        child_chunk_size: int = 300,
        child_overlap: int = 30,
    ) -> None:
        if child_chunk_size >= parent_chunk_size:
            raise ValueError(
                f"child_chunk_size ({child_chunk_size}) must be smaller than "
                f"parent_chunk_size ({parent_chunk_size})"
            )
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.child_overlap = child_overlap

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Return parents followed by their children for each document.

        Ordering guarantee: all parents come before children so that StaticPipeline
        can build _parent_map in a single left-to-right pass.
        """
        parents: list[Chunk] = []
        children: list[Chunk] = []

        for doc in documents:
            doc_parents, doc_children = self._chunk_document(doc)
            parents.extend(doc_parents)
            children.extend(doc_children)

        # Parents first so pipeline can build parent_map cheaply
        return parents + children

    def _chunk_document(
        self, doc: Document
    ) -> tuple[list[Chunk], list[Chunk]]:
        text = doc.text
        parents: list[Chunk] = []
        children: list[Chunk] = []

        # --- parent windows (no overlap; each parent is a distinct context block) ---
        p_idx = 0
        p_seq = 0
        while p_idx < len(text):
            p_text = text[p_idx : p_idx + self.parent_chunk_size]
            pid = _chunk_id(doc.id, "p", p_idx)
            parents.append(
                Chunk(
                    id=pid,
                    doc_id=doc.id,
                    text=p_text,
                    metadata={
                        **doc.metadata,
                        "chunk_level": "parent",
                        "chunk_seq": p_seq,
                        "char_offset": p_idx,
                    },
                    parent_id=None,
                )
            )

            # --- child windows inside this parent ---
            c_step = max(1, self.child_chunk_size - self.child_overlap)
            c_local = 0
            c_seq = 0
            while c_local < len(p_text):
                c_text = p_text[c_local : c_local + self.child_chunk_size]
                cid = _chunk_id(doc.id, f"c{p_seq}", c_local)
                children.append(
                    Chunk(
                        id=cid,
                        doc_id=doc.id,
                        text=c_text,
                        metadata={
                            **doc.metadata,
                            "chunk_level": "child",
                            "parent_seq": p_seq,
                            "chunk_seq": c_seq,
                            "char_offset": p_idx + c_local,
                        },
                        parent_id=pid,
                    )
                )
                c_local += c_step
                c_seq += 1

            p_idx += self.parent_chunk_size
            p_seq += 1

        return parents, children


@register("chunker", "contextual_parent_child")
class ContextualParentChildChunker(ParentChildChunker):
    """ParentChildChunker that prepends document + section context to every child chunk.

    Each child's text is prefixed with:
        Tài liệu: {filename}
        Mục: {nearest_markdown_heading_in_parent | "General"}

        {original_child_text}

    This "contextual" prefix anchors the child's embedding to its document origin,
    improving retrieval precision for multi-document corpora — similar to the
    Anthropic "contextual retrieval" technique.

    Params:
        parent_chunk_size -- characters per parent (default: 1000)
        child_chunk_size  -- characters per child (default: 300)
        child_overlap     -- overlap between siblings (default: 30)
        context_template  -- f-string template; receives {filename} and {section}
                             (default: "Tài liệu: {filename}\\nMục: {section}\\n\\n")
    """

    def __init__(
        self,
        parent_chunk_size: int = 1000,
        child_chunk_size: int = 300,
        child_overlap: int = 30,
        context_template: str = "Tài liệu: {filename}\nMục: {section}\n\n",
    ) -> None:
        super().__init__(
            parent_chunk_size=parent_chunk_size,
            child_chunk_size=child_chunk_size,
            child_overlap=child_overlap,
        )
        self.context_template = context_template

    def _chunk_document(self, doc: Document) -> tuple[list[Chunk], list[Chunk]]:
        parents, children = super()._chunk_document(doc)
        parent_by_id = {p.id: p for p in parents}
        filename = doc.metadata.get("filename", "Unknown")

        enriched: list[Chunk] = []
        for child in children:
            parent = parent_by_id.get(child.parent_id or "")
            parent_text = parent.text if parent else ""
            local_offset = child.metadata.get("char_offset", 0) - (
                parent.metadata.get("char_offset", 0) if parent else 0
            )
            section = _nearest_heading(parent_text, local_offset) or "General"
            prefix = self.context_template.format(filename=filename, section=section)
            enriched.append(
                Chunk(
                    id=child.id,
                    doc_id=child.doc_id,
                    text=prefix + child.text,
                    metadata={**child.metadata, "context_section": section},
                    parent_id=child.parent_id,
                )
            )
        return parents, enriched


def _nearest_heading(text: str, before_offset: int) -> str | None:
    """Return the last markdown heading that starts at or before *before_offset* in *text*."""
    best: str | None = None
    for m in _HEADER_RE.finditer(text):
        if m.start() <= before_offset:
            best = m.group(1).strip()
        else:
            break
    return best


def _chunk_id(doc_id: str, level: str, offset: int) -> str:
    return hashlib.sha256(f"{doc_id}:{level}:{offset}".encode()).hexdigest()[:16]
