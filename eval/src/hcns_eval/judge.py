"""LLM-as-judge abstraction with file-based caching.

Cache layout:
    {cache_dir}/{prompt_hash[:2]}/{prompt_hash}.json

Each cache entry:
    {"score": 0.85, "model": "gpt-4o", "prompt_version": "1.0.0",
     "timestamp": "...", "prompt_hash": "..."}

Two runs with the same (model, prompt_version, prompt_text) hit the cache and
return identical scores — this is what makes evals reproducible.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


# ── Prompt templates (versioned; bump prompt_version when changing) ─────────────
# RAGAS-style prompts in Vietnamese/English bilingual style for HC-NS domain

_PROMPTS: dict[str, str] = {
    "faithfulness": (
        "You are evaluating whether an AI assistant's answer is grounded in the provided context.\n\n"
        "Context:\n{contexts}\n\n"
        "Question: {question}\n"
        "Answer: {answer}\n\n"
        "Rate faithfulness on a scale from 0.0 to 1.0:\n"
        "- 1.0: Every claim in the answer is supported by the context\n"
        "- 0.5: Some claims are supported, some are not\n"
        "- 0.0: The answer contradicts or ignores the context\n\n"
        "Reply with ONLY a float between 0.0 and 1.0."
    ),
    "answer_relevancy": (
        "You are evaluating whether an AI assistant's answer addresses the question.\n\n"
        "Question: {question}\n"
        "Answer: {answer}\n\n"
        "Rate relevancy from 0.0 to 1.0:\n"
        "- 1.0: The answer directly and completely addresses the question\n"
        "- 0.5: The answer partially addresses the question\n"
        "- 0.0: The answer does not address the question at all\n\n"
        "Reply with ONLY a float between 0.0 and 1.0."
    ),
    "context_precision": (
        "You are evaluating whether the retrieved context is relevant to the question.\n\n"
        "Question: {question}\n"
        "Context:\n{contexts}\n\n"
        "Rate context precision from 0.0 to 1.0:\n"
        "- 1.0: All retrieved context is directly relevant to the question\n"
        "- 0.5: About half the context is relevant\n"
        "- 0.0: None of the context is relevant to the question\n\n"
        "Reply with ONLY a float between 0.0 and 1.0."
    ),
    "correctness": (
        "You are evaluating whether an AI assistant's answer is factually correct.\n\n"
        "Question: {question}\n"
        "Expected Answer: {expected_answer}\n"
        "Actual Answer: {answer}\n\n"
        "Rate correctness from 0.0 to 1.0:\n"
        "- 1.0: Factually correct and complete\n"
        "- 0.5: Partially correct\n"
        "- 0.0: Factually incorrect or completely wrong\n\n"
        "Reply with ONLY a float between 0.0 and 1.0."
    ),
    "hallucination": (
        "You are detecting hallucinated (fabricated) information in an AI assistant's answer.\n\n"
        "Context:\n{contexts}\n\n"
        "Answer: {answer}\n\n"
        "Rate the hallucination rate from 0.0 to 1.0:\n"
        "- 0.0: No hallucination; all facts are supported by the context\n"
        "- 0.5: Some facts are fabricated\n"
        "- 1.0: Significant fabrication not in the context\n\n"
        "Reply with ONLY a float between 0.0 and 1.0."
    ),
}

# Hash of all prompt templates — bump when any template changes
PROMPT_VERSION_HASH: str = hashlib.sha256(
    json.dumps(_PROMPTS, sort_keys=True).encode()
).hexdigest()[:8]


# ── Judge class ────────────────────────────────────────────────────────────────

@dataclass
class JudgeResult:
    metric: str
    score: float
    cached: bool
    model: str


class Judge:
    """LLM-as-judge with transparent file-based caching.

    Params:
        model              -- LLM model id (default: "gpt-4o")
        temperature        -- sampling temperature (default: 0.0)
        api_key_env        -- env var for OpenAI API key (default: "OPENAI_API_KEY")
        cache_dir          -- directory for result cache (default: ".judge_cache")
        prompt_version     -- version tag stored in cache entries (default: PROMPT_VERSION_HASH)
        skip_on_missing_key -- return 0.0 silently when API key absent (default: True)
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        api_key_env: str = "OPENAI_API_KEY",
        cache_dir: str | Path = ".judge_cache",
        prompt_version: str = PROMPT_VERSION_HASH,
        skip_on_missing_key: bool = True,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.prompt_version = prompt_version
        self.skip_on_missing_key = skip_on_missing_key
        self._cache_dir = Path(cache_dir)
        self._api_key = os.environ.get(api_key_env, "")
        self._client: object | None = None
        if self._api_key:
            self._client = self._build_client()

    def _build_client(self) -> object:
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("openai is not installed. Run: uv add openai") from e
        return OpenAI(api_key=self._api_key)

    # ── Public scoring methods ─────────────────────────────────────────────────

    def faithfulness(self, question: str, answer: str, contexts: list[str]) -> JudgeResult:
        return self._score("faithfulness", question=question, answer=answer,
                           contexts="\n---\n".join(contexts))

    def answer_relevancy(self, question: str, answer: str) -> JudgeResult:
        return self._score("answer_relevancy", question=question, answer=answer)

    def context_precision(self, question: str, contexts: list[str]) -> JudgeResult:
        return self._score("context_precision", question=question,
                           contexts="\n---\n".join(contexts))

    def correctness(self, question: str, answer: str, expected_answer: str) -> JudgeResult:
        return self._score("correctness", question=question, answer=answer,
                           expected_answer=expected_answer)

    def hallucination(self, answer: str, contexts: list[str]) -> JudgeResult:
        return self._score("hallucination", question="", answer=answer,
                           contexts="\n---\n".join(contexts))

    # ── Core ───────────────────────────────────────────────────────────────────

    def _score(self, metric: str, **kwargs) -> JudgeResult:
        prompt = _PROMPTS[metric].format(**{k: v for k, v in kwargs.items() if v is not None})
        cache_key = self._cache_key(metric, prompt)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return JudgeResult(metric=metric, score=cached, cached=True, model=self.model)

        if not self._client:
            if self.skip_on_missing_key:
                return JudgeResult(metric=metric, score=0.0, cached=False, model=self.model)
            raise EnvironmentError(
                "Judge: OpenAI API key not set. Configure OPENAI_API_KEY in .env."
            )

        score = self._call_llm(prompt)
        self._write_cache(cache_key, metric, score, prompt)
        return JudgeResult(metric=metric, score=score, cached=False, model=self.model)

    def _call_llm(self, prompt: str) -> float:
        from openai import OpenAI  # type: ignore[import-untyped]
        assert isinstance(self._client, OpenAI)
        for attempt in range(3):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=16,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = (resp.choices[0].message.content or "").strip()
                return _parse_score(text)
            except Exception as exc:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"Judge LLM call failed: {exc}") from exc
        return 0.0

    # ── Cache helpers ──────────────────────────────────────────────────────────

    def _cache_key(self, metric: str, prompt: str) -> str:
        payload = f"{self.model}|{self.prompt_version}|{metric}|{prompt}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def _read_cache(self, key: str) -> float | None:
        path = self._cache_path(key)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return float(data["score"])
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        return None

    def _write_cache(self, key: str, metric: str, score: float, prompt: str) -> None:
        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "score": score,
            "metric": metric,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "prompt_hash": key[:16],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2))

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / key[:2] / f"{key}.json"


# ── helpers ────────────────────────────────────────────────────────────────────

def _parse_score(text: str) -> float:
    """Extract float from LLM response; clamp to [0, 1]."""
    m = re.search(r"(\d+\.?\d*)", text)
    if m:
        return min(1.0, max(0.0, float(m.group(1))))
    return 0.0
