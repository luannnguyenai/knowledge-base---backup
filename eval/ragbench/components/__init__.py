"""Auto-import all component modules so @register decorators fire on import."""
from ragbench.components import (  # noqa: F401
    chunkers,
    embedders,
    generators,
    parsers,
    rerankers,
    retrievers,
    vector_stores,
)
