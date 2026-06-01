"""Prompt templates for agent generators and nodes.

Prompts live as plain-text .md files in this directory (per agents/AGENTS.md:
"Prompts tách riêng file, không embed trong code"). load_prompt() reads them.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load a prompt template by file stem (e.g. "gemini_system").

    Params:
        name -- file name without the .md extension
    Returns:
        the prompt text (trailing whitespace stripped)
    Raises:
        FileNotFoundError if the prompt file does not exist.
    """
    path = _PROMPT_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8").rstrip()
