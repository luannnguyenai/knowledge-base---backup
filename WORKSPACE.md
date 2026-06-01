# HCNS KB Monorepo — uv Workspace Structure

This is a **uv workspace** with 4 Python packages: shared-types, backend, agents, eval. All packages use protocol-based design and registry-driven instantiation.

## Package Organization

```
hcns-kb-workspace/
├── packages/shared-types/src/hcns_shared/     [shared contracts, types, interfaces, registry]
├── backend/src/hcns_backend/                   [parsing, chunking, embedding, retrieval, reranking layers]
├── agents/src/hcns_agents/                     [orchestration: StaticPipeline + LangGraphAgent]
├── eval/src/hcns_eval/                         [eval framework + adapters]
├── pyproject.toml                              [root workspace, dev dependencies]
├── .venv/                                      [shared virtual environment]
└── uv.lock                                     [lock file for reproducible installs]
```

## Package Dependencies

```
hcns_shared
    ↑
hcns_backend
    ↑
hcns_agents
    ↑
hcns_eval (contains adapters that import hcns_agents)
```

### Design Goal: Eval Independence

**eval/ is pipeline-agnostic** — it only depends on `hcns_shared` for protocols and types. The only place eval imports a concrete pipeline is in `eval/src/hcns_eval/adapters/`:

- `baseline_adapter.py` — wraps StaticPipeline
- `newteam_adapter.py` — wraps LangGraphAgent

Both implement the `PipelineAdapter` Protocol (from hcns_shared). The CLI and harness only touch the protocol, never the concrete implementations.

## Quick Start

### Setup

```bash
uv sync                      # Install all packages + dev dependencies into .venv
source .venv/bin/activate   # Or: uv run <command> (auto-activates)
```

### CLI Commands

```bash
# Index corpus
ragbench index --config configs/_smoke.yaml --corpus data/corpus_smoke

# Query
ragbench query "Số ngày nghỉ phép?" --config configs/_smoke.yaml

# Full evaluation
ragbench eval --config configs/_smoke.yaml --save-result reports/baseline.json

# Compare two pipelines
ragbench compare configs/_smoke.yaml configs/new_langgraph.yaml --corpus data/corpus_smoke

# Hyperparameter sweep
ragbench sweep configs/sweeps/smoke_sweep.yaml

# Regression gate
ragbench gate --new reports/pr_result.json --baseline reports/baseline.json --config configs/gate.yaml
```

### Testing

```bash
cd eval
uv run pytest tests/ -q  # All 188 tests
```

## Key Design Patterns

### 1. Protocol-Based Components

Every layer (parser, chunker, embedder, etc.) is a Python Protocol from `hcns_shared.interfaces`. Implementations:
- Live in `hcns_backend/` (layers) or `hcns_agents/` (generators)
- Decorate with `@register(kind, name)` so build() finds them
- Can be swapped without touching other code

### 2. Registry + Factory

```python
@register("parser", "echo")
class EchoParser:
    def parse(self, source: Path) -> list[Document]: ...

# Later:
from hcns_shared import build
parser = build("parser", {"name": "echo"})
```

### 3. Config-Driven Instantiation

```python
cfg = BenchmarkConfig.from_yaml("config.yaml")
pipeline = build_adapter(cfg)  # All components built via registry
```

All component parameters come from YAML, no env vars or hardcoding.

### 4. Eval Isolation via Adapters

eval/src/hcns_eval/adapters/ is the ONLY place eval imports pipeline internals:

```python
class BaselineAdapter:
    def __init__(self, config: BenchmarkConfig):
        from hcns_agents.pipelines import build_pipeline_from_config
        self._pipeline = build_pipeline_from_config(config)

    def index(self, corpus_dir: Path) -> None:
        self._pipeline.index(corpus_dir)

    def query(self, question: str) -> Answer:
        return self._pipeline.query(question)
```

The harness never imports pipeline directly — only the PipelineAdapter Protocol.

## Reproducibility

### Judge Caching

`eval/judge.py` implements file-based caching of LLM judge results:
- Cache key = SHA256(model, prompt_version, prompt_text)
- Cache dir: `.judge_cache/{key[:2]}/{key}.json`
- Same prompt + model = always same score

Two eval runs on identical golden set + config = identical metrics (bitwise).

### Run Manifests

Each `RunResult` includes a `RunManifest`:
- config_hash: SHA256 of YAML
- git_sha: current HEAD
- data_version: golden set version
- judge_model: LLM used
- judge_prompt_version: prompt template version
- ragbench_version: package version
- timestamp: ISO 8601

Enables reproducibility audits and pinpointing which changes caused deltas.

## CI Integration

`.github/workflows/regression-gate.yml` runs:
1. `uv sync` (installs workspace)
2. `pytest tests/ -q` (188 tests)
3. `ragbench eval` on smoke config
4. `ragbench gate` (compares against baseline)
   - Fails (exit 1) if metrics drop beyond threshold

## Workspace Maintenance

### Adding a New Component

1. Create class in `backend/src/hcns_backend/{layer}/`
2. Implement Protocol from `hcns_shared.interfaces`
3. Decorate with `@register(kind, name)`
4. Add to config YAML: `{kind: {name: <name>, ...}}`

No changes needed elsewhere — registry auto-discovers.

### Adding a New Metric

1. Implement function in `eval/src/hcns_eval/metrics/{retrieval,generation}.py`
2. Update `RunResult` dataclass if needed
3. Call from harness: `metric = score_metric(...)`

### Updating Prompts

Prompts live in `agents/src/hcns_agents/prompts/*.md`. Changing one:
1. Edit the `.md` file
2. (No code changes — load_prompt() reads disk)
3. Bump `judge_prompt_version` in config if it's a judge prompt

## Troubleshooting

**Import errors in IDE?** IDE caches may not see the workspace structure.
- Run: `uv sync`
- Reload IDE
- Workspace members are in `packages/shared-types/src`, `backend/src`, `agents/src`, `eval/src`

**Tests import wrong module?** Check `PYTHONPATH`:
- If running tests locally: `cd eval && uv run pytest`
- If in IDE: ensure Python interpreter is the workspace's `.venv`

**Registry not populated?** Packages must be imported to trigger `@register`:
- `hcns_backend` auto-imports all layers in `__init__.py`
- `hcns_agents.generators` auto-imports generators
- Config factories call these before build()

## Related Docs

- `README.md` — Project overview
- `packages/shared-types/README.md` — hcns_shared design
- `backend/README.md` — Component layers
- `agents/README.md` — Orchestration
- `eval/README.md` — Evaluation framework
- `.github/workflows/regression-gate.yml` — CI gate
