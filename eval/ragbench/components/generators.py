"""Generator implementations."""
from __future__ import annotations

import os
import re
import time

from ragbench.core.registry import register
from ragbench.core.types import Answer, ScoredChunk

_GEMINI_SYSTEM_PROMPT = """\
Bạn là trợ lý KB nội bộ cho hệ thống Hành chính – Nhân sự (HC-NS).
Chỉ trả lời dựa trên các đoạn tài liệu được cung cấp bên dưới.
Với mỗi thông tin bạn trích dẫn, hãy ghi rõ nguồn bằng ký hiệu [CHUNK_ID] ngay sau câu đó.
Nếu câu trả lời không có trong tài liệu, hãy nói: "Tôi không tìm thấy thông tin này trong KB."
Trả lời bằng tiếng Việt, súc tích và chính xác.\
"""

_CITATION_RE = re.compile(r"\[([a-f0-9]{8,16})\]")


@register("generator", "fake")
class FakeGenerator:
    """Deterministic fake generator: answer = concatenation of retrieved context snippets.

    No LLM calls. Suitable for integration tests and smoke runs.
    Params:
        max_context_chars -- max chars from each chunk to include (default: 200)
    """

    def __init__(self, max_context_chars: int = 200) -> None:
        self.max_context_chars = max_context_chars

    def generate(self, query: str, chunks: list[ScoredChunk]) -> Answer:
        contexts = [sc.chunk.text[: self.max_context_chars] for sc in chunks]
        answer_text = " | ".join(contexts) if contexts else "[no context]"
        citations = [sc.chunk.id for sc in chunks]
        return Answer(
            query=query,
            text=answer_text,
            citations=citations,
            contexts=contexts,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )


@register("generator", "gemini")
class GeminiGenerator:
    """Generate answers using the Gemini API (google-genai SDK) with enforced citations.

    Each retrieved chunk is formatted as:
        [CHUNK_ID] <chunk text>
    The system prompt instructs the model to cite every fact with [CHUNK_ID].
    Citations are extracted from the response via regex and stored in Answer.citations.

    Params:
        model             -- Gemini model id (default: "gemini-2.0-flash")
        temperature       -- sampling temperature (default: 0.1)
        max_output_tokens -- max tokens in the answer (default: 1024)
        api_key_env       -- env var name for the API key (default: "GOOGLE_API_KEY")
        retry_attempts    -- retries on transient API errors (default: 3)
        system_prompt     -- override default system instructions (default: None)

    Requires env var GOOGLE_API_KEY (or the value of api_key_env).
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.1,
        max_output_tokens: int = 1024,
        api_key_env: str = "GOOGLE_API_KEY",
        retry_attempts: int = 3,
        system_prompt: str | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.retry_attempts = retry_attempts
        self._system_prompt = system_prompt or _GEMINI_SYSTEM_PROMPT

        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise EnvironmentError(
                f"GeminiGenerator requires env var '{api_key_env}'. "
                "Set it in .env or export before running."
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

    def generate(self, query: str, chunks: list[ScoredChunk]) -> Answer:
        from google.genai import types  # type: ignore[import-untyped]

        contexts = [sc.chunk.text for sc in chunks]
        user_message = _build_user_message(query, chunks)

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            system_instruction=self._system_prompt,
        )

        for attempt in range(self.retry_attempts):
            try:
                t0 = time.perf_counter()
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=user_message,
                    config=config,
                )
                latency_ms = (time.perf_counter() - t0) * 1000
                break
            except Exception as exc:
                if attempt < self.retry_attempts - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(
                        f"GeminiGenerator failed after {self.retry_attempts} attempts: {exc}"
                    ) from exc
        else:
            latency_ms = 0.0

        answer_text = response.text or ""
        citations = _CITATION_RE.findall(answer_text)

        usage: dict[str, int] = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(meta, "prompt_token_count", 0),
                "completion_tokens": getattr(meta, "candidates_token_count", 0),
            }

        return Answer(
            query=query,
            text=answer_text,
            citations=citations,
            contexts=contexts,
            usage=usage,
            latency_ms=latency_ms,
        )


def _build_user_message(query: str, chunks: list[ScoredChunk]) -> str:
    context_block = "\n\n".join(
        f"[{sc.chunk.id}] (score={sc.score:.3f})\n{sc.chunk.text}" for sc in chunks
    )
    return (
        f"## Tài liệu tham khảo\n\n{context_block}\n\n"
        f"## Câu hỏi\n\n{query}"
    )


@register("generator", "routed")
class RoutedGenerator:
    """Route queries to different generators based on detected complexity.

    Routing logic (in priority order):
    1. If query matches any of *complex_keywords* (case-insensitive)   → smart_generator
    2. If query word-count ≥ *min_words_for_smart*                     → smart_generator
    3. Otherwise                                                        → fast_generator

    This gives a cheap, zero-latency routing decision that avoids burning
    expensive model capacity on simple factual lookups.

    Params:
        fast_generator      -- Generator for simple / factual queries
        smart_generator     -- Generator for complex / multi-hop queries
        complex_keywords    -- list of substrings that trigger the smart generator
                               (default: Vietnamese complexity signals)
        min_words_for_smart -- word count threshold for smart routing (default: 15)
    """

    _DEFAULT_KEYWORDS: list[str] = [
        "so sánh", "giải thích chi tiết", "giải thích rõ",
        "phân tích", "tại sao", "ưu nhược điểm",
        "khác nhau", "liên quan", "tổng hợp",
    ]

    def __init__(
        self,
        fast_generator: "Generator",  # type: ignore[name-defined]
        smart_generator: "Generator",  # type: ignore[name-defined]
        complex_keywords: list[str] | None = None,
        min_words_for_smart: int = 15,
    ) -> None:
        self._fast = fast_generator
        self._smart = smart_generator
        self._keywords = [kw.lower() for kw in (complex_keywords or self._DEFAULT_KEYWORDS)]
        self._min_words = min_words_for_smart

    def generate(self, query: str, chunks: list[ScoredChunk]) -> Answer:
        gen = self._smart if self._is_complex(query) else self._fast
        answer = gen.generate(query, chunks)
        answer.trace = f"routed:{'smart' if gen is self._smart else 'fast'}"
        return answer

    def _is_complex(self, query: str) -> bool:
        lower = query.lower()
        if any(kw in lower for kw in self._keywords):
            return True
        return len(lower.split()) >= self._min_words
