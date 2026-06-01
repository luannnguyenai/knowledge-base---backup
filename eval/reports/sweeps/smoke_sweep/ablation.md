# Ablation: smoke_sweep

**Target metric:** `faithfulness` (maximize)

## `chunk_size` (`pipeline.chunker.chunk_size`)

| Value | Avg `faithfulness` | Δ vs first |
| --- | --- | --- |
| `100` | 0.0000 | — |
| `200` | 0.0000 | +0.0000 |
| `400` | 0.0000 | +0.0000 |

## `overlap` (`pipeline.chunker.overlap`)

| Value | Avg `faithfulness` | Δ vs first |
| --- | --- | --- |
| `10` | 0.0000 | — |
| `20` | 0.0000 | +0.0000 |

## `top_k` (`pipeline.retriever.top_k`)

| Value | Avg `faithfulness` | Δ vs first |
| --- | --- | --- |
| `2` | 0.0000 | — |
| `3` | 0.0000 | +0.0000 |
