# Model Usage Proxy

`model_usage_proxy.py` is a dependency-free OpenAI-compatible proxy for benchmark runs.

Use it when a lane needs measured model usage:

```bash
OPENAI_API_KEY=... \
./runners/python/model_usage_proxy.py \
  --port 18080 \
  --trace-path reports/local-runs/model-usage.jsonl \
  --lane anip \
  --run-id run-001
```

Then point the agent/runtime at:

```bash
OPENAI_BASE_URL=http://127.0.0.1:18080/v1
```

The proxy forwards requests to `https://api.openai.com/v1` by default and writes one JSONL row per model call.

## Captured fields

- benchmark
- lane
- run id
- provider
- model
- path
- status
- started_at
- latency_ms
- input_tokens
- output_tokens
- cached_input_tokens
- reasoning_tokens
- total_tokens
- request_id
- question_id, when provided in metadata or `x-anip-benchmark-question-id`
- error_type

## Why this exists

The cost benchmark cannot rely on prompt character counts. It needs measured usage from provider responses, tied to benchmark question IDs and run IDs.
