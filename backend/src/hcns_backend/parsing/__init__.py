"""Parser implementations."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from hcns_shared.registry import register
from hcns_shared.types import Document

# File extensions LlamaParse can handle
_LLAMAPARSE_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    ".html", ".htm", ".txt", ".md", ".rst",
}


@register("parser", "echo")
class EchoParser:
    """Return one Document per file; text = raw UTF-8 content (or filename for binary).

    Params: (none)
    """

    def parse(self, source: Path) -> list[Document]:
        paths = list(source.rglob("*")) if source.is_dir() else [source]
        docs: list[Document] = []
        for p in paths:
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = f"<binary: {p.name}>"
            doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
            docs.append(
                Document(
                    id=doc_id,
                    text=text,
                    metadata={"source": str(p), "filename": p.name},
                )
            )
        return docs


@register("parser", "llamaparse")
class LlamaParseParser:
    """Parse files via the LlamaParse cloud API (supports PDF, DOCX, PPTX, …).

    Falls back to plain-text read for .txt/.md files to avoid unnecessary API calls.
    Skips unsupported file extensions silently.

    Params:
        result_type     -- "markdown" or "text" (default: "markdown")
        language        -- document language hint (default: "vi")
        api_key_env     -- env var name for the API key (default: "LLAMA_CLOUD_API_KEY")
        num_workers     -- parallel parse workers for batch (default: 4)
        verbose         -- enable verbose SDK logging (default: False)

    Requires env var LLAMA_CLOUD_API_KEY (or the value of api_key_env).
    """

    def __init__(
        self,
        result_type: str = "markdown",
        language: str = "vi",
        api_key_env: str = "LLAMA_CLOUD_API_KEY",
        num_workers: int = 4,
        verbose: bool = False,
    ) -> None:
        self.result_type = result_type
        self.language = language
        self.num_workers = num_workers
        self.verbose = verbose
        self._api_key = os.environ.get(api_key_env, "")
        if not self._api_key:
            raise EnvironmentError(
                f"LlamaParseParser requires env var '{api_key_env}'. "
                "Set it in .env or export before running."
            )
        self._client = self._build_client()

    def _build_client(self):  # type: ignore[return]
        try:
            from llama_parse import LlamaParse  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "llama-parse is not installed. Run: uv add llama-parse"
            ) from e

        return LlamaParse(
            api_key=self._api_key,
            result_type=self.result_type,
            language=self.language,
            num_workers=self.num_workers,
            verbose=self.verbose,
        )

    def parse(self, source: Path) -> list[Document]:
        """Parse *source* (file or dir) — routes each file to LlamaParse or plain-text."""
        paths = list(source.rglob("*")) if source.is_dir() else [source]
        parseable = [p for p in paths if p.is_file() and p.suffix.lower() in _LLAMAPARSE_EXTENSIONS]

        docs: list[Document] = []
        # Plain-text files (avoid API round-trip)
        plain_exts = {".txt", ".md", ".rst"}
        plain_paths = [p for p in parseable if p.suffix.lower() in plain_exts]
        api_paths = [p for p in parseable if p.suffix.lower() not in plain_exts]

        for p in plain_paths:
            text = p.read_text(encoding="utf-8", errors="replace")
            docs.append(_make_doc(p, text))

        if api_paths:
            docs.extend(self._parse_with_api(api_paths))

        return docs

    def _parse_with_api(self, paths: list[Path]) -> list[Document]:
        # LlamaParse.load_data accepts a list of file paths
        raw_results = self._client.load_data([str(p) for p in paths])
        docs: list[Document] = []
        for llama_doc, path in zip(raw_results, paths):
            text = getattr(llama_doc, "text", str(llama_doc))
            docs.append(_make_doc(path, text))
        return docs


def _make_doc(path: Path, text: str) -> Document:
    doc_id = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return Document(
        id=doc_id,
        text=text,
        metadata={"source": str(path), "filename": path.name, "suffix": path.suffix},
    )
