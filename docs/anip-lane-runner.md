# ANIP Lane Runner

The ANIP lane uses the GTM showcase release-gate harness as the correctness oracle.
That matters: benchmark numbers should be produced from the same 350 + 140
question banks used to validate the generated GTM services, not from a separate
looser evaluator.

## Inputs

You need:

- a checked-out `anip-protocol/anip` repository
- a running generated GTM agent runtime
- an OpenAI-compatible model endpoint, optionally routed through the usage proxy

## Recommended local flow

Start a model usage proxy:

```bash
python3 runners/python/model_usage_proxy.py \
  --host 127.0.0.1 \
  --port 18080 \
  --upstream-base-url https://api.openai.com/v1 \
  --api-key "$OPENAI_API_KEY" \
  --trace-path reports/local-runs/gtm-anip/raw-traces/model-usage.jsonl \
  --provider openai \
  --run-id gtm-anip-local \
  --lane anip \
  --benchmark gtm-agent-490
```

Start the GTM generated services and host-side LLM runtime from the ANIP repo.
The host-side runtime can point to the proxy through `STUDIO_SIMULATOR_BASE_URL`.

Then run the benchmark converter:

```bash
python3 runners/python/run_gtm_anip_benchmark.py \
  --anip-root /path/to/anip \
  --runtime-url http://127.0.0.1:9304 \
  --trace-path reports/local-runs/gtm-anip/raw-traces/model-usage.jsonl \
  --output reports/local-runs/gtm-anip/anip-report.json \
  --model gpt-5.4-mini \
  --provider openai \
  --core \
  --variations
```

For smoke runs, restrict to one phase:

```bash
python3 runners/python/run_gtm_anip_benchmark.py \
  --anip-root /path/to/anip \
  --runtime-url http://127.0.0.1:9304 \
  --output reports/local-runs/gtm-anip/phase1-smoke.json \
  --phase 1 \
  --core
```

## Current limitation

The GTM agent runtime does not yet attach benchmark question IDs to model calls.
The first report therefore contains per-question pass/fail, loop count, and
latency from the regression harness, plus run-level token totals from the proxy.
Per-question token attribution requires adding benchmark metadata to the agent
model-call path.
