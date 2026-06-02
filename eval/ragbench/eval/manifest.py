"""RunManifest — records all inputs that can affect eval reproducibility.

Written alongside every RunResult so that two runs can be verified to be
comparable (same data, same judge, same code).
"""
from __future__ import annotations

import hashlib
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RunManifest:
    """Immutable snapshot of all version-determining inputs for a run.

    Params:
        config_hash       -- SHA-256[:16] of the raw YAML config text
        git_sha           -- first 8 chars of HEAD commit SHA ("unknown" if not a git repo)
        data_version      -- GoldenSet.version string
        data_hash         -- GoldenSet.content_hash() for exact data fingerprint
        judge_model       -- judge model id (e.g. "gpt-4o")
        judge_prompt_version -- semver of the judge prompt templates
        ragbench_version  -- importlib.metadata version of ragbench package
        timestamp         -- ISO-8601 UTC timestamp of the run
        pipeline_name     -- human-readable pipeline label
    """
    config_hash: str
    git_sha: str
    data_version: str
    data_hash: str
    judge_model: str
    judge_prompt_version: str
    ragbench_version: str
    timestamp: str
    pipeline_name: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RunManifest":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def create(
        cls,
        config_path: Path,
        golden_set: "GoldenSet",  # type: ignore[name-defined]
        judge_model: str,
        judge_prompt_version: str,
        pipeline_name: str = "",
    ) -> "RunManifest":
        return cls(
            config_hash=_hash_file(config_path),
            git_sha=_git_sha(),
            data_version=golden_set.version,
            data_hash=golden_set.content_hash(),
            judge_model=judge_model,
            judge_prompt_version=judge_prompt_version,
            ragbench_version=_pkg_version(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            pipeline_name=pipeline_name,
        )


# ── helpers ────────────────────────────────────────────────────────────────────

def _hash_file(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    except Exception:
        return "unknown"


def _git_sha() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).parent,
        ).decode().strip()
        return sha[:8]
    except Exception:
        return "unknown"


def _pkg_version() -> str:
    try:
        from importlib.metadata import version
        return version("ragbench")
    except Exception:
        return "dev"
