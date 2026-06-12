# ANIP Benchmarks

Reproducible benchmark suites for comparing ANIP governed service contracts with common agent integration patterns.

The purpose of this repository is not to claim that one protocol is always cheaper or safer. The purpose is to run the same workloads against different implementation styles and publish the measured differences: success rate, loop count, model tier, token usage, estimated cost, latency, and governance correctness.

## Initial benchmark track

The first benchmark track is the GTM Agent workload:

- 490 questions
- governed reads, clarifications, denials, restrictions, approval-required outcomes, and composed service workflows
- ANIP implementation backed by the published GTM Agent contract
- baseline implementations for MCP/tool-calling, raw tools, and skills/recipes workflows

## Benchmark lanes

| Lane | Purpose |
| --- | --- |
| `implementations/anip` | Governed service-contract execution using ANIP packages and generated services. |
| `implementations/mcp` | Standard MCP-style tool discovery/invocation baseline. |
| `implementations/raw-tools` | Direct tool/API-calling baseline without service-owned governance semantics. |
| `implementations/skills-recipes` | Consumer-side skills, recipes, or workflow instructions layered on top of tools. |

## Current runnable lane

The ANIP lane can now run against the existing GTM release-gate harness and emit the shared benchmark report envelope.

Start with:

```bash
python3 runners/python/model_usage_proxy.py --help
python3 runners/python/run_gtm_anip_benchmark.py --help
```

For the end-to-end GTM ANIP lane flow, see `docs/anip-lane-runner.md`.

## Metrics

Every run should produce a machine-readable report containing:

- task success rate
- governance correctness
- loop count
- model used
- prompt tokens
- completion tokens
- tool/service calls
- estimated cost
- latency
- failure class
- reproducibility metadata

See `docs/methodology.md`, `docs/scoring.md`, and `docs/cost-model.md`.

## Status

Experimental scaffold. Do not use early results as public claims until the benchmark methodology and baseline implementations are complete and reviewable.
