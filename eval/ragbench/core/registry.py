"""Global component registry.

Usage:
    @register("chunker", "fixed")
    class FixedChunker: ...

    obj = build("chunker", {"name": "fixed", "chunk_size": 256})

Raises ComponentNotFoundError with a helpful message listing registered names
when an unknown component is requested (fail-fast principle).
"""
from __future__ import annotations

from typing import Any, Callable, Type

_REGISTRY: dict[str, dict[str, Type[Any]]] = {}

_KIND_LABELS = {
    "parser": "Parser",
    "chunker": "Chunker",
    "embedder": "Embedder",
    "vector_store": "VectorStore",
    "retriever": "Retriever",
    "reranker": "Reranker",
    "generator": "Generator",
}


class ComponentNotFoundError(KeyError):
    """Raised when build() cannot find a registered name for a kind."""


def register(kind: str, name: str) -> Callable[[Type[Any]], Type[Any]]:
    """Class decorator — registers *cls* under (*kind*, *name*).

    Params:
        kind -- component category (e.g. "chunker", "embedder")
        name -- unique identifier within the category
    """
    def decorator(cls: Type[Any]) -> Type[Any]:
        _REGISTRY.setdefault(kind, {})[name] = cls
        return cls
    return decorator


def build(kind: str, spec: dict[str, Any]) -> Any:
    """Instantiate a registered component from a spec dict.

    The spec must contain a "name" key matching a registered component.
    All remaining keys are passed as keyword arguments to __init__.

    Params:
        kind -- component category
        spec -- dict with at least {"name": "<registered_name>", ...kwargs}

    Raises:
        ComponentNotFoundError if kind or name is not registered
    """
    name = spec.get("name")
    if name is None:
        raise ComponentNotFoundError(
            f"Component spec for kind '{kind}' is missing the 'name' field. "
            f"Registered names: {list(_REGISTRY.get(kind, {}).keys())}"
        )
    available = _REGISTRY.get(kind, {})
    if name not in available:
        label = _KIND_LABELS.get(kind, kind)
        raise ComponentNotFoundError(
            f"Unknown {label} '{name}'. "
            f"Registered {label}s: {sorted(available.keys()) or '(none)'}\n"
            f"Tip: make sure the component module is imported before calling build()."
        )
    kwargs = {k: v for k, v in spec.items() if k != "name"}
    return available[name](**kwargs)


def list_registered(kind: str) -> list[str]:
    """Return sorted list of registered names for a kind."""
    return sorted(_REGISTRY.get(kind, {}).keys())
